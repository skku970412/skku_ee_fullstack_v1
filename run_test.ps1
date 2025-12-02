Param(
    [string]$RecognitionUrl,
    [string]$MatchUrl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSCommandPath
$ManualScript = Join-Path $Root 'start-manual-capture.ps1'
$KeyFile = Join-Path $Root 'openai-key.txt'

if (-not (Test-Path $ManualScript)) {
    throw "start-manual-capture.ps1 not found at $ManualScript"
}

if (-not $env:OPENAI_API_KEY -and (Test-Path $KeyFile)) {
    $env:OPENAI_API_KEY = (Get-Content -LiteralPath $KeyFile -Raw).Trim()
    Write-Host "[run_test] Loaded OPENAI_API_KEY from openai-key.txt"
}

if (-not $env:OPENAI_API_KEY) {
    Write-Warning "[run_test] OPENAI_API_KEY is not set. GPT-based recognition will fail."
}

$backendPort = 8000
if ($env:BACKEND_PORT) {
    if ([int]::TryParse($env:BACKEND_PORT, [ref]([int]$null))) {
        $backendPort = [int]$env:BACKEND_PORT
    }
}

$effectiveRecognition = if ($RecognitionUrl) { $RecognitionUrl } else { "http://localhost:$backendPort/api/license-plates" }
$effectiveMatch = if ($MatchUrl) { $MatchUrl } else { "http://localhost:$backendPort/api/plates/match" }

Write-Host "[run_test] Recognition URL: $effectiveRecognition"
Write-Host "[run_test] Match URL       : $effectiveMatch"

& $ManualScript --recognition-url $effectiveRecognition --match-url $effectiveMatch @Args
$ExitCode = $LASTEXITCODE
Write-Host "[run_test] Finished with exit code $ExitCode"
exit $ExitCode
