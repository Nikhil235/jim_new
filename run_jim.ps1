Write-Host "=================================================="
Write-Host "  Starting Mini-Medallion Project"
Write-Host "=================================================="

# Start Backend API
Write-Host "[1/2] Starting Backend API..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", ".\.venv\Scripts\python.exe main.py --mode api"

# Wait a moment
Start-Sleep -Seconds 3

# Start Frontend Dashboard
Write-Host "[2/2] Starting Frontend Dashboard..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "cd dashboard && npm run dev"

Write-Host ""
Write-Host "Both services are starting up in new windows!"
Write-Host "- Backend API will be available at: http://localhost:8000"
Write-Host "- Frontend will be available at: http://localhost:5173"
Write-Host ""
Write-Host "To stop the project, simply close the two new command prompt windows."
