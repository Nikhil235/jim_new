@echo off
echo ==================================================
echo   Starting Mini-Medallion Project
echo ==================================================

:: Start the Python backend API
echo [1/2] Starting Backend API...
start "Mini-Medallion Backend" cmd /k ".\.venv\Scripts\python.exe main.py --mode api"

:: Wait a few seconds for the backend to start up
timeout /t 3 /nobreak >nul

:: Start the React frontend
echo [2/2] Starting Frontend Dashboard...
start "Mini-Medallion Frontend" cmd /k "cd dashboard && npm run dev"

echo.
echo Both services are starting up in new windows!
echo - Backend API will be available at: http://localhost:8000
echo - Frontend will be available at: http://localhost:5173
echo.
echo To stop the project, simply close the two new command prompt windows.
pause
