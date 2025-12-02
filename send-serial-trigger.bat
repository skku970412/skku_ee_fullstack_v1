@echo off
setlocal
set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%send-serial-trigger.ps1

if not exist "%PS_SCRIPT%" (
    echo [serial-trigger] PowerShell script not found: %PS_SCRIPT%
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*
set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% EQU 0 (
    echo [serial-trigger] Completed successfully.
) else (
    echo [serial-trigger] Failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
