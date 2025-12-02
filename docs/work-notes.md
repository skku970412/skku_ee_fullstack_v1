# Work Notes (latest changes)

- Added `tools/check-sample-match.ps1`: PowerShell helper that uploads `example.jpg` (or a given image) via the FastAPI app (TestClient), prints GPT recognition result, and immediately calls `/api/plates/match` with the current UTC timestamp. Requires `OPENAI_API_KEY`. Usage: `.\tools\check-sample-match.ps1`.
- Added `--use-latest` option to `tools/test_plate_match.py` to test DB 최신 예약의 번호판과 중간 시각으로 매칭을 바로 확인.
- Relaxed UTC migration error handling in `backend/app/crud.py` to skip (with warning) when legacy reservations cause unique-constraint conflicts during startup.
- Recent run of `check-sample-match.ps1` (with OPENAI key set) yielded: plate `03두 2902`, `/api/plates/match` → `match: true` for active reservation `13:30~14:30` KST on 2025-11-23.
- Updated `start-manual-capture.ps1`: after successful capture it now reads the latest `camera-capture/reports/report-*.json`; if `match_response.match == true` it auto-runs `start-arduino-workflow.ps1`. Otherwise it exits silently.
