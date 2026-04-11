import sqlite3
import hashlib
import os
from cryptography.fernet import Fernet

def setup_database():
    print("[*] Initializing Vanguard Database...")
    conn = sqlite3.connect('vanguard.db')
    cursor = conn.cursor()

    # Create the users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Create weak MD5 hashes for the Red Team to crack
    # employee1 hash is "operator"
    # admin hash is "admin_core_77"
    emp_hash = hashlib.md5(b"operator").hexdigest()
    admin_hash = hashlib.md5(b"admin_core_77").hexdigest()

    # Insert the users (IGNORE if they already exist)
    cursor.execute("INSERT OR IGNORE INTO users (id, username, password_hash, role) VALUES (1, 'employee1', ?, 'logistics')", (emp_hash,))
    cursor.execute("INSERT OR IGNORE INTO users (id, username, password_hash, role) VALUES (2, 'admin', ?, 'administrator')", (admin_hash,))

    conn.commit()
    conn.close()
    print("[+] Database 'vanguard.db' created successfully with seeded users.")

def create_encrypted_flag():
    print("[*] Encrypting VIP Cargo Manifest (Target Flag)...")
    
    # Generate the AES key (In Phase 2, this will be hidden on the DB Server)
    key = Fernet.generate_key()
    with open('vault.key', 'wb') as key_file:
        key_file.write(key)
        
    # Encrypt the flag
    cipher_suite = Fernet(key)
    flag_data = b"flag{admin_credentials.txt}"
    cipher_text = cipher_suite.encrypt(flag_data)
    
    with open('manifest.enc', 'wb') as enc_file:
        enc_file.write(cipher_text)
        
    print("[+] Flag encrypted as 'manifest.enc' and key saved as 'vault.key'.")

if __name__ == '__main__':
    setup_database()
    create_encrypted_flag()