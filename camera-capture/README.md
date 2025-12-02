# Camera Capture Worker

This worker listens to the Firebase signal (`/signals/car_on_parkinglot`), captures a frame with the C270 webcam, and forwards the saved image to the AI license-plate service. Every attempt writes a JSON report under `camera-capture/reports` so that results can be reviewed later.

```powershell
.\.venv\Scripts\activate
cd camera-capture
python main.py --credentials <service-account.json> --database-url https://<project>.firebaseio.com
```

Key options:

- `--recognition-url` / `--recognition-timeout`: target AI endpoint and HTTP timeout.
- `--timestamp-path` / `--match-path`: Firebase paths for the detection timestamp and match result (defaults: `/signals/timestamp`, `/signals/car_plate_same`).
- `--match-url` / `--match-timeout`: backend endpoint that verifies whether the recognized plate matches a live reservation.
- `--report-dir`: where to store JSON reports (default `camera-capture/reports`).
- `--continuous` with `--cycle-interval`: keep the worker running like a service.
- `--skip-firebase`: bypass Firebase waiting for quick tests.
- All previous knobs (`--signal-path`, `--camera-name`, `--output-path`, etc.) are still available.
- `--serial-port` / `--serial-baudrate` / `--serial-message`: when a reservation match succeeds, send a trigger string (defaults to `START\n`) to an attached serial device (e.g., the Arduino sketch in `total_system.ino`, which begins operation whenever any serial byte arrives). Fine-tune with `--serial-wait`, `--serial-timeout`, and `--serial-no-newline`.

Dependencies (`firebase-admin`, `opencv-python`, `pygrabber`, `requests`) already live in `backend/requirements.txt`, so `pip install -r backend/requirements.txt` inside the shared `.venv` is sufficient.

## Firebase Storage upload defaults
- Bucket and prefix for uploads are stored in `camera-capture/storage.env`:
  - `FIREBASE_STORAGE_BUCKET=plate-detection-b7ac6.firebasestorage.app`
  - `FIREBASE_STORAGE_PREFIX=uploads`
- Load these before running if you want captures to be pushed to this bucket:
  ```powershell
  $env:FIREBASE_STORAGE_BUCKET = "plate-detection-b7ac6.firebasestorage.app"
  $env:FIREBASE_STORAGE_PREFIX = "uploads"
  python main.py --upload-to-storage --credentials <service-account.json> --database-url https://<project>.firebaseio.com
  ```
  Add other flags as needed (`--recognition-url`, `--match-url`, etc.).
- `camera-capture/storage.env` is auto-loaded on start. If you want uploads on by default, set `AUTO_UPLOAD_TO_STORAGE=1` in the env (or in `storage.env`), so you can omit `--upload-to-storage`.
- Pipeline modes (`--pipeline-mode` or `PIPELINE_MODE` env):
  - `gpt` (default): 인식/매칭만 수행, 업로드 플래그는 무시.
  - `storage`: 인식/매칭 스킵, 업로드만 수행.
  - `both`: 인식+업로드 둘 다 수행. `--secondary-recognition-url`가 있으면 그 결과 plate가 우선 적용됨.
  - RTDB plate 후보를 같이 보고 싶으면 `--rtdb-plate-path` 지정(예: `/plate-detected-now`). 후보 우선순위: secondary → primary(GPT/HTTP) → RTDB.

## Manual trigger helper (Windows)

- Double-click `../start-manual-capture.bat` (or run `.\start-manual-capture.bat` from the repo root) for a one-off capture. It uses the shared `.venv`, calls `camera-capture/main.py --skip-firebase`, and saves the photo under `captured/manual-<timestamp>.jpg`.
- Need extra flags? Run the PowerShell script directly: `.\start-manual-capture.ps1 --recognition-url http://... --match-url http://...`.

`run.ps1`와 함께 자동 실행하려면 환경 변수 `RUN_CAMERA_WORKER=1` 그리고 원하는 인자를 담은 `CAMERA_WORKER_ARGS`(예: `--credentials ... --database-url ...`)를 설정한 뒤 `.\run.ps1`을 실행하세요.
