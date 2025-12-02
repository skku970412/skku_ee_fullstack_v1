# AI / 워커 요약

## 번호판 인식(plates.py, FastAPI)
- 엔드포인트: POST `/api/license-plates`(주요), `/api/plates/recognize`(레거시).
- 모드:
  - `gptapi`: OpenAI Responses API 사용. 입력: 텍스트 프롬프트 + 이미지 data URL. 반환: plate 텍스트와 raw output.
  - `http`: multipart/form-data를 `PLATE_SERVICE_URL`로 프록시, 응답 그대로 전달.
- 설정: `PLATE_SERVICE_MODE`, `PLATE_SERVICE_URL`, `PLATE_OPENAI_MODEL`, `PLATE_OPENAI_PROMPT`, `OPENAI_API_KEY`.

## 번호판 매칭(/api/plates/match)
- 입력: plate, timestamp(ISO/epoch/Date 객체 등). UTC로 변환 후 `start_time <= ts < end_time`인 활성 예약을 조회.
- 응답: `{ match: bool, reservation?: ReservationPublic }`. 예약 없거나 시간 범위 밖이면 match=false.

## 카메라 워커(camera-capture/main.py)
- 역할: Firebase 신호 수신 → 웹캠 캡처(JPEG) → AI 인식 요청 → /api/plates/match 호출 → 결과를 Firebase/시리얼로 전달, 리포트 JSON 기록.
- 실행 예: `python main.py --credentials <svc.json> --database-url https://<proj>.firebaseio.com`
- 주요 옵션:
  - Firebase: `--signal-path`(기본 `/signals/car_on_parkinglot`), `--expected-signal-value`, `--timestamp-path`, `--match-path`, `--auth-mode`(admin/rest), `--rest-auth-token`, `--skip-firebase`(로컬 테스트).
  - 카메라: `--camera-name`(pygrabber로 장치 검색), `--camera-index`, `--warmup-seconds`, `--list-cameras`.
  - AI 호출: `--recognition-url`(기본 /api/license-plates), `--recognition-timeout`.
  - 매칭: `--match-url`(기본 /api/plates/match), `--match-timeout`.
  - 시리얼 트리거: `--serial-port`, `--serial-baudrate`, `--serial-message`(기본 START), `--serial-no-newline`, `--serial-wait`, `--serial-timeout`.
  - 반복: `--continuous`, `--cycle-interval`; 단발 테스트는 기본 단일 사이클.
- 리포트: `camera-capture/reports/report-*.json`에 인식/매칭/시리얼/Firebase 결과 저장.
- 예외 처리: AI/매칭 실패 시 메시지 로그, Firebase 업데이트 실패도 보고.

## 테스트/헬퍼
- `tools/test_plate_match.py`: GPT 인식→매칭 통합 검사 또는 plate/timestamp 강제. `--use-latest`로 최신 예약 활용.
- `tools/check-sample-match.ps1`: example.jpg를 TestClient로 업로드 후 즉시 `/api/plates/match` 호출(OPENAI_API_KEY 필요).
- `start-manual-capture.ps1/.bat`: Firebase 없이 캡처→AI→매칭; match 성공 시 `start-arduino-workflow.ps1` 자동 호출.
