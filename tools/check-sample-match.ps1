Param(
    [string]$ImagePath = "example.jpg"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $PSCommandPath
$Root = Split-Path -Parent $ScriptDir
$Python = Join-Path $Root '.venv\Scripts\python.exe'

$FullImage = Resolve-Path -LiteralPath $ImagePath -ErrorAction SilentlyContinue
if (-not $FullImage) { throw "Image not found: $ImagePath" }
$ImageName = [System.IO.Path]::GetFileName($FullImage)

if (-not $env:OPENAI_API_KEY) {
    Write-Warning "OPENAI_API_KEY is not set. GPT 기반 인식이 실패할 수 있습니다."
}

Write-Host "[check] Python:" $Python
Write-Host "[check] Image :" $FullImage

if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$Root$([IO.Path]::PathSeparator)$($env:PYTHONPATH)"
} else {
    $env:PYTHONPATH = $Root
}

Push-Location $Root
try {
@"
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import create_app

os.environ.setdefault("PLATE_SERVICE_MODE", "gptapi")

img_path = Path(r"$ImageName")
app = create_app()
client = TestClient(app)

files = {"image": (img_path.name, img_path.read_bytes(), "image/jpeg")}
resp = client.post("/api/license-plates", files=files)
print("[recognition] status:", resp.status_code)
try:
    rec_body = resp.json()
except Exception as exc:  # pylint: disable=broad-except
    print("[recognition] invalid JSON:", exc)
    raise SystemExit(1)
print("[recognition] body:", rec_body)

plate = rec_body.get("plate") if resp.status_code == 200 else None
if not plate:
    print("[match] skipped: no plate")
    raise SystemExit(1)

now_utc = datetime.now(timezone.utc)
payload = {"plate": plate, "timestamp": now_utc.isoformat()}
resp2 = client.post("/api/plates/match", json=payload)
print("[match] ts (UTC):", now_utc)
print("[match] status:", resp2.status_code)
try:
    match_body = resp2.json()
except Exception as exc:  # pylint: disable=broad-except
    print("[match] invalid JSON:", exc)
    raise SystemExit(1)
print("[match] body:", match_body)
"@ | & $Python -
}
finally {
    Pop-Location
}
