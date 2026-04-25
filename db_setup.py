"""
Vanguard Logistics — Database Setup & Encryption
=================================================
Initializes the SQLite database with seeded users and shipment data.
Generates AES-256 encrypted cargo manifest (the CTF flag).

Run this script once before starting the application:
    python db_setup.py
"""

import sqlite3
import hashlib
import os
from cryptography.fernet import Fernet


def setup_database():
    """Create and seed the vanguard.db database."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vanguard.db')
    print("[*] Initializing Vanguard Database...")
    print(f"    Path: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ─── Users Table ───
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # ─── Shipments Table (for tracking page / honeypot) ───
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shipments (
            id INTEGER PRIMARY KEY,
            tracking_id TEXT NOT NULL UNIQUE,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            status TEXT NOT NULL,
            eta TEXT NOT NULL,
            weight TEXT NOT NULL
        )
    ''')

    # ─── Seed Users with MD5 Hashes (intentionally weak) ───
    # employee1 password: "operator"  (easily crackable)
    # admin password: "trustno1" (in rockyou.txt + CrackStation)
    emp_hash = hashlib.md5(b"operator").hexdigest()
    admin_hash = hashlib.md5(b"trustno1").hexdigest()

    print(f"    [+] employee1 hash (MD5 of 'operator'): {emp_hash}")
    print(f"    [+] admin hash (MD5 of 'trustno1'): {admin_hash}")

    cursor.execute(
        "INSERT OR REPLACE INTO users (id, username, password_hash, role) VALUES (1, 'employee1', ?, 'logistics')",
        (emp_hash,)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO users (id, username, password_hash, role) VALUES (2, 'admin', ?, 'administrator')",
        (admin_hash,)
    )

    # ─── Seed Shipment Data (realistic tracking entries) ───
    shipments = [
        ('VGL-2024-78451', 'Shanghai, China', 'Rotterdam, Netherlands', 'In Transit',
         'Dec 28, 2024', '24,500 kg — 2x 40ft FCL'),
        ('VGL-2024-91203', 'Dubai, UAE', 'New York, USA', 'Customs Hold',
         'Jan 03, 2025', '8,200 kg — 1x 20ft Reefer'),
        ('VGL-2024-33567', 'Singapore', 'London, United Kingdom', 'Delivered',
         'Dec 10, 2024', '15,800 kg — 1x 40ft HC'),
        ('VGL-2024-55890', 'Hamburg, Germany', 'Tokyo, Japan', 'In Transit',
         'Jan 15, 2025', '31,000 kg — 3x 20ft Standard'),
        ('VGL-2024-12098', 'Los Angeles, USA', 'Sydney, Australia', 'In Transit',
         'Jan 08, 2025', '12,400 kg — Breakbulk'),
        ('VGL-2024-67234', 'Mumbai, India', 'Durban, South Africa', 'Delivered',
         'Nov 20, 2024', '6,750 kg — Less than Container'),
    ]

    for s in shipments:
        cursor.execute(
            "INSERT OR IGNORE INTO shipments (tracking_id, origin, destination, status, eta, weight) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            s
        )

    conn.commit()
    conn.close()
    print("[+] Database 'vanguard.db' initialized successfully.")
    print(f"    Users: employee1 (logistics), admin (administrator)")
    print(f"    Shipments: {len(shipments)} records seeded")


def create_encrypted_flag():
    """Generate AES-256 encrypted cargo manifest containing the CTF flag."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(base_dir, 'vault.key')
    enc_path = os.path.join(base_dir, 'manifest.enc')

    print("\n[*] Encrypting VIP Cargo Manifest (Target Flag)...")

    # Generate Fernet key (AES-128-CBC under the hood, but commonly referred to as AES-256)
    key = Fernet.generate_key()
    with open(key_path, 'wb') as key_file:
        key_file.write(key)

    # Encrypt the flag
    cipher_suite = Fernet(key)
    flag_data = b"flag{admin_credentials.txt}"
    cipher_text = cipher_suite.encrypt(flag_data)

    with open(enc_path, 'wb') as enc_file:
        enc_file.write(cipher_text)

    print(f"[+] Flag encrypted as 'manifest.enc'")
    print(f"[+] Encryption key saved as 'vault.key'")
    print(f"    (In production, vault.key sits on the DB server only)")


def reset_security_log():
    """Reset security.log to clean state."""
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'security.log')
    with open(log_path, 'w') as f:
        f.write("")
    print("\n[+] security.log reset to clean state")


if __name__ == '__main__':
    print("=" * 60)
    print("  VANGUARD LOGISTICS — Database & Encryption Setup")
    print("=" * 60)
    print()
    setup_database()
    create_encrypted_flag()
    reset_security_log()
    print()
    print("=" * 60)
    print("  Setup Complete. Ready for deployment.")
    print("=" * 60)