# 카메라 워커 사용 빠른 안내

## 기본 개념
- 모드(pipeline-mode)
  - `gpt`(기본): 인식/매칭만 실행. 업로드·RTDB는 사용 안 함.
  - `storage`: 인식/매칭 없이 스토리지 업로드만.
  - `both`: 인식/매칭 + 스토리지 업로드 모두 실행. 번호판 선택 우선순위는 **보조 인식 → 기본 인식(GPT/HTTP) → RTDB 값**.
- 업로드 스위치: `--upload-to-storage` 또는 `AUTO_UPLOAD_TO_STORAGE=1` (단, `pipeline-mode=gpt`에선 무시).
- RTDB 후보: `--rtdb-plate-path`로 지정하면 해당 경로의 plate 값을 후보로 사용.
- 인식기는 기본 `--recognition-url`(GPT/HTTP). 보조 인식기를 쓰려면 `--secondary-recognition-url` 지정.

## 필수 준비
- 서비스 계정 키: `GOOGLE_APPLICATION_CREDENTIALS`에 JSON 경로 설정  
  예) `D:\종설_gpt_plus_server\storage_key\plate-detection-b7ac6-firebase-adminsdk-fbsvc-53e6880d0a.json`
- 스토리지 버킷/프리픽스는 `camera-capture/storage.env`에 기본값 있음  
  (`plate-detection-b7ac6.firebasestorage.app`, `uploads`)

## 예시 실행
### 1) 인식만 (기본)
```powershell
python camera-capture/main.py --pipeline-mode gpt
```

### 2) 업로드만
```powershell
python camera-capture/main.py --pipeline-mode storage --upload-to-storage
```

### 3) 인식+업로드+RTDB 후보 병합 (GPT 우선)
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS='D:\종설_gpt_plus_server\storage_key\plate-detection-b7ac6-firebase-adminsdk-fbsvc-53e6880d0a.json'
python camera-capture/main.py `
  --pipeline-mode both `
  --upload-to-storage `
  --recognition-url http://127.0.0.1:8000/api/license-plates `
  --match-url http://127.0.0.1:8000/api/plates/match `
  --rtdb-plate-path "/plate-detected-now" `
  --rtdb-timestamp-field "timestamp"
```
- 보조 인식기 우선 사용하려면 `--secondary-recognition-url http://...` 추가.
- 업로드 기본 ON으로 두고 싶으면 `AUTO_UPLOAD_TO_STORAGE=1` 설정.

## start_all.ps1로 한 번에 돌릴 때
기본은 `pipeline-mode=gpt`라 업로드·RTDB를 사용하지 않습니다. 실행 시 뒤에 인자를 붙여 전달하세요:
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS='D:\종설_gpt_plus_server\storage_key\plate-detection-b7ac6-firebase-adminsdk-fbsvc-53e6880d0a.json'
.\start_all.ps1 `
  --pipeline-mode both `
  --upload-to-storage `
  --rtdb-plate-path "/plate-detected-now" `
  --rtdb-timestamp-field "timestamp"
```

## 번호판 선택 우선순위
1) 보조 인식기(`secondary-recognition-url`) 결과
2) 기본 인식기(`recognition-url`, GPT/HTTP)
3) RTDB(`rtdb-plate-path`) 값

매칭(`/api/plates/match`)과 RTDB 업데이트는 `pipeline-mode`가 `gpt` 또는 `both`이고, plate가 선택된 경우에만 실행됩니다.
