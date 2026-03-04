@echo off
title SerapeumAI Installer
color 0A

echo =======================================================
echo          SerapeumAI - One-Click Installer
echo =======================================================
echo.

:: 1. Check Python
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.11 from python.org
    echo IMPORTANT: Remember to check the "Add Python to PATH" box during installation!
    echo.
    pause
    exit /b
)

:: 2. Install pip requirements
echo.
echo [2/3] Installing Required Python Packages...
echo This might take a few minutes. Please wait...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERROR] Failed to install Python dependencies. Please check your internet connection.
    echo.
    pause
    exit /b
)

:: 3. Check for npm to install lms
echo.
echo [3/3] Checking AI Server dependencies...
call npm --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Node.js found. Installing LM Studio CLI in the background...
    call npm install -g @lmstudio/lms >nul 2>&1
) else (
    color 0E
    echo [WARNING] Node.js (npm) was not found. 
    echo SerapeumAI will attempt to install LM Studio automatically on first launch,
    echo but if it fails, please install Node.js from https://nodejs.org/
    color 0A
)

echo.
echo =======================================================
echo                 INSTALLATION COMPLETE!
echo =======================================================
echo.
echo You can now double-click "Start.bat" to launch SerapeumAI.
echo.
pause
