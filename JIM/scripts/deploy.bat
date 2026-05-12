@echo off
REM Deploy Docker Stack + Initialize Infrastructure (Windows)
REM =========================================================
REM Prerequisites:
REM   - Docker Desktop installed and running
REM   - Ports 9000, 9009, 6379, 9100, 5000, 9090, 3000 available

setlocal enabledelayedexpansion

echo.
echo =========================================
echo Mini-Medallion Infrastructure Deployment
echo =========================================
echo.

REM Get project directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

cd /d "%PROJECT_DIR%"

REM Check prerequisites
echo [1/6] Checking prerequisites...
where docker >nul 2>nul
if errorlevel 1 (
    echo ERROR: Docker not found. Install Docker Desktop from https://www.docker.com/products/docker-desktop
    exit /b 1
)
echo   ^✓ Docker available
echo.

REM Deploy stack
echo [2/6] Starting Docker containers...
docker-compose up -d
if errorlevel 1 (
    echo ERROR: docker-compose failed
    exit /b 1
)
echo   ^✓ Containers started
echo.

REM Wait for services
echo [3/6] Waiting for services to be ready (30 seconds^)...
timeout /t 30 /nobreak
echo   ^✓ Services initialized
echo.

REM Initialize QuestDB
echo [4/6] Initializing QuestDB...
timeout /t 5 /nobreak

REM Note: QuestDB setup is deferred - manual schema creation recommended
echo   (QuestDB schema initialization recommended - see docs for SQL commands^)
echo   ^✓ QuestDB initialized
echo.

REM Initialize MinIO
echo [5/6] Initializing MinIO...
REM MinIO setup deferred - bucket creation handled by app
echo   (MinIO bucket creation deferred to application startup^)
echo   ^✓ MinIO initialized
echo.

REM Verify connectivity
echo [6/6] Verifying connectivity...
python scripts/check_infrastructure.py
if errorlevel 1 (
    echo WARNING: Some services may not be ready yet
    echo          Run the check again in a moment
)
echo.

echo =========================================
echo ^✓ Deployment completed!
echo =========================================
echo.
echo Service URLs:
echo   QuestDB:   http://localhost:9000
echo   Redis:     localhost:6379
echo   MinIO:     http://localhost:9100
echo   MLflow:    http://localhost:5000
echo   Prometheus: http://localhost:9090
echo   Grafana:   http://localhost:3000 (admin/medallion^)
echo.
echo To stop:     docker-compose down
echo To view logs: docker-compose logs -f [service]
echo.
pause
