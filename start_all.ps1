Param(
    [string]$RecognitionUrl,
    [string]$MatchUrl,
    [int]$StartupWaitSeconds = 10,
    [int]$BackendPort = 8001
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSCommandPath
$RunScript = Join-Path $Root 'run.ps1'
$TestScript = Join-Path $Root 'run_test.ps1'
$KeyFile = Join-Path $Root 'openai-key.txt'

$env:BACKEND_PORT = $BackendPort

$effectiveRecognition = if ($RecognitionUrl) { $RecognitionUrl } else { "http://localhost:$BackendPort/api/license-plates" }
$effectiveMatch = if ($MatchUrl) { $MatchUrl } else { "http://localhost:$BackendPort/api/plates/match" }

if (-not (Test-Path $RunScript)) { throw "run.ps1 not found at $RunScript" }
if (-not (Test-Path $TestScript)) { throw "run_test.ps1 not found at $TestScript" }

if (-not $env:OPENAI_API_KEY -and (Test-Path $KeyFile)) {
    $env:OPENAI_API_KEY = (Get-Content -LiteralPath $KeyFile -Raw).Trim()
    Write-Host "[start_all] Loaded OPENAI_API_KEY from openai-key.txt"
}

if (-not $env:OPENAI_API_KEY) {
    Write-Warning "[start_all] OPENAI_API_KEY is not set. GPT plate recognition will fail until you set it."
}

function Stop-PortProcess {
    param([int]$Port)
    $proc = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty OwningProcess
    if ($proc) {
        Write-Host "[start_all] Stopping process on port $Port (PID $proc)"
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
    }
}

# Ensure no stale uvicorn on 8000
Stop-PortProcess -Port $BackendPort

Write-Host "[start_all] Launching run.ps1 (backend + frontends)..."
$runProc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $RunScript -WorkingDirectory $Root -WindowStyle Minimized -PassThru

Write-Host "[start_all] Waiting $StartupWaitSeconds seconds for services to start..."
Start-Sleep -Seconds $StartupWaitSeconds

# Quick health probe
try {
    $health = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$BackendPort/docs" -Method Get -TimeoutSec 5
    Write-Host ("[start_all] Backend reachable, status {0}" -f $health.StatusCode)
} catch {
    Write-Warning "[start_all] Backend health probe failed; continuing anyway."
}

Write-Host "[start_all] Running test capture/match..."
& $TestScript -RecognitionUrl $effectiveRecognition -MatchUrl $effectiveMatch @Args
$testExit = $LASTEXITCODE
Write-Host "[start_all] run_test.ps1 exited with $testExit"

Write-Host "[start_all] Servers (run.ps1) are still running (PID $($runProc.Id)). Stop manually with Ctrl+C in that window or Stop-Process -Id $($runProc.Id)."
exit $testExit
