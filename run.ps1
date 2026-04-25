# =========================================================
#  Project Vanguard - Run All Services (Windows PowerShell)
# =========================================================

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  PROJECT VANGUARD - Starting All Services" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "venv")) {
    Write-Host "  ERROR: Virtual environment not found!" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "vanguard.db")) {
    Write-Host "  ERROR: Database not found!" -ForegroundColor Red
    exit 1
}

$venvPython = ".\venv\Scripts\python.exe"

Write-Host "  [1/3] Starting Internal API (Port 5000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PWD'; & '$venvPython' internal_api.py" -WindowStyle Normal

Start-Sleep -Seconds 1

Write-Host "  [2/3] Starting SIEM Daemon..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PWD'; & '$venvPython' siem_daemon.py" -WindowStyle Normal

Start-Sleep -Seconds 1

Write-Host "  [3/3] Starting Web Application (Port 80)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PWD'; & '$venvPython' app.py" -WindowStyle Normal

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  ALL SERVICES STARTED!" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  Home Page:     http://localhost" -ForegroundColor Cyan
Write-Host "  Staff Portal:  http://localhost/staff_portal" -ForegroundColor DarkYellow
Write-Host "  Internal API:  http://localhost:5000" -ForegroundColor DarkYellow
Write-Host ""
Write-Host "  Login: employee1 / operator" -ForegroundColor DarkGray
Write-Host "  To stop: Close the 3 terminal windows that opened." -ForegroundColor DarkGray
Write-Host ""
