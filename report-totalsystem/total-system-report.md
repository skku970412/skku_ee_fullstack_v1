# EV 무선충전 통합 시스템 기술 보고서

## 1. 개요
- 목적: 차량 번호 기반 예약, 번호판 인식 AI, 주차 감지-충전 HW(아두이노)까지 연결된 무선충전 데모.
- 구성: FastAPI 백엔드 + SQLite, 사용자/관리자 React(Vite) 프런트 2종, 번호판 AI(OPENAI/외부 HTTP), Firebase 연동 카메라 워커(OpenCV), 아두이노 XY 스테이지/충전 제어.

## 2. 시스템 구성(흐름)
- 사용자 프런트(user-front): 로그인(토큰 임시 발급) → 번호 검증/스캔 → 시간/세션 선택 → 예약 생성/조회/취소 → 날씨/요금 표시.
- 관리자 프런트(admin-front): 로그인(고정 크레덴셜) → 날짜별 세션 예약 현황 모니터링, 자동 새로고침, 예약 삭제.
- 백엔드(FastAPI): 예약/검증/매칭 API, 관리자·사용자 인증, 번호판 인식 프록시(GPT API 또는 외부 HTTP), 시간대/슬롯 관리, DB 마이그레이션/시드.
- AI/카메라: camera-capture 워커가 Firebase 신호→웹캠 캡처→AI 인식→/api/plates/match 호출→Firebase/시리얼로 결과 전달, 모든 시도 JSON 리포트 기록.
- HW: total_system.ino(아두이노)에서 시리얼 트리거 수신 시 LED/서보/초음파로 정렬 후 충전 시나리오 수행.

## 3. 백엔드(FastAPI, backend/app)
- 스택: FastAPI, SQLAlchemy ORM, Pydantic v2, SQLite(기본), uvicorn. 요구사항은 backend/requirements.txt.
- 설정(config.py): DATABASE_URL, BUSINESS_TIMEZONE(기본 Asia/Seoul), ADMIN_EMAIL/PASSWORD/TOKEN, AUTO_SEED_SESSIONS, CORS_ORIGINS, PLATE_SERVICE_MODE(gptapi|http), PLATE_SERVICE_URL, PLATE_OPENAI_MODEL/ PROMPT, OPENAI_API_KEY(openai-key.txt 자동 로드).
- 데이터 모델(models.py):
  - ChargingSession(id, name)
  - Reservation(id UUID, session_id, plate/plate_normalized, start/end_time tz-aware, status, contact_email, created/updated)
  - ReservationSlot(session_id+slot_start 유니크)로 30분 단위 슬롯 점유 관리.
  - derived_status가 현재 시각 기준 CONFIRMED/IN_PROGRESS/COMPLETED/ CANCELLED 판정.
- 비즈니스 규칙(crud.py, routers/reservations.py):
  - 운영시간 09:00~22:00, 30분 배수 시작/종료만 허용, 최소 1슬롯.
  - 동일 세션 겹침 방지(uq session_id+slot_start) + 차량 번호 중복 방지(시간 겹침 시 에러).
  - 모든 시간은 UTC로 저장/비교하며 startup 시 UTC 마이그레이션 및 예약 슬롯 보정, 기본 4개 세션 자동 시드.
- 주요 API:
  - 시스템: GET /health
  - 사용자: POST /api/user/login(임시 토큰 발급)
  - 예약 조회/생성: GET /api/sessions, GET /api/reservations/by-session?date=YYYY-MM-DD, POST /api/reservations, GET /api/reservations/my(email|plate), DELETE /api/reservations/{id}
  - 번호판 검증·매칭: POST /api/plates/verify(중복/겹침 확인), POST /api/plates/match(특정 시각의 활성 예약 여부)
  - 관리자: POST /api/admin/login, GET /api/admin/reservations/by-session, DELETE /api/admin/reservations/{id} (Bearer {ADMIN_TOKEN})
  - 번호판 인식 프록시(plates.py): POST /api/license-plates(신규) /api/plates/recognize(레거시). PLATE_SERVICE_MODE=gptapi 시 OpenAI Responses API로 data URL 전송, http 모드 시 PLATE_SERVICE_URL로 파일 프록시.
- DB: 기본 `data/ev_charging.db`. SessionLocal + contextmanager session_scope. SQLite check_same_thread=False 적용.

## 4. 프런트엔드
### 공통
- Vite + React 18 + TypeScript, TailwindCSS, framer-motion, lucide-react. API_BASE는 VITE_API_BASE 또는 현재 호스트:8000.

### 사용자 화면(user-front/src)
- 흐름: 허브 메뉴 ↔ 로그인 → 번호 입력/검증 → 가용 슬롯 확인 후 예약 → 결과 공유 → 내 예약 조회/취소.
- 기능:
  - 번호 검증: 한국 번호판 정규식, 백엔드 /api/plates/verify, 기존 예약 히스토리 조회(/api/reservations/my?plate).
  - 스케줄링: 세션 4개, 날짜 +-3~10일 가용률 스트립 표시(여러 날짜 /api/reservations/by-session 호출 후 점유 집계), 30분 슬롯 선택, 종료시간 자동 계산, 22시 초과 방지.
  - 예약 CRUD: create, 내 예약 리스트/상세, 단건·전체 취소.
  - 스캐너: getUserMedia로 웹캠 캡처 → /api/license-plates 업로드 → plate 입력 자동 채움.
  - 부가 UX: Stepper 진행, 허브 메뉴(예약/내 예약/요금표 토글), 요금 견적(분당 100원), 날씨 위젯(open-meteo API), 상태 애니메이션.
- 에러 처리: fetch 공통 extractError, 경고/로딩 상태 관리, confirm 삭제.

### 관리자 화면(admin-front/src)
- 로그인 후 Bearer 토큰으로 /api/admin/... 호출, 날짜 선택/자동 새로고침(15s 토글), 2열 카드/1열 리스트 전환.
- KPI: 총 예약 건수, 진행 중, 단순 점유율(예약 수 기반 가중치 1.7 슬롯).
- 세션 카드: 혼잡도 배지, 진행/다음 예약, 테이블(예약/이메일/상태/진행도), 예약 삭제.
- UI: framer-motion 전환, Tailwind 카드/토글/ProgressBar 등 자체 컴포넌트.

## 5. AI·카메라·연동
- 번호판 인식(plates.py):
  - gptapi 모드: OpenAI Responses API, 입력은 텍스트 프롬프트+이미지 data URL, 결과 텍스트만 반환(raw 포함).
  - http 모드: multipart/form-data를 PLATE_SERVICE_URL로 프록시, 응답을 그대로 전달.
- plate match: /api/plates/match가 예약 테이블에서 UTC 기준 활성 창(start<=ts<end) 여부 확인 후 match/reservation 반환.
- 카메라 워커(camera-capture/main.py):
  - Firebase 신호 감시(관리자 SDK or REST): car_on_parkinglot 값이 expected_value일 때 동작, timestamp path 읽기.
  - 카메라: pygrabber로 장치명 힌트 검색, OpenCV 캡처·JPEG 저장, warmup 지원.
  - AI 호출: --recognition-url(기본 /api/license-plates)로 파일 업로드, 결과 plate 추출.
  - 매칭: --match-url(기본 /api/plates/match)로 plate+timestamp 전송, 결과 로그.
  - 시리얼 트리거: match true 시 지정 포트로 메시지(기본 START\n) 송신 → 아두이노 워크플로 시작.
  - Firebase 업데이트: car_plate_same에 ok/no 기록. 모든 사이클 결과를 camera-capture/reports/report-*.json에 저장.
  - 실행 옵션: --skip-firebase, --continuous/--cycle-interval, --list-cameras, --credentials/--database-url, timeouts 등. README.md에 요약.
- 테스트/유틸(tools):
  - test_plate_match.py: GPT 인식+매칭 통합 테스트 또는 특정 번호/타임스탬프 강제, 최신 예약 활용 옵션(--use-latest).
  - check-sample-match.ps1: example.jpg로 TestClient 호출해 인식→/api/plates/match 연쇄 실행(OPENAI_API_KEY 필요).

## 6. 하드웨어·기타 자동화
- total_system/total_system.ino:
  - 하드웨어: 서보 2축(핀 9/10), 초음파 3개(TRIG/ECHO 좌/우/정면), 전류 센서(A0), RGB LED, LCD I2C.
  - 상태 머신: S00 신호대기(시리얼 입력) → S01 목표 충전량 입력 → S1 승인 대기(10s LED R) → S2 승인완료(5s LED G) → S3 정렬(초음파 거리 기반 각도 계산, 보정 범위 제한) → S4 충전(전류적분 mAh, 목표 도달 또는 타임아웃) → S5 완료(서보 홈 복귀 후 초기화).
  - 캘리브레이션 계수 AX/BX, AY/BY 및 서보 가동 범위 상수화. 시리얼 신호만 오면 워크플로 시작하므로 카메라 워커 시리얼 트리거와 연동 가능.
- run.ps1:
  - setup.ps1 실행 후 백엔드 uvicorn --reload, 두 프런트 npm run dev --host 병렬 기동. RUN_CAMERA_WORKER=1 시 camera-capture/main.py 추가 실행.
  - 자동 환경: AUTO_SEED_SESSIONS=1, CORS_ORIGINS(로컬 IP/포트 조합), VITE_API_BASE(첫 번째 로컬 IP:8000), PLATE_SERVICE_URL 기본 /api/license-plates, openai-key.txt 자동 로드.
- 기타 스크립트: start-manual-capture.*(firebase 없이 단발 캡처→match 결과 ok면 start-arduino-workflow.* 호출), send-serial-trigger.* 등.

## 7. 데이터·운영 메모
- DB 위치: `data/ev_charging.db`(SQLite). 예약/슬롯/세션 자동 생성 및 마이그레이션으로 초기 상태 보정.
- 기본 관리자: admin@demo.dev / admin123, 토큰 admin-demo-token.
- 타임존: 비즈니스 시간대 Asia/Seoul, 내부 저장 UTC.
- OPENAI_API_KEY: 환경변수 우선, 없으면 루트 openai-key.txt 읽음. PLATE_SERVICE_MODE=http 시 외부 인식 서비스 필요.
- 빌드: npm run build(각 프런트), uvicorn 배포 시 factory(create_app) 사용. camera-capture는 backend requirements와 동일 venv 사용.

## 8. 진단/시험 포인트
- API 상태: /health, /api/reservations/by-session, /api/plates/verify/match로 기본 동작 확인.
- AI 경로: PLATE_SERVICE_MODE=gptapi 시 OpenAI 키 필수, http 모드 시 PLATE_SERVICE_URL 점검.
- 워커: --skip-firebase + --recognition-url http://localhost:8000/api/license-plates 로 로컬 단발 테스트, reports/*.json 내용 확인.
- HW: 시리얼 메시지 수신만으로 흐름 시작되므로 PC->아두이노 케이블/포트 확인, 서보 캘리브레이션 상수 조정 필요 시 AX/BX/AY/BY 수정.
