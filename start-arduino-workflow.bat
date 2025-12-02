@echo off
setlocal
set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%start-arduino-workflow.ps1

if not exist "%PS_SCRIPT%" (
    echo [arduino] Missing PowerShell script: %PS_SCRIPT%
    exit /b 1
)

pushd "%SCRIPT_DIR%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
set EXITCODE=%ERRORLEVEL%
popd
if %EXITCODE% EQU 0 (
    echo [arduino] Trigger sequence finished.
) else (
    echo [arduino] Trigger sequence failed with exit code %EXITCODE%.
)
exit /b %EXITCODE%
