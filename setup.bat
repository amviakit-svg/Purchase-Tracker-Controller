@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  Purchase Tracker Controller - First-time Setup
:: ============================================================
::  Creates a Python virtual environment and installs the
::  dependencies required to run the server.
::
::  Usage:  double-click this file, or run from cmd:
::          setup.bat
:: ============================================================

cd /d "%~dp0"

echo ============================================================
echo  Purchase Tracker Controller - First-time Setup
echo ============================================================
echo.

:: ---- CHECK PYTHON ----
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not on PATH.
    echo Download Python 3.10+ from https://www.python.org/downloads/
    echo During install, make sure to tick "Add Python to PATH".
    pause
    exit /b 1
)

python --version
echo.

:: ---- CREATE VENV ----
if exist venv (
    echo [OK] Virtual environment already exists at .\venv
) else (
    echo [1/2] Creating virtual environment in .\venv ...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

:: ---- INSTALL DEPENDENCIES ----
echo.
echo [2/2] Installing dependencies from backend\requirements.txt ...
echo        (first run can take a minute or two)
echo.
venv\Scripts\python.exe -m pip install --upgrade pip >nul
venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete!
echo ============================================================
echo.
echo  Next step:  double-click  start_server.bat
echo  Then open:  http://localhost:5000
echo.
echo  To run silently in the background, use  start_background.vbs
echo  To install as a Windows service, use   install_service.bat
echo.
pause
endlocal