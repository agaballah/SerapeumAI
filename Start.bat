@echo off
title SerapeumAI
color 0B

echo =======================================================
echo                 Starting SerapeumAI
echo =======================================================
echo.
echo Starting the AI Engine in the background...

:: The python app handles everything (DB, UI, LM Studio autostart)
python run.py

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo [ERROR] SerapeumAI closed unexpectedly.
    echo Please make sure you ran Install.bat first.
    echo.
    pause
)
