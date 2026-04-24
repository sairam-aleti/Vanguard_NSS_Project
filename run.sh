#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Project Vanguard — Run All Services (Linux/Mac)
# ═══════════════════════════════════════════════════════════
#  Starts all 3 services in background
#  Usage: ./run.sh
#  Stop:  ./run.sh stop
# ═══════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ "$1" == "stop" ]; then
    echo "[*] Stopping all Vanguard services..."
    pkill -f "python.*app.py" 2>/dev/null && echo "    Stopped: Web App" || echo "    Web App not running"
    pkill -f "python.*internal_api.py" 2>/dev/null && echo "    Stopped: Internal API" || echo "    Internal API not running"
    pkill -f "python.*siem_daemon.py" 2>/dev/null && echo "    Stopped: SIEM Daemon" || echo "    SIEM Daemon not running"
    exit 0
fi

# Check setup
if [ ! -d "venv" ]; then
    echo "ERROR: Run setup first: ./setup.sh"
    exit 1
fi

source venv/bin/activate

echo ""
echo "═══════════════════════════════════════════════════"
echo "  PROJECT VANGUARD — Starting All Services"
echo "═══════════════════════════════════════════════════"
echo ""

# Start Internal API
echo "  [1/3] Starting Internal API (Port 5000)..."
nohup python internal_api.py > /dev/null 2>&1 &
echo "         PID: $!"

sleep 1

# Start SIEM Daemon
echo "  [2/3] Starting SIEM Daemon..."
nohup python siem_daemon.py > /dev/null 2>&1 &
echo "         PID: $!"

sleep 1

# Start Web App (may need sudo for port 80)
echo "  [3/3] Starting Web Application (Port 80)..."
if [ "$EUID" -eq 0 ]; then
    nohup python app.py > /dev/null 2>&1 &
else
    echo "         NOTE: Port 80 requires root. Using sudo..."
    sudo nohup venv/bin/python app.py > /dev/null 2>&1 &
fi
echo "         PID: $!"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ALL SERVICES RUNNING"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Home:          http://localhost"
echo "  Staff Portal:  http://localhost/staff_portal"
echo "  Internal API:  http://localhost:5000"
echo ""
echo "  Stop all: ./run.sh stop"
echo ""
