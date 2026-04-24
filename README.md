# 🛡️ Project Vanguard — Secure Logistics & Supply Chain Defense

> A high-fidelity 3-tier enterprise network emulation with intentional SSRF vulnerability, 
> active SIEM defense, and military-grade network segmentation.

---

## ⚡ Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- pip (comes with Python)

### 1. Clone & Setup Virtual Environment

```bash
# Clone the repository
git clone <repo-url>
cd Vanguard_Project

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (CMD):
.\venv\Scripts\activate.bat

# Linux/Mac:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database

```bash
python db_setup.py
```

This creates:
- `vanguard.db` — SQLite database with users & shipments
- `vault.key` — AES encryption key
- `manifest.enc` — Encrypted CTF flag

### 4. Run the Application

**Terminal 1 — Web Application (Port 80):**
```bash
# Note: Port 80 may require admin/sudo privileges
# Use port 8080 for local dev if needed
python app.py
```

**Terminal 2 — Internal API (Port 5000):**
```bash
python internal_api.py
```

**Terminal 3 — SIEM Daemon:**
```bash
python siem_daemon.py
```

### 5. Access the Application

| Page | URL |
|------|-----|
| Home (Corporate Site) | http://localhost/ |
| About | http://localhost/about |
| Tracking | http://localhost/tracking |
| Contact | http://localhost/contact |
| **Staff Portal (Hidden)** | http://localhost/staff_portal |
| Internal API | http://localhost:5000/ |

---

## 🔑 CTF Credentials

| User | Password | MD5 Hash | Role |
|------|----------|----------|------|
| employee1 | `operator` | `1a7ed... ` | logistics |
| admin | `admin_core_77` | `8f14e...` | administrator |

---

## 🎯 Attack Path (Red Team)

1. **Reconnaissance** → Find `/staff_portal` via `robots.txt` or directory brute-force
2. **Credential Cracking** → Crack `employee1` password (`operator`) from leaked/guessed MD5
3. **Login** → Authenticate at `/staff_portal` with `employee1:operator`
4. **SSRF Discovery** → Find the "Customs API Fetcher" in the dashboard
5. **SSRF Bypass** → Use decimal IP `http://2130706433:5000/api/admin_keys` to bypass the filter
6. **Admin Hash** → Extract admin MD5 hash from the API response
7. **Hash Cracking** → Crack `admin_core_77` from the MD5 hash
8. **Flag** → Decrypt `manifest.enc` using `vault.key` → `flag{admin_credentials.txt}`

---

## 🛡️ Blue Team Defense (SIEM)

The SIEM daemon (`siem_daemon.py`) provides:

- **Multi-signal detection**: Tracks LOGIN_FAILED, BLOCKED_SSRF, RATE_LIMITED, etc.
- **Cross-event correlation**: Scores IPs higher when they generate multiple event types
- **Behavior-based response**: Escalating threat levels (GREEN → YELLOW → ORANGE → RED → DEFCON1)
- **Active defense at RED level**: Swaps admin hash for honeypot hash (`nice_try_red_team`)
- **IP blocking at DEFCON1**: Generates iptables commands to block attacker IPs

---

## 📁 Project Structure

```
Vanguard_Project/
├── app.py                      # Main Flask web application
├── internal_api.py             # Internal API server (Port 5000)
├── db_setup.py                 # Database & encryption setup
├── siem_daemon.py              # SIEM active defense daemon
├── decrypt_flag.py             # Flag decryption utility
├── requirements.txt            # Python dependencies
├── robots.txt                  # SSH port hint for recon
├── vanguard.db                 # SQLite database (generated)
├── vault.key                   # AES key (generated)
├── manifest.enc                # Encrypted flag (generated)
├── security.log                # Security event log
├── templates/
│   ├── base.html               # Master layout
│   ├── index.html              # Corporate landing page
│   ├── about.html              # Company info
│   ├── tracking.html           # Shipment tracking (bait)
│   ├── contact.html            # Contact page
│   ├── portal.html             # Hidden staff login
│   └── dashboard.html          # Staff dashboard + SSRF tool
├── static/
│   ├── css/style.css           # Custom styles & animations
│   ├── js/shield.js            # Anti-inspect protection
│   └── img/hero-port.png       # Hero background image
├── config/
│   ├── vanguard-web.service    # Systemd unit (web app)
│   ├── vanguard-api.service    # Systemd unit (internal API)
│   ├── vanguard-siem.service   # Systemd unit (SIEM)
│   ├── iptables-rules.sh       # Firewall hardening
│   ├── sshd_config             # SSH hardening
│   └── vsftpd.conf             # FTP chroot config
├── scripts/
│   └── health_check.sh         # Service health monitor
└── docs/
    └── DEPLOYMENT.md           # Full VirtualBox setup guide
```

---

## 📋 For VM Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the complete guide covering:
- VirtualBox VM creation & network configuration
- pfSense dual-firewall setup
- Ubuntu Server deployment
- Systemd service installation
- iptables, SSH, and vsftpd hardening
