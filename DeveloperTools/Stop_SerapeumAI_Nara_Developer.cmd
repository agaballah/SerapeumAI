@echo off
setlocal

echo ============================================================
echo  SerapeumAI — Stop Nara Developer Session
echo ============================================================

cd /d D:\SerapeumAI

set PID_FILE=.ai_developer_control\session_logs\session.pid

if not exist "%PID_FILE%" (
    echo No active session.pid found.
    echo Either no session is running or it already exited cleanly.
    pause
    exit /b 0
)

set /p AIDER_PID=<"%PID_FILE%"

if "%AIDER_PID%"=="STARTING" (
    echo WARNING: Session is still starting. Wait for it to fully launch before stopping.
    pause
    exit /b 1
)

echo Stopping Aider session PID: %AIDER_PID%
taskkill /PID %AIDER_PID% /F >nul 2>&1

if errorlevel 1 (
    echo WARNING: Could not stop PID %AIDER_PID%. It may have already exited.
) else (
    echo Developer session stopped cleanly.
)

del "%PID_FILE%" >nul 2>&1

echo.
echo Run DeveloperTools\PostSessionAudit.ps1 to generate the session audit.
echo ============================================================

pause