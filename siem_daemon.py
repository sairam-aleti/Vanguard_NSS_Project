import time
import sqlite3
import os
import hashlib

LOG_FILE = "security.log"
THRESHOLD = 3

def lockdown_database():
    print("\n[!!!] DEFCON 1 TRIGGERED: INTRUSION DETECTED [!!!]")
    print("[*] Engaging Active Defense: Swapping Admin Credentials with Honeypot Hash...")
    
    conn = sqlite3.connect('vanguard.db')
    cursor = conn.cursor()
    
    # Generate a fake hash (cracking this reveals "nice_try_red_team" instead of the password)
    fake_hash = hashlib.md5(b"nice_try_red_team").hexdigest()
    
    cursor.execute("UPDATE users SET password_hash=? WHERE username='admin'", (fake_hash,))
    conn.commit()
    conn.close()
    
    print("[+] Lockdown Complete. Attackers will now steal fake credentials.")
    print("[*] (In production, this also triggers a 15-minute iptables IP ban).")

def monitor_logs():
    print("[*] Vanguard SIEM Daemon Initialized.")
    print(f"[*] Monitoring {LOG_FILE} for aggressive scanning...")
    
    # Create the log file if it doesn't exist yet
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()

    while True:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            
        # If we see 3 or more alerts, trigger the defense!
        if len(lines) >= THRESHOLD:
            lockdown_database()
            # Clear the log so it doesn't trigger infinitely
            open(LOG_FILE, 'w').close()
            break # Stop the daemon for demo purposes
            
        time.sleep(2) # Check every 2 seconds

if __name__ == '__main__':
    monitor_logs()