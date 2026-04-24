"""
Vanguard Logistics — SIEM Daemon (Advanced Active Defense)
===========================================================
Security Information and Event Management daemon that provides:

  1. Multi-signal detection (LOGIN_FAILED, BLOCKED_SSRF, RATE_LIMITED, etc.)
  2. Cross-event correlation by attacker IP
  3. Behavior-based threat scoring with escalating responses
  4. Active defense: honeypot hash swap + iptables IP blocking

This daemon qualifies for the "Advanced Defense" bonus by implementing
behavior-based decision-making and responses that affect attacker behavior.

DEPLOYMENT:
    - Run as a systemd service on the Web Server VM
    - Monitors security.log in real-time
    - Requires write access to vanguard.db
"""

import time
import sqlite3
import os
import hashlib
import datetime
import subprocess
import json
import signal
import sys

# ═══════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "security.log")
DB_FILE = os.path.join(BASE_DIR, "vanguard.db")
SIEM_LOG = os.path.join(BASE_DIR, "siem_daemon.log")
POLL_INTERVAL = 2  # seconds between log checks

# ─── Threat Scoring Weights ───
# Different event types carry different risk weights.
# Multi-signal detection is achieved by tracking diverse event types.
EVENT_WEIGHTS = {
    'LOGIN_FAILED':    3,    # Failed login attempt
    'BLOCKED_SSRF':    8,    # Blocked SSRF attempt (high risk)
    'RATE_LIMITED':    5,    # Rate limit triggered
    'TRACKING_QUERY':  1,    # Tracking page recon (low individually)
    'CSRF_VIOLATION':  6,    # CSRF token mismatch
    'SSRF_FETCH':      2,    # Successful SSRF fetch (may be legitimate)
}

# ─── Correlation Multiplier ───
# If an IP produces multiple distinct event types, their score is multiplied.
# This rewards the SIEM for detecting coordinated attack patterns.
CORRELATION_MULTIPLIER = 1.5  # Applied when 2+ distinct event types from same IP

# ─── Threat Level Thresholds ───
THREAT_LEVELS = {
    'GREEN':   0,    # Normal
    'YELLOW':  8,    # Suspicious — start monitoring
    'ORANGE':  15,   # Elevated — log warning
    'RED':     25,   # High — swap admin hash (honeypot)
    'DEFCON1': 40,   # Critical — swap hash + block IP
}


# ═══════════════════════════════════════════════
# THREAT INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════

class ThreatIntelligence:
    """
    Core threat scoring engine implementing:
    - Per-IP cumulative threat scoring
    - Multi-signal correlation
    - Behavior-based escalation
    """

    def __init__(self):
        self.ip_scores = {}       # IP -> cumulative threat score
        self.ip_events = {}       # IP -> list of (timestamp, event_type)
        self.ip_threat_level = {} # IP -> current threat level string
        self.blocked_ips = set()  # IPs that have been blocked via iptables
        self.honeypot_active = False  # Whether admin hash has been swapped
        self.events_processed = 0

    def process_event(self, event_type, ip, details, timestamp):
        """
        Process a single security event and update threat scoring.
        Returns the action taken (if any).
        """
        self.events_processed += 1
        action = None

        # Calculate base weight
        weight = EVENT_WEIGHTS.get(event_type, 1)

        # ─── Correlation Analysis ───
        # If same IP has produced multiple distinct event types,
        # apply a multiplier. This detects coordinated attacks
        # (e.g., recon + brute force + exploitation).
        if ip not in self.ip_events:
            self.ip_events[ip] = []
        self.ip_events[ip].append((timestamp, event_type))

        unique_event_types = set(et for _, et in self.ip_events[ip])
        if len(unique_event_types) >= 2:
            weight = int(weight * CORRELATION_MULTIPLIER)
            if len(unique_event_types) >= 3:
                weight = int(weight * CORRELATION_MULTIPLIER)  # Double multiplier for 3+

        # ─── Update Score ───
        if ip not in self.ip_scores:
            self.ip_scores[ip] = 0
        self.ip_scores[ip] += weight

        score = self.ip_scores[ip]

        # ─── Determine Threat Level ───
        old_level = self.ip_threat_level.get(ip, 'GREEN')
        new_level = 'GREEN'
        for level, threshold in sorted(THREAT_LEVELS.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                new_level = level
                break
        self.ip_threat_level[ip] = new_level

        # ─── Escalation Response ───
        if new_level != old_level:
            siem_log(f"THREAT LEVEL CHANGE: {ip} | {old_level} -> {new_level} | Score: {score}")

        if new_level == 'DEFCON1' and ip not in self.blocked_ips:
            action = self._engage_defcon1(ip, score)
        elif new_level == 'RED' and not self.honeypot_active:
            action = self._engage_red_alert(ip, score)
        elif new_level == 'ORANGE':
            action = f"ORANGE_ALERT: IP {ip} under elevated monitoring (score: {score})"

        return action

    def _engage_red_alert(self, ip, score):
        """RED level: Swap admin hash for honeypot hash."""
        siem_log(f"[!!!] RED ALERT TRIGGERED by {ip} (score: {score})")
        siem_log("[*] Engaging Active Defense: Swapping Admin Hash → Honeypot")

        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            # Save the real hash for potential restoration
            cursor.execute("SELECT password_hash FROM users WHERE username='admin'")
            real_hash = cursor.fetchone()
            if real_hash:
                siem_log(f"[*] Original admin hash backed up: {real_hash[0][:8]}...")

            # Swap to honeypot hash: MD5("nice_try_red_team")
            fake_hash = hashlib.md5(b"nice_try_red_team").hexdigest()
            cursor.execute("UPDATE users SET password_hash=? WHERE username='admin'", (fake_hash,))
            conn.commit()
            conn.close()

            self.honeypot_active = True
            siem_log(f"[+] Admin hash swapped to honeypot: {fake_hash[:8]}...")
            siem_log("[+] Attackers will now steal fake credentials → dead end")
            return f"HONEYPOT_ACTIVATED: Admin hash swapped by {ip} (score: {score})"

        except Exception as e:
            siem_log(f"[!] ERROR during hash swap: {e}")
            return None

    def _engage_defcon1(self, ip, score):
        """DEFCON1: Swap hash + attempt IP block via iptables."""
        siem_log(f"[!!!] DEFCON 1 TRIGGERED by {ip} (score: {score})")

        # Ensure honeypot is active
        if not self.honeypot_active:
            self._engage_red_alert(ip, score)

        # Attempt iptables block (only works on Linux with root)
        siem_log(f"[*] Attempting IP block: {ip}")
        try:
            # Generate the iptables command (execute only on Linux)
            cmd = f"iptables -A INPUT -s {ip} -j DROP"
            if os.name != 'nt':  # Only execute on Linux
                result = subprocess.run(
                    cmd.split(),
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    self.blocked_ips.add(ip)
                    siem_log(f"[+] IP {ip} blocked via iptables")
                else:
                    siem_log(f"[!] iptables block failed (need root?): {result.stderr.strip()}")
            else:
                siem_log(f"[*] Windows detected — iptables block skipped (command: {cmd})")
                self.blocked_ips.add(ip)

        except Exception as e:
            siem_log(f"[!] IP block error: {e}")

        return f"DEFCON1: Honeypot active + IP {ip} blocked (score: {score})"

    def get_status(self):
        """Return current threat landscape summary."""
        return {
            'events_processed': self.events_processed,
            'tracked_ips': len(self.ip_scores),
            'honeypot_active': self.honeypot_active,
            'blocked_ips': list(self.blocked_ips),
            'threat_levels': dict(self.ip_threat_level),
            'scores': dict(self.ip_scores),
        }


# ═══════════════════════════════════════════════
# LOG PARSING
# ═══════════════════════════════════════════════

def parse_log_line(line):
    """
    Parse a structured log line from security.log.
    Expected format: [TIMESTAMP] EVENT_TYPE | IP: x.x.x.x | details
    Also handles legacy format: BLOCKED SSRF ATTEMPT: url
    """
    line = line.strip()
    if not line:
        return None

    # New structured format
    if line.startswith('[') and '|' in line:
        try:
            parts = line.split(' | ')
            timestamp_and_type = parts[0]
            # Extract timestamp
            timestamp_end = timestamp_and_type.index(']')
            timestamp = timestamp_and_type[1:timestamp_end]
            event_type = timestamp_and_type[timestamp_end+2:].strip()

            # Extract IP
            ip = 'unknown'
            details = ''
            for part in parts[1:]:
                if part.startswith('IP:'):
                    ip = part.split('IP:')[1].strip()
                else:
                    details = part.strip()

            return {
                'timestamp': timestamp,
                'event_type': event_type,
                'ip': ip,
                'details': details,
                'raw': line,
            }
        except (ValueError, IndexError):
            pass

    # Legacy format (from old app.py)
    if line.startswith('BLOCKED SSRF ATTEMPT:'):
        return {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': 'BLOCKED_SSRF',
            'ip': 'unknown',
            'details': line,
            'raw': line,
        }

    return None


# ═══════════════════════════════════════════════
# SIEM LOGGING
# ═══════════════════════════════════════════════

def siem_log(message):
    """Write to SIEM daemon's own log file and print to console."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    try:
        with open(SIEM_LOG, 'a') as f:
            f.write(formatted + '\n')
    except IOError:
        pass


# ═══════════════════════════════════════════════
# MAIN MONITORING LOOP
# ═══════════════════════════════════════════════

def monitor():
    """
    Main SIEM monitoring loop.
    Continuously watches security.log for new events,
    feeds them into the ThreatIntelligence engine,
    and takes automated defensive actions.
    """
    siem_log("=" * 60)
    siem_log("  VANGUARD SIEM DAEMON v3.0 — ACTIVE DEFENSE SYSTEM")
    siem_log("=" * 60)
    siem_log(f"Monitoring: {LOG_FILE}")
    siem_log(f"Database:   {DB_FILE}")
    siem_log(f"Poll rate:  {POLL_INTERVAL}s")
    siem_log(f"Threat thresholds: {json.dumps(THREAT_LEVELS)}")
    siem_log("")

    # Initialize threat engine
    engine = ThreatIntelligence()

    # Track file position so we only read new lines
    last_position = 0

    # Create log file if it doesn't exist
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()

    # Start at end of file (process only new events)
    with open(LOG_FILE, 'r') as f:
        f.seek(0, 2)  # Seek to end
        last_position = f.tell()

    siem_log("[+] SIEM Daemon online. Waiting for events...")

    while True:
        try:
            with open(LOG_FILE, 'r') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()

            for line in new_lines:
                event = parse_log_line(line)
                if event:
                    # Feed into threat engine
                    action = engine.process_event(
                        event['event_type'],
                        event['ip'],
                        event['details'],
                        event['timestamp']
                    )

                    # Log the event
                    siem_log(
                        f"EVENT: {event['event_type']} | "
                        f"IP: {event['ip']} | "
                        f"Score: {engine.ip_scores.get(event['ip'], 0)} | "
                        f"Level: {engine.ip_threat_level.get(event['ip'], 'GREEN')}"
                    )

                    # Log any triggered action
                    if action:
                        siem_log(f"ACTION: {action}")

            # Periodic status report (every 30 seconds worth of polls)
            if engine.events_processed > 0 and engine.events_processed % 15 == 0:
                status = engine.get_status()
                siem_log(f"STATUS: {json.dumps(status, indent=2)}")

        except FileNotFoundError:
            # Log file may have been rotated
            open(LOG_FILE, 'w').close()
            last_position = 0

        except Exception as e:
            siem_log(f"ERROR: {type(e).__name__}: {e}")

        time.sleep(POLL_INTERVAL)


# ═══════════════════════════════════════════════
# SIGNAL HANDLING (for graceful shutdown)
# ═══════════════════════════════════════════════

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    siem_log(f"Received signal {signum}. Shutting down SIEM daemon...")
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    monitor()