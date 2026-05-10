@echo off
REM ============================================================================
REM AI-cademics - One-click Windows starter
REM 
REM Just double-click this file to start the backend.
REM 
REM Generated with Claude AI assistance.
REM ============================================================================

title AI-cademics Backend

echo.
echo ============================================================
echo        AI-CADEMICS - Backend Starter (Windows)
echo ============================================================
echo.

REM Move to script directory
cd /d "%~dp0"

REM Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Install from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Run launcher
python launcher.py %*

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo [ERROR] Launcher exited with errors
    pause
)
