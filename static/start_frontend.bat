@echo off
REM Quick Start Script for Medical AI Platform Frontend

echo ========================================
echo Medical AI Platform - Frontend Demo
echo Johns Hopkins Medicine
echo ========================================
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "..\..\.venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

echo [1/3] Checking dependencies...
..\..\.venv\Scripts\python.exe -c "import fastapi" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    ..\..\.venv\Scripts\pip.exe install -q fastapi uvicorn python-multipart pillow
)

echo [2/3] Starting server...
echo.
echo Frontend will be available at:
echo   http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start server
..\..\.venv\Scripts\python.exe ..\..\medical-inference-server\main.py

pause
