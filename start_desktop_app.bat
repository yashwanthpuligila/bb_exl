@echo off
title Sri Laxmi Gayatri Traders - Invoice ERP
setlocal enabledelayedexpansion

:: 1. Always anchor working directory to this script's directory
cd /d "%~dp0"

:: 2. Find Python executable (check venvs first, then system PATH)
set "PYTHON_BIN="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_BIN=%~dp0.venv\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_BIN=%~dp0venv\Scripts\python.exe"
) else (
    where python.exe >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=*" %%i in ('where python.exe') do (
            if not defined PYTHON_BIN set "PYTHON_BIN=%%i"
        )
    ) else (
        where py.exe >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_BIN=py.exe"
        )
    )
)

:: 3. Verify Python was found
if not defined PYTHON_BIN (
    echo.
    echo ================================================================
    echo  ERROR: Python was not found on your system.
    echo ================================================================
    echo  Please install Python 3.10+ from https://www.python.org/
    echo  and make sure to check "Add Python to PATH" during installation.
    echo ================================================================
    echo.
    pause
    exit /b 1
)

:: 4. Ensure desktop SQLite engine environment
set "DATABASE_ENGINE=sqlite"
set "DESKTOP_MODE=1"
set "DATABASE_URL="
set "POSTGRES_URL="
set "POSTGRESQL_URL="

:: 5. Launch the Desktop Application
echo Starting Sri Laxmi Gayatri Traders - Invoice ERP...
"%PYTHON_BIN%" desktop_app.py
set "EXIT_CODE=%errorlevel%"

if %EXIT_CODE% neq 0 (
    echo.
    echo ================================================================
    echo  The application exited with error code: %EXIT_CODE%
    echo  Check "desktop_app.log" for additional details.
    echo ================================================================
    echo.
    pause
)

exit /b %EXIT_CODE%
