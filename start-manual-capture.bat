@echo off
setlocal
set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%start-manual-capture.ps1

if not exist "%PS_SCRIPT%" (
    echo [manual-capture] start-manual-capture.ps1 is missing next to this file.
    pause
    exit /b 1
)

pushd "%SCRIPT_DIR%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
set EXITCODE=%ERRORLEVEL%
popd
echo [manual-capture] Script finished with exit code %EXITCODE%.
pause
exit /b %EXITCODE%
