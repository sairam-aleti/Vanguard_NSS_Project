# ═══════════════════════════════════════════════════════════
#  Project Vanguard — One-Click Setup (Windows PowerShell)
# ═══════════════════════════════════════════════════════════
#  Run this script after cloning the repo:
#    .\setup.ps1
#
#  It will:
#   1. Create a Python virtual environment
#   2. Install all dependencies
#   3. Initialize the database with users & shipment data
#   4. Generate encryption keys and flag file
#   5. Reset the security log
# ═══════════════════════════════════════════════════════════

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  PROJECT VANGUARD — Automated Setup" -ForegroundColor White
Write-Host "  Secure Logistics & Supply Chain Defense" -ForegroundColor DarkGray
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check Python is installed
Write-Host "[1/4] Checking Python installation..." -ForegroundColor Yellow
try {
    $pyVersion = python --version 2>&1
    Write-Host "       Found: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "       ERROR: Python not found! Install Python 3.10+ from python.org" -ForegroundColor Red
    Write-Host "       Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "[2/4] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "       Virtual environment already exists. Reusing it." -ForegroundColor DarkGray
} else {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "       ERROR: Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "       Created: .\venv\" -ForegroundColor Green
}

# Activate venv and install dependencies
Write-Host "[3/4] Installing dependencies..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "       ERROR: Failed to install dependencies." -ForegroundColor Red
    exit 1
}
Write-Host "       Installed: flask, requests, cryptography" -ForegroundColor Green

# Initialize database
Write-Host "[4/4] Initializing database & encryption..." -ForegroundColor Yellow
python db_setup.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "       ERROR: Database setup failed." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  SETUP COMPLETE!" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  To run the project, execute:" -ForegroundColor White
Write-Host "    .\run.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Or manually (3 separate terminals):" -ForegroundColor DarkGray
Write-Host "    Terminal 1: .\venv\Scripts\Activate.ps1; python app.py" -ForegroundColor DarkGray
Write-Host "    Terminal 2: .\venv\Scripts\Activate.ps1; python internal_api.py" -ForegroundColor DarkGray
Write-Host "    Terminal 3: .\venv\Scripts\Activate.ps1; python siem_daemon.py" -ForegroundColor DarkGray
Write-Host ""
