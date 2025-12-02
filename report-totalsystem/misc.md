# 기타/운영 메모

## 하드웨어(total_system/total_system.ino)
- 구성: 서보 2축(핀 9/10), 초음파 3개(TRIG/ECHO 좌/우/정면), 전류 센서 A0, RGB LED(11/12/13), I2C LCD.
- 상태 머신: 신호대기(S00, 시리얼) → 목표 충전량 입력(S01) → 승인 대기(S1, LED R 10s) → 승인 완료(S2, LED G 5s) → 정렬(S3, 초음파 거리→서보 각도, 보정) → 충전(S4, 전류 적분 mAh, 목표 도달/타임아웃) → 완료(S5, 서보 홈 복귀 후 초기화).
- 캘리브레이션: AX/BX, AY/BY 선형식으로 거리→각도 변환, `SERVO_MIN/MAX`로 안전 범위 제한. 시리얼 수신만으로 시작하므로 PC/워커의 시리얼 트리거와 연동.

## 실행·자동화 스크립트
- `run.ps1`: setup.ps1 호출 후 uvicorn(reload) + user-front/admin-front `npm run dev -- --host` 병렬 실행. 환경 자동: AUTO_SEED_SESSIONS=1, 로컬 IP 기반 CORS_ORIGINS, VITE_API_BASE 결정, openai-key.txt 로드, 기본 PLATE_SERVICE_URL=/api/license-plates. `RUN_CAMERA_WORKER=1` + `CAMERA_WORKER_ARGS` 설정 시 카메라 워커 추가 기동.
- 수동 캡처: `start-manual-capture.ps1/.bat` → camera-capture/main.py `--skip-firebase`, 결과 보고 후 match 성공 시 `start-arduino-workflow.ps1` 실행.
- 시리얼 트리거: `send-serial-trigger.*`로 아두이노 플로우 수동 시작 가능.

## 데이터/환경
- DB: `data/ev_charging.db`(SQLite). startup 시 테이블 생성 및 `reservations` contact_email 컬럼 추가 검사.
- 기본 관리자: `admin@demo.dev / admin123`, 토큰 `admin-demo-token`.
- 타임존: 비즈니스 Asia/Seoul, 저장·비교는 UTC.
- OPENAI_API_KEY: 환경변수 우선, 없으면 `openai-key.txt` 자동 로드. PLATE_SERVICE_MODE=http 사용 시 외부 인식 서비스 필요.

## 문서/참고
- `docs/plate-service.md`: 인식 서비스 프록시/구성.
- `docs/plate-match-verification.md`: `/api/plates/match` 검증 테스트 절차.
- `docs/work-notes.md`: 최근 변경/헬퍼 스크립트 메모.
