# Plate Match API 검증 보고

## 목적
- `POST /api/plates/match` 엔드포인트가 탐지된 차량 번호와 Firebase의 타임스탬프를 받아 예약과 정확히 비교하는지 확인합니다.

## 테스트 방법
1. 임시 SQLite DB(`sqlite:///./data/test_worker.db`)로 백엔드를 부팅하지 않고, FastAPI `TestClient`를 이용한 단위 테스트를 수행했습니다.
2. 테스트 스크립트 개요:
   - `models.Base.metadata.drop_all()` 후 `create_all()`로 깨끗한 스키마 생성
   - `crud.ensure_base_sessions(session, names=['T1'])`로 기본 세션 삽입
   - 현재 시각~+90분 동안 `crud.create_reservation()`을 사용해 예약 생성 (차량번호 `12가3456`)
   - `client.post('/api/plates/match', json={...})`로 세 가지 시나리오 호출
     1. **예약 시간 내부** (`timestamp = start`): `match=True`와 예약 정보 반환
     2. **예약 끝난 이후** (`timestamp = end + 5분`): `match=False`
     3. **다른 번호판** (`plate = 99가9999`): `match=False`
3. 테스트 실행 커맨드:
   ```powershell
   python _temp_match_test.py  # 위 스크립트를 임시 파일로 저장 후 실행
   ```
   실행 결과 로그:
   ```
   match response (should be true): 200 {..., "match": true, ...}
   match response (outside window): 200 {..., "match": false, ...}
   match response (wrong plate): 200 {..., "match": false, ...}
   ```

## 결론
- `plates/match` 엔드포인트가 예약 시간대 및 번호판을 정확히 판별하며, 조건을 벗어나면 `match=False`로 떨어지는 것을 확인했습니다.
- 워커(`camera-capture/main.py`)가 AI 인식 결과와 Firebase 타임스탬프를 백엔드에 전달하면, 해당 응답을 기반으로 `signals/car_plate_same` 값을 업데이트할 수 있습니다.
