@echo off
echo ==================================================
echo   Starting Mini-Medallion Project
echo ==================================================

:: Run the Data Ingestion & Feature Engineering Pipeline
echo [1/3] Running Data Ingestion & Feature Pipeline...
.\.venv\Scripts\python.exe scripts/run_pipeline.py --mode full
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Pipeline completed with warnings or non-zero status. Starting servers...
    echo.
)

:: Start the Python backend API
echo [2/3] Starting Backend API...
start "Mini-Medallion Backend" cmd /k ".\.venv\Scripts\python.exe main.py --mode api"

:: Wait a few seconds for the backend to start up
timeout /t 3 /nobreak >nul

:: Start the React frontend
echo [3/3] Starting Frontend Dashboard...
start "Mini-Medallion Frontend" cmd /k "cd dashboard && npm run dev"

echo.
echo Both services are starting up in new windows!
echo - Backend API will be available at: http://localhost:8000
echo - Frontend will be available at: http://localhost:5173
echo.
echo To stop the project, simply close the two new command prompt windows.
pause
