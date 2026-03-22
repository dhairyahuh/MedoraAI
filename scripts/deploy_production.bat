@echo off
REM Production Deployment Script for Windows
REM Secure Federated Medical Imaging System

echo ========================================
echo Production Deployment
echo Secure Federated Medical Imaging System
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.8+ first.
    pause
    exit /b 1
)

REM Check Redis
echo Checking Redis...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo WARNING: Redis not running. Start Redis for rate limiting.
    echo.
    echo Install Redis:
    echo 1. Download: https://github.com/tporadowski/redis/releases
    echo 2. Extract and run redis-server.exe
    echo.
    set /p continue="Continue without Redis? (y/n): "
    if /i not "%continue%"=="y" exit /b 1
)

REM Create directories
echo Creating directories...
if not exist logs mkdir logs
if not exist logs\audit mkdir logs\audit
if not exist certs mkdir certs
if not exist models\weights mkdir models\weights

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Install security dependencies
echo Installing security dependencies...
pip install -r requirements_security.txt
if errorlevel 1 (
    echo WARNING: Some security dependencies failed
)

REM Check environment file
if not exist .env.production (
    echo.
    echo WARNING: .env.production not found
    echo Copying example file...
    copy .env.production.example .env.production
    echo.
    echo IMPORTANT: Edit .env.production and set:
    echo   - JWT_SECRET_KEY (256-bit random string)
    echo   - DATABASE_URL (PostgreSQL connection)
    echo   - REDIS_PASSWORD (if Redis has auth)
    echo.
    pause
)

REM Generate TLS certificates if missing
if not exist certs\server.crt (
    echo.
    echo Generating self-signed TLS certificates...
    python -c "from security.tls_config import ensure_certificates_exist; ensure_certificates_exist()"
    echo Certificates generated in certs/ directory
)

REM Run health check
echo.
echo Running pre-deployment health check...
python health_check.py
if errorlevel 1 (
    echo.
    echo WARNING: Health check failed. Review errors above.
    set /p continue="Continue anyway? (y/n): "
    if /i not "%continue%"=="y" exit /b 1
)

REM Start server
echo.
echo ========================================
echo Starting Production Server
echo ========================================
echo.
echo Server will start on https://localhost:8443
echo Press Ctrl+C to stop
echo.

python run_production.py

pause
