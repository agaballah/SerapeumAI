@echo off
setlocal EnableDelayedExpansion

title SerapeumAI Nara Developer

echo ============================================================
echo  SerapeumAI Nara Developer Session Boot
echo ============================================================

cd /d D:\SerapeumAI

REM ── 1. Verify required brain files exist ─────────────────────
for %%F in (
    ".ai_developer_control\SerapeumAI_AI_Developer_Contract.md"
    ".ai_developer_control\CURRENT_TASK.md"
    ".ai_developer_control\PROJECT_STATE.md"
    ".ai_developer_control\DEVELOPMENT_LOG.md"
    ".ai_developer_control\CONTRACT_CORE_HASH.txt"
    ".ai_developer_control\DEVELOPER_RUNTIME_CONFIG.md"
    ".ai_developer_control\MANAGER_OPERATING_RULES.md"
    "DeveloperTools\DeveloperStartupPrompt.txt"
    "DeveloperTools\.env"
) do (
    if not exist %%F (
        echo.
        echo ERROR: Missing required file: %%F
        echo        The system cannot start without all brain files.
        pause
        exit /b 1
    )
)

REM ── 2. Read model from DEVELOPER_RUNTIME_CONFIG.md ───────────
set AIDER_MODEL=openai/mistral-large
for /f "tokens=2 delims=: " %%M in ('findstr /C:"model:" ".ai_developer_control\DEVELOPER_RUNTIME_CONFIG.md"') do (
    set AIDER_MODEL=openai/%%M
)
echo Model: %AIDER_MODEL%

REM ── 3. Check CURRENT_TASK.md has STATUS: APPROVED ────────────
findstr /C:"STATUS: APPROVED" ".ai_developer_control\CURRENT_TASK.md" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: CURRENT_TASK.md does not have STATUS: APPROVED
    echo        The Manager must write and approve a task before launching a session.
    echo        Edit .ai_developer_control\CURRENT_TASK.md and set STATUS: APPROVED.
    pause
    exit /b 1
)
echo Task gate: APPROVED

REM ── 4. Verify immutable constitution hash ────────────────────
powershell -NoProfile -ExecutionPolicy Bypass -File "DeveloperTools\VerifyHash.ps1"

if errorlevel 1 (
    echo.
    echo CRITICAL: Contract core constitution hash mismatch.
    echo           The immutable section has been modified. Aborting.
    echo           Restore SerapeumAI_AI_Developer_Contract.md Section I or regenerate hash with Owner approval.
    pause
    exit /b 1
)
echo Constitution: VERIFIED

REM ── 5. Create session directories ────────────────────────────
if not exist ".ai_developer_control\session_logs" mkdir ".ai_developer_control\session_logs"

REM ── 6. Generate session ID ───────────────────────────────────
set SESSION=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set SESSION=%SESSION: =0%

REM ── 7. Capture pre-session git state ─────────────────────────
git branch --show-current > ".ai_developer_control\session_logs\%SESSION%_branch.txt" 2>&1
git status --short        > ".ai_developer_control\session_logs\%SESSION%_status.txt" 2>&1

REM ── 8. Generate MANAGER_BOOTSTRAP.md ─────────────────────────
powershell -NoProfile -ExecutionPolicy Bypass -File "DeveloperTools\GenerateBootstrap.ps1"

echo Bootstrap: GENERATED

REM ── 9. Save session PID placeholder (written after Aider starts) ──
echo STARTING > ".ai_developer_control\session_logs\session.pid"

echo.
echo Session ID : %SESSION%
echo Branch     :
type ".ai_developer_control\session_logs\%SESSION%_branch.txt"
echo.
echo ============================================================
echo  All gates passed. Launching Nara + Aider...
echo ============================================================
echo.

REM ── 10. Launch Aider ─────────────────────────────────────────
aider --model %AIDER_MODEL% ^
      --env-file DeveloperTools\.env ^
      --read DeveloperTools\DeveloperStartupPrompt.txt ^
      --read .ai_developer_control\SerapeumAI_AI_Developer_Contract.md ^
      --yes-always ^
      --no-show-model-warnings

REM ── 11. Clean up PID file on exit ────────────────────────────
if exist ".ai_developer_control\session_logs\session.pid" (
    del ".ai_developer_control\session_logs\session.pid"
)

echo.
echo ============================================================
echo  Aider session ended.
echo  Session logs: .ai_developer_control\session_logs\
echo  Run PostSessionAudit.ps1 to generate audit report.
echo ============================================================
echo.

pause