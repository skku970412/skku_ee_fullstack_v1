# 백엔드 기술 보고서 v3 (FastAPI 서버)

## 1. 역할과 범위
- 이 백엔드 서버는 다음 네 가지 역할을 맡습니다.
  1. 예약 관리: 전기차 충전 예약을 생성·조회·취소하고, 예약 시간이 서로 겹치지 않도록 보장.
  2. 번호판 검증·매칭: 번호판 문자열이 기존 예약과 충돌하는지 확인하고, 실시간 인식 결과를 예약과 매칭.
  3. 관리자 기능: 관리자 계정으로 날짜별 예약 현황을 확인하고, 필요 시 예약을 강제로 삭제.
  4. 시스템 설정: 시간대, CORS, 번호판 인식 모드(OpenAI/HTTP), 관리자 계정 등의 설정을 환경변수로 관리.

## 2. 전체 구조
### 2.1 주요 모듈
- `main.py`
  - `create_app()` 팩토리 함수에서 FastAPI 인스턴스를 생성합니다.
  - CORS 설정: `CORS_ORIGINS` 환경변수를 기준으로 허용 도메인 목록 설정.
  - 라우터 등록:
    - 건강 체크: `routers.health`
    - 예약 관련: `routers.reservations`
    - 관리자: `routers.admin`
    - 사용자 로그인: `routers.user`
    - 번호판 인식 프록시: `routers.plates`
  - `@app.on_event("startup")`에서 DB 초기화 및 마이그레이션 수행.

- `config.py`
  - `Settings` 클래스에 모든 환경 설정을 정의합니다.
  - 주요 항목:
    - `database_url`: 기본 `sqlite:///./data/ev_charging.db`.
    - `business_timezone`: `Asia/Seoul` (영업시간 해석용).
    - 관리자 계정: 이메일/비밀번호/토큰.
    - `auto_seed_sessions`: 기본 세션 자동 생성 여부.
    - CORS, 번호판 인식 모드(`plate_service_mode`), OpenAI 프롬프트/모델, API 키.
  - OPENAI_API_KEY가 비어 있으면 `openai-key.txt`에서 키를 자동 로드.

- `database.py`
  - SQLAlchemy `engine` 및 `SessionLocal` 생성.
  - SQLite인 경우 `check_same_thread=False`로 설정하여 여러 스레드에서 세션 사용 가능.
  - `session_scope()` 컨텍스트 매니저와 `get_db()` 종속성으로 세션 라이프사이클 관리.

### 2.2 데이터 모델(models.py)
- `ChargingSession`
  - 충전 자리(예: 세션 1~4)를 나타냅니다.
  - 필드: `id`, `name`.
  - 관계: 여러 `Reservation`을 가집니다.

- `Reservation`
  - 실제 예약 한 건을 나타냅니다.
  - 주요 필드:
    - `id`: UUID 문자열.
    - `session_id`: 어떤 충전 자리인지.
    - `plate` / `plate_normalized`: 원본 번호판과 공백 제거·대문자 변환한 정규화 값.
    - `start_time`, `end_time`: timezone 정보를 포함한 UTC 기준 시각.
    - `status`: CONFIRMED / IN_PROGRESS / COMPLETED / CANCELLED.
    - `contact_email`: 예약자 이메일.
    - `created_at`, `updated_at`: 생성/수정 타임스탬프.
  - 유니크 제약: `session_id + start_time` 조합은 한 번만 허용합니다.
  - `derived_status` 속성:
    - 현재 시각 기준으로 예약의 실제 상태를 계산합니다.
    - 예: 아직 시작 전이면 CONFIRMED, 진행 중이면 IN_PROGRESS, 끝났으면 COMPLETED.

- `ReservationSlot`
  - 30분 단위 슬롯을 나타냅니다.
  - 필드:
    - `reservation_id`: 어떤 예약에 속하는지.
    - `session_id`: 어떤 세션인지.
    - `slot_start`: 슬롯 시작 시각(UTC, timezone 정보 포함).
  - 유니크 제약: `session_id + slot_start` 조합이 한 번만 존재하도록 제한.
  - 이 제약으로 같은 세션에서 같은 30분 구간에 두 예약이 동시에 들어오는 것을 DB 차원에서 막습니다.

### 2.3 시간·타임존 처리(time_utils.py)
- `business_timezone()`: 설정에서 읽은 타임존(기본 `Asia/Seoul`) 객체 반환.
- `combine_business_datetime(date, time)`: 날짜+시간을 비즈니스 타임존 기준 datetime으로 합칩니다.
- `business_day_bounds_utc(date)`: 하루의 시작~끝을 비즈니스 타임존 기준으로 계산한 뒤 UTC로 변환.
- `ensure_utc(dt)`: naive datetime이면 UTC로 간주하고 timezone을 부여한 뒤, UTC로 변환.

## 3. 예약/검증/매칭 로직
### 3.1 예약 생성 흐름
1) 입력 데이터 검증(schemas.py – `ReservationCreate`)
   - `sessionId`, `plate`, `date`, `startTime`, `endTime`, `contactEmail`를 받습니다.
   - 날짜/시간 문자열을 `YYYY-MM-DD`, `HH:MM` 형식으로 검증하고, 파이썬 `date`, `time` 객체로 변환.
   - 번호판 길이가 너무 짧으면 에러.
   - 이메일은 공백 제거 후 소문자로 정규화.

2) 도메인 규칙 검사(routers/reservations.py)
   - 선택한 세션이 존재하는지 확인, 없으면 404.
   - `combine_business_datetime`으로 한국시간 기준 시작/끝 시각 생성.
   - 종료 시간이 시작 시간보다 빠르면 400 에러.
   - 30분 단위 및 영업시간(09~22시) 범위 체크:
     - 시작·끝이 00 또는 30분이어야 함.
     - 시작 시간은 09:00~22:00 사이.
     - 종료 시간은 22:00을 넘으면 안 됨.
   - 총 길이(분)가 30의 배수인지 확인.
   - 마지막으로 UTC로 변환 후 CRUD 계층에 넘깁니다.

3) CRUD 계층에서의 충돌 검사(crud.py)
   - `_lock_session`: 해당 세션의 행을 `SELECT ... FOR UPDATE`로 잠금 → 동시 예약 생성 시 레이스 컨디션 방지.
   - `normalize_plate`: 번호판 문자열에서 공백 제거, 대문자 변환.
   - `ensure_no_overlap`:
     - 예약 기간을 30분 구간으로 나눈 `slot_start` 리스트 생성.
     - 이미 같은 세션에서 해당 `slot_start`를 사용하는 예약 슬롯이 있는지 확인.
     - 하나라도 겹치면 “해당 시간에 이미 예약이 존재합니다” 에러 반환.
   - `ensure_no_conflict_for_plate`:
     - 같은 차량(normalized plate)이 예약 상태(CANCELLED 제외)에서 시간 구간이 겹치는 예약이 있는지 확인.
     - 있으면 “해당 차량은 다른 시간대에 이미 예약되어 있습니다” 에러.
   - 에러 없으면 `Reservation`과 연결된 `ReservationSlot`을 생성하고, DB에 flush 합니다.

### 3.2 번호판 검증·매칭
- `/api/plates/verify`
  - 사용자가 예약을 시도하기 전에 번호판·시간·세션을 입력하면, 해당 조합이 기존 예약과 겹치는지를 백엔드가 최종 확인합니다.
  - 충돌이 있으면 `conflict=true`와 함께 어떤 예약과 겹치는지 상세 정보를 반환합니다.

- `/api/plates/match`
  - 카메라 워커가 인식한 번호판과 시각을 보내면, 그 시각에 유효한 예약이 있는지 확인합니다.
  - 규칙:
    - 번호판은 normalize 후 비교.
    - 상태가 CANCELLED가 아닌 예약 중, `start_time <= timestamp < end_time`이면 활성 예약으로 간주.
  - 결과:
    - `match=true`이면 해당 예약의 요약 정보를 함께 반환.
    - 그렇지 않으면 `match=false`.

## 4. 번호판 인식 프록시(plates.py)
- `/api/license-plates`
  - 프런트나 워커가 업로드한 이미지 파일을 받아, 내부 설정에 따라 인식 방법을 선택합니다.
  - `plate_service_mode == "gptapi"`:
    - OpenAI Responses API를 사용.
    - 이미지 파일을 base64 data URL로 변환해 프롬프트와 함께 전송.
  - 그 외(http 모드):
    - `PLATE_SERVICE_URL`로 multipart/form-data 요청을 그대로 전달(프록시).
  - 응답:
    - 인식된 번호판 문자열(`plate`)과 원본 응답(`raw`)을 JSON으로 반환.

## 5. 설계 상 강점과 한계
### 5.1 강점
- 겹치는 예약/번호판 중복을 DB 레벨 유니크 제약과 비즈니스 로직으로 이중으로 차단합니다.
- UTC 기준 저장 + 비즈니스 타임존 변환 구조로, 서버 위치와 관계 없이 일관된 시간 처리가 가능합니다.
- plate verify/match API를 분리해, 카메라 워커·테스트 스크립트 등 다양한 클라이언트가 쉽게 연동 가능합니다.
- 설정(`Settings`)이 환경변수 기반이라, 개발/테스트/운영 환경마다 값을 바꾸기 쉽습니다.

### 5.2 한계
- SQLite는 단일 파일 DB라서 동시 접속이 많은 환경에서는 병목이 될 수 있습니다.
- 관리자 계정과 토큰이 코드/환경변수에 고정되어 있고, 별도의 사용자 관리·권한 시스템(RBAC)이 없습니다.
- 자동 테스트/CI 설정이 코드 안에 포함되어 있지 않아 회귀 테스트 체계가 부족합니다.

## 6. 향후 개선 방향
- DB·마이그레이션
  - Postgres 등 서버형 DB로 이전.
  - Alembic 도입으로 스키마 변경 이력 관리.
- 인증·보안
  - OAuth2/JWT 기반 로그인, 비밀번호 정책, 로그인 실패 횟수 제한, 감사 로그 도입.
  - 관리자와 일반 사용자 역할(Role) 분리 및 세분화.
- 성능·운영
  - 예약 조회 캐싱, 대량 조회용 읽기 전용 엔드포인트 추가.
  - 프로덕션 환경용 uvicorn/gunicorn 설정 및 헬스 체크.

