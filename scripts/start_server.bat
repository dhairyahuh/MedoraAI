@echo off
REM Production Startup Script for Medical Inference Server
REM Run this to start the server in production mode

echo.
echo ========================================
echo Medical Inference Server - Starting
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then install dependencies: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check Python and PyTorch
echo Checking dependencies...
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA Available:', torch.cuda.is_available())"
if errorlevel 1 (
    echo ERROR: PyTorch not installed correctly!
    pause
    exit /b 1
)

REM Check if .env exists
if not exist ".env" (
    echo WARNING: .env file not found, using defaults
    echo Consider copying .env.example to .env and customizing
    timeout /t 3
)

echo.
echo Starting server...
echo API: http://localhost:8000
echo Dashboard: http://localhost:8000/dashboard
echo Docs: http://localhost:8000/docs
echo Metrics: http://localhost:8000/metrics
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start server
python main.py

REM If we get here, server stopped
echo.
echo Server stopped.
pause
