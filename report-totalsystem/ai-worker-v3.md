# AI · 카메라 워커 기술 보고서 v3

## 1. 역할과 범위
- 이 영역은 두 부분으로 나뉩니다.
  1. 번호판 인식 API(백엔드 `plates.py`): 이미지 파일을 받아 번호판 문자열로 바꾸는 역할.
  2. 카메라 워커(`camera-capture/main.py`): Firebase 신호를 감지해 사진을 찍고, 번호판 인식 및 예약 매칭을 수행한 뒤, 결과에 따라 아두이노를 제어하는 역할.
- 목표: “현장에서 어떤 센서가 차량 도착을 알려주면, 사람이 개입하지 않고도 번호판을 읽고 예약 여부를 판단할 수 있는 자동 파이프라인”을 만드는 것입니다.

## 2. 번호판 인식 API 구조(plates.py)
### 2.1 엔드포인트
- `POST /api/license-plates`
  - 메인 엔드포인트. `image` 필드에 이미지 파일을 담은 `multipart/form-data` 요청을 받습니다.
  - 내부 설정에 따라 OpenAI 기반 인식(GPTAPI) 또는 외부 HTTP 서비스 프록시 모드를 선택합니다.
- `POST /api/plates/recognize`
  - 이전 버전에서 사용하던 엔드포인트로, 현재는 호환성을 위해 유지됩니다.

### 2.2 GPTAPI 모드(`plate_service_mode=gptapi`)
- 흐름:
  1. 업로드된 이미지를 읽어 bytes로 확보합니다.
  2. 파일 포맷을 추정해 `data:image/jpeg;base64,...` 형태의 data URL로 변환합니다.
  3. `plate_openai_prompt`에 저장된 한글/영문 혼합 프롬프트와 함께 OpenAI Responses API에 요청합니다.
  4. 응답의 텍스트 결과를 `plate` 값으로 사용합니다.
- 설계 이유:
  - OpenAI를 사용하면 인식 엔진을 자체 개발하지 않고도 높은 정확도를 기대할 수 있습니다.
  - 프롬프트를 환경설정으로 빼두어, 번호판 형식이나 응답 포맷 요구사항을 쉽게 조정할 수 있습니다.

### 2.3 HTTP 프록시 모드(`plate_service_mode=http`)
- 흐름:
  1. `PLATE_SERVICE_URL` 환경변수에서 외부 번호판 인식 서비스 주소를 읽습니다.
  2. 동일한 `multipart/form-data` 형식으로 이미지를 이 서비스에 전달합니다.
  3. 응답을 그대로 클라이언트에 전달하되, Content-Type과 일부 헤더(Cache-Control, ETag 등)만 조정합니다.
- 설계 이유:
  - 현장에 이미 구축된 번호판 인식 서버가 있는 경우, 백엔드 API를 바꾸지 않고도 쉽게 연동할 수 있도록 하기 위함입니다.

## 3. 번호판 매칭 API 구조(/api/plates/match)
### 3.1 목적
- 카메라 워커가 “이 번호판이 이 시간에 촬영되었다”는 정보를 보내면, 백엔드는 “이 차량이 지금 예약된 상태인지”를 알려줍니다.

### 3.2 입력과 처리
- 입력(JSON):
  - `plate`: 인식된 번호판 문자열.
  - `timestamp`: 촬영 시각(ISO 문자열, Unix 타임 등 다양한 형태 지원).
- 처리:
  - `PlateMatchRequest` 스키마에서 `timestamp`를 파싱하고, 필요하면 UTC로 변환합니다.
  - `crud.find_active_reservation_by_plate`를 사용해:
    - 같은 차량(normalized plate)이며,
    - 상태가 CANCELLED가 아니고,
    - `start_time <= timestamp < end_time` 범위 안에 있는 예약을 찾습니다.
- 출력(JSON):
  - `match`: 예약이 있으면 `true`, 없으면 `false`.
  - `reservation`: `match=true`일 때 해당 예약의 요약 정보.

## 4. 카메라 워커 구조(camera-capture/main.py)
### 4.1 주요 책임
1) Firebase에서 차량 도착 신호 감지.
2) USB 카메라로 사진 캡처.
3) 번호판 인식 API 호출.
4) 예약 매칭 API 호출.
5) 결과에 따라 Firebase에 상태 기록, 필요 시 시리얼 포트를 통해 아두이노에 신호 전송.
6) 위 과정을 보고서(JSON 파일)로 기록.

### 4.2 Firebase 연동
- 모드:
  - `admin` 모드: 서비스 계정 JSON을 사용해 Firebase Admin SDK로 연결.
  - `rest` 모드: HTTP REST API로 Realtime Database에 접근.
- 주요 경로:
  - `signal_path` (기본 `/signals/car_on_parkinglot`): 차량 도착을 나타내는 신호 값이 저장되는 위치.
  - `timestamp_path` (기본 `/signals/timestamp`): 차량이 감지된 시각을 기록하는 위치.
  - `match_path` (기본 `/signals/car_plate_same`): 예약 매칭 결과를 기록하는 위치(`ok`/`no`).
- 흐름:
  1. `wait_for_signal_admin/rest` 함수가 `signal_path`의 값이 설정된 `expected_value`로 바뀔 때까지 polling 합니다.
  2. 시간 초과(`timeout`)가 설정되어 있는 경우, 일정 시간 안에 신호가 오지 않으면 종료합니다.
  3. 신호 수신 후 `timestamp_path`에서 발견된 시각 값을 읽어 `parse_timestamp_value`로 파싱합니다.

### 4.3 카메라 캡처
- `find_camera_index_by_name`:
  - `pygrabber`를 사용해 DirectShow 장치 목록을 가져오고, 이름에 특정 문자열(예: “C270”)이 포함된 장치를 탐색합니다.
  - 찾으면 해당 인덱스를 사용하고, 없으면 기본 인덱스(`--camera-index`)를 사용합니다.
- `capture_photo`:
  - OpenCV `VideoCapture`를 사용해 카메라를 열고, warmup 시간 동안 기다린 뒤 한 프레임을 읽습니다.
  - 읽은 프레임을 JPEG로 인코딩해 지정된 경로(`output_path`)에 저장합니다.

### 4.4 번호판 인식 및 예약 매칭
- `recognize_plate_http`:
  - `--recognition-url`(기본: 백엔드 `/api/license-plates`)로 이미지 파일을 업로드합니다.
  - 성공 시 JSON 응답을 반환하고, 실패 시 에러 메시지 문자열을 반환합니다.
- `match_plate_http`:
  - `--match-url`(기본: 백엔드 `/api/plates/match`)로 번호판 문자열 및 타임스탬프를 보내 예약 매칭 결과를 가져옵니다.
  - 성공 시 JSON 응답과 `match` 결과를 기록합니다.

### 4.5 시리얼 트리거와 보고서 기록
- `trigger_serial_device`:
  - `pyserial`을 사용해 지정된 포트(예: `COM5`)를 열고, 메시지(기본 `"START"` + 개행)를 전송합니다.
  - `serial-wait`만큼 대기 후 데이터를 쓰고, 예외가 발생하면 에러 메시지를 반환합니다.
- `write_report`:
  - 한 번의 사이클에 대한 모든 결과(인식 성공/실패, 인식된 번호판, 매칭 결과, 시리얼 전송 결과, Firebase 기록 상태 등)를 JSON으로 묶습니다.
  - `camera-capture/reports/report-YYYYMMDD-HHMMSS-fff.json` 형태의 파일로 저장합니다.

## 5. 설계 상 강점과 한계
### 5.1 강점
- 인식 → 매칭 → 시리얼 트리거 → 리포트 저장이라는 일련의 흐름이 하나의 사이클로 명확하게 구성되어 있습니다.
- 워커는 Firebase `admin`과 `rest` 두 방식 모두를 지원하여, 운영 환경에 따라 적절한 연결 방법을 선택할 수 있습니다.
- OpenAI 기반 인식과 외부 HTTP 인식 서비스 둘 다 지원하므로, 환경 제약에 따라 유연하게 구성 가능합니다.
- 각 사이클 결과를 JSON 파일로 남겨, 개발/운영 시 문제 원인을 쉽게 추적할 수 있습니다.

### 5.2 한계
- 워커는 장기간 실행 시 예외 상황(네트워크 단절, 카메라 장애 등)에 대한 자동 복구 로직이 제한적입니다.
- OpenAI 모드에서는 인터넷 연결과 API 비용에 대한 리스크가 존재합니다.
- 매칭/인식 API에 인증이 없으므로, 인터넷에 직접 노출하면 보안에 취약할 수 있습니다(역프록시/방화벽 추가 필요).

## 6. 향후 개선 방향
- 안정성:
  - 워커를 시스템 서비스 또는 Docker 컨테이너로 운영하고, 헬스 체크·자동 재시작·백오프 정책을 도입합니다.
  - 카메라·Firebase·백엔드와의 연결 문제를 단계별로 감지하고, 재시도/알림 로직을 추가합니다.
- 인식 엔진:
  - ONNX/YOLO 기반 로컬 번호판 인식 모델을 도입하여, 네트워크 의존성을 줄이고 응답 속도를 개선합니다.
  - 인식 결과 품질(정확도, 오탐지율)을 측정하는 테스트 스위트를 마련합니다.
- 보안:
  - 인식·매칭 API에 인증 토큰 또는 IP 화이트리스트를 적용합니다.
  - 워커와 백엔드 사이 트래픽에 HTTPS를 적용하고, 키 관리 정책을 명확히 합니다.

