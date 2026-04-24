# Project Vanguard — Manual Setup & Run Guide

## Prerequisites
- Python 3.10+ installed (with "Add to PATH" checked)
- Git installed

---

## First Time Setup (run once)

1. Open a terminal in the project folder

2. Create virtual environment:
   .\venv\Scripts\Activate.ps1
   (if that fails try: python -m venv venv first)

3. Install packages:
   pip install flask requests cryptography

4. Initialize database:
   python db_setup.py

---

## Running the Project (3 terminals needed)

TERMINAL 1 — Web App:
   .\venv\Scripts\Activate.ps1
   python app.py

TERMINAL 2 — Internal API:
   .\venv\Scripts\Activate.ps1
   python internal_api.py

TERMINAL 3 — SIEM Daemon:
   .\venv\Scripts\Activate.ps1
   python siem_daemon.py

---

## URLs

Home Page:         http://localhost
About:             http://localhost/about
Tracking:          http://localhost/tracking
Contact:           http://localhost/contact
Robots.txt:        http://localhost/robots.txt
Backup Configs:    http://localhost/backup_configs/
Staff Portal:      http://localhost/staff_portal
Internal API:      http://localhost:5000

---

## Test Credentials

employee1 / operator        (found via leaked backup config)
admin / admin_core_77       (found via SSRF + MD5 cracking)

---

## SSRF Test (after logging in as employee1)

In the dashboard "Customs API Fetcher", enter:
   http://2130706433:5000/api/admin_keys

This is 127.0.0.1 in decimal format, which bypasses the IP filter.
On the VM deployment, use 167772175 instead (which is 10.0.0.15 in decimal).

---

## After git pull

Stop all 3 terminals (Ctrl+C), then start them again.

---

## To stop

Press Ctrl+C in each terminal window.
