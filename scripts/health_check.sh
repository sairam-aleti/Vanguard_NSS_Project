#!/bin/bash
# ═══════════════════════════════════════════════════════
# Vanguard Logistics — Service Health Check
# ═══════════════════════════════════════════════════════
# Monitors critical services and alerts if any are down.
# Add to crontab: */2 * * * * /opt/vanguard/scripts/health_check.sh
# ═══════════════════════════════════════════════════════

LOG_FILE="/opt/vanguard/health_check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

check_port() {
    local port=$1
    local name=$2
    if ss -tlnp | grep -q ":${port} "; then
        echo "[$TIMESTAMP] [OK] $name is running on port $port" >> "$LOG_FILE"
        return 0
    else
        echo "[$TIMESTAMP] [CRITICAL] $name is DOWN on port $port!" >> "$LOG_FILE"
        return 1
    fi
}

echo "[$TIMESTAMP] === Health Check Starting ===" >> "$LOG_FILE"

# Check web server (port 80)
if ! check_port 80 "Web Server (app.py)"; then
    echo "[$TIMESTAMP] [ACTION] Attempting to restart vanguard-web..." >> "$LOG_FILE"
    systemctl restart vanguard-web 2>/dev/null
fi

# Check internal API (port 5000) — only on DB server
if ss -tlnp | grep -q ":5000 " 2>/dev/null; then
    echo "[$TIMESTAMP] [OK] Internal API is running on port 5000" >> "$LOG_FILE"
elif [ -f /opt/vanguard/internal_api.py ]; then
    if ! check_port 5000 "Internal API (internal_api.py)"; then
        echo "[$TIMESTAMP] [ACTION] Attempting to restart vanguard-api..." >> "$LOG_FILE"
        systemctl restart vanguard-api 2>/dev/null
    fi
fi

# Check SIEM daemon
if pgrep -f "siem_daemon.py" >/dev/null 2>&1; then
    echo "[$TIMESTAMP] [OK] SIEM Daemon is running" >> "$LOG_FILE"
else
    echo "[$TIMESTAMP] [CRITICAL] SIEM Daemon is DOWN!" >> "$LOG_FILE"
    echo "[$TIMESTAMP] [ACTION] Attempting to restart vanguard-siem..." >> "$LOG_FILE"
    systemctl restart vanguard-siem 2>/dev/null
fi

# Check disk space (alert if < 10%)
DISK_USE=$(df /opt/vanguard --output=pcent | tail -1 | tr -d ' %')
if [ "$DISK_USE" -gt 90 ]; then
    echo "[$TIMESTAMP] [WARNING] Disk usage at ${DISK_USE}%! Consider log rotation." >> "$LOG_FILE"
fi

echo "[$TIMESTAMP] === Health Check Complete ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
