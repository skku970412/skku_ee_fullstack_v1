@echo off
setlocal
set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%run_test.ps1

if not exist "%PS_SCRIPT%" (
    echo [run_test] Missing PowerShell script: %PS_SCRIPT%
    exit /b 1
)

pushd "%SCRIPT_DIR%"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
set EXITCODE=%ERRORLEVEL%
popd
echo [run_test] Finished with exit code %EXITCODE%.
exit /b %EXITCODE%
