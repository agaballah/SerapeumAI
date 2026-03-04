@echo off
:: This is the entry point for the automated setup.
:: It bypasses the PowerShell execution policy which is why Setup.ps1 was failing.

title SerapeumAI System Setup
color 0B

echo =======================================================
echo          SerapeumAI - Starting System Setup
echo =======================================================
echo.
echo Launching automated installer...
echo.

:: Run the PowerShell script with Bypass policy to avoid security errors
powershell -ExecutionPolicy Bypass -File "%~dp0Setup.ps1"

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERROR] Setup script failed. 
    echo Please make sure you are running this from a local drive (not a network drive).
    echo.
)

pause
