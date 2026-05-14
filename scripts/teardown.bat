@echo off
REM Teardown: Stop and clean Docker stack (Windows)
REM =============================================

setlocal enabledelayedexpansion

echo.
echo =========================================
echo Mini-Medallion Infrastructure Teardown
echo =========================================
echo.

REM Get project directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

cd /d "%PROJECT_DIR%"

set /p confirm="Stop Docker stack and remove containers? (y/n) "
if /i not "%confirm%"=="y" (
    echo Aborted
    exit /b 0
)

echo.
echo Stopping containers...
docker-compose down
if errorlevel 1 (
    echo ERROR: docker-compose down failed
    exit /b 1
)

echo.
echo ^✓ Stack stopped and cleaned
echo.
echo To remove volumes ^(data^): docker-compose down -v
echo.
pause
