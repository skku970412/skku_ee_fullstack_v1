# 백엔드 요약 (FastAPI)

## 스택·환경
- FastAPI, SQLAlchemy ORM, Pydantic v2, SQLite(기본), uvicorn. 의존성: `backend/requirements.txt`.
- 설정(config.py): DATABASE_URL(기본 `sqlite:///./data/ev_charging.db`), BUSINESS_TIMEZONE(Asia/Seoul), 관리자 이메일/패스워드/토큰, AUTO_SEED_SESSIONS, CORS_ORIGINS, PLATE_SERVICE_MODE(gptapi|http), PLATE_SERVICE_URL, PLATE_OPENAI_MODEL/PROMPT, OPENAI_API_KEY(openai-key.txt 자동 로드).
- 실행: `uvicorn backend.app.main:create_app --factory --reload --host 0.0.0.0 --port 8000`.

## 데이터 모델(models.py)
- ChargingSession(id, name).
- Reservation(id UUID, session_id, plate/plate_normalized, start/end_time(tz-aware), status, contact_email, created_at/updated_at). `derived_status`로 현재 상태 계산.
- ReservationSlot(session_id+slot_start 유니크)로 30분 단위 점유 관리.

## 비즈니스 규칙(crud.py, routers/reservations.py)
- 예약은 09:00~22:00, 30분 단위 시작/종료, 최소 1슬롯.
- 같은 세션의 겹침(ReservationSlot) 및 같은 차량의 시간 겹침을 모두 차단.
- 모든 시간 UTC 저장/비교; startup 시 UTC 마이그레이션 및 슬롯 보정, 기본 4개 세션 자동 시드(AUTO_SEED_SESSIONS).

## 주요 API
- 시스템: GET `/health`
- 사용자:
  - POST `/api/user/login` (임시 토큰)
  - GET `/api/sessions`, GET `/api/reservations/by-session?date=YYYY-MM-DD`
  - POST `/api/reservations` 생성
  - GET `/api/reservations/my?email|plate`, DELETE `/api/reservations/{id}`
  - POST `/api/plates/verify`(겹침·중복 확인), POST `/api/plates/match`(특정 시각 활성 예약 여부)
- 관리자:
  - POST `/api/admin/login`
  - GET `/api/admin/reservations/by-session?date=...`
  - DELETE `/api/admin/reservations/{id}` (Bearer {ADMIN_TOKEN})
- 번호판 인식 프록시(plates.py):
  - POST `/api/license-plates`(신규), `/api/plates/recognize`(레거시)
  - gptapi 모드: OpenAI Responses API + 이미지 data URL; http 모드: PLATE_SERVICE_URL로 multipart 프록시.

## 데이터·운영
- DB 파일: `data/ev_charging.db`(startup 시 테이블 생성/ALTER contact_email). SessionLocal + `check_same_thread=False`(SQLite).
- 예약 시 slot_start 기준 유니크 제약으로 경합 방지; `_lock_session`으로 행 잠금 후 생성.
- 로그/마이그레이션: UTC 변환 시 유니크 충돌은 경고 후 롤백, 슬롯 보강 수행.

## 테스트·도구
- `tools/test_plate_match.py`: GPT 인식+매칭 통합, 최신 예약 활용 옵션(--use-latest) 또는 특정 plate/timestamp.
- `tools/check-sample-match.ps1`: example.jpg로 TestClient 호출→/api/plates/match 연쇄 실행(OPENAI_API_KEY 필요).
