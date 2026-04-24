#!/bin/bash
# Vanguard Logistics — Backup Config Decoy Generator
# Creates small, misleading files in /backup_configs/ to waste Red Team time
# These files are intentionally corrupted or contain fake data

BACKUP_DIR="/opt/vanguard/backup_configs"
mkdir -p "$BACKUP_DIR"

echo "[*] Generating decoy backup files..."

# Fake SSH keys (corrupted, won't work)
cat > "$BACKUP_DIR/id_rsa_admin.bak" << 'EOF'
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBzV2F4aGVkX2Zha2Vfa2V5X3Zhbmd1YXJkXzIwMjQAAAA=
CORRUPTED_DATA_BLOCK_RECOVERY_FAILED_0x4F2A
Backup restored from: tape-vault-03 (Rotterdam DC)
Admin: Hans van der Berg <hvdberg@vanguard-logistics.internal>
Last rotation: 2024-09-15
-----END OPENSSH PRIVATE KEY-----
EOF

# Fake database dump header (truncated, useless)
cat > "$BACKUP_DIR/vanguard_full_backup_2024Q3.sql.gz.part1" << 'EOF'
VANGUARD LOGISTICS - EMERGENCY DATABASE BACKUP
================================================
Backup ID: VG-BKP-2024-Q3-FULL-001
Server: db-primary-01.secure.vanguard.internal
Date: 2024-09-30T02:00:00Z
Size: 2.3 GB (compressed)
Status: SPLIT ARCHIVE - Part 1 of 47

WARNING: This is a partial archive. All 47 parts are required for restoration.
Parts 2-47 stored on: tape-vault-03 (Rotterdam Secure DC)
Contact: sysadmin@vanguard-logistics.internal

[BINARY DATA FOLLOWS - CORRUPTED AFTER BYTE 1024]
EOF
# Append random binary-looking data
head -c 4096 /dev/urandom 2>/dev/null | base64 >> "$BACKUP_DIR/vanguard_full_backup_2024Q3.sql.gz.part1" 2>/dev/null || \
python3 -c "import os,base64;print(base64.b64encode(os.urandom(4096)).decode())" >> "$BACKUP_DIR/vanguard_full_backup_2024Q3.sql.gz.part1"

# Fake firewall config export
cat > "$BACKUP_DIR/pfsense_export_20240915.xml" << 'EOF'
<?xml version="1.0"?>
<!-- pfSense Configuration Export
     Host: fw-edge-01.vanguard.internal
     Date: 2024-09-15
     NOTE: Passwords redacted per VG-SEC-POL-2024
-->
<pfsense>
  <version>24.03</version>
  <system>
    <hostname>fw-edge-01</hostname>
    <domain>vanguard.internal</domain>
    <dns>8.8.8.8 8.8.4.4</dns>
    <!-- SSH moved to 58229 per IT-SEC-MEMO-2024-Q3-0147 -->
    <ssh><port>58229</port><enabled>yes</enabled></ssh>
  </system>
  <interfaces>
    <wan><ipaddr>dhcp</ipaddr><desc>WAN - External</desc></wan>
    <dmz><ipaddr>192.168.50.1</ipaddr><subnet>24</subnet></dmz>
  </interfaces>
  <filter>
    <rule>
      <desc>Legacy API Sync - DO NOT REMOVE - Required for customs integration</desc>
      <source>192.168.50.10</source>
      <destination>10.0.0.15</destination>
      <port>5000</port>
      <protocol>tcp</protocol>
      <action>pass</action>
    </rule>
    <!-- TRUNCATED: Export corrupted at this point -->
  </filter>
</pfsense>
EOF

# Fake .env file with misleading credentials
cat > "$BACKUP_DIR/.env.production.bak" << 'EOF'
# Vanguard Logistics — Production Environment
# Last updated: 2024-08-20 by sysadmin
# DO NOT COMMIT TO VERSION CONTROL

DATABASE_URL=postgresql://vanguard_app:Str0ng!P@ss2024@db-primary:5432/vanguard_prod
REDIS_URL=redis://cache-01.internal:6379/0
SECRET_KEY=vg_prod_8f14e45fceea167a5a36dedd4bea2543
SMTP_PASSWORD=Vg!Mail#2024Secure
AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# NOTE: These credentials rotated on 2024-09-01
# Current credentials in HashiCorp Vault: vault.vanguard.internal
EOF

# Fake SSL certificate (expired)
cat > "$BACKUP_DIR/wildcard_vanguard-logistics.com.pem.expired" << 'EOF'
-----BEGIN CERTIFICATE-----
MIIFzTCCBLWgAwIBAgISA1234FakeVanguardCertExpired
Issuer: Let's Encrypt Authority X3
Validity:
    Not Before: Jan 15 00:00:00 2023 GMT
    Not After : Apr 15 23:59:59 2023 GMT  << EXPIRED
Subject: CN=*.vanguard-logistics.com

THIS CERTIFICATE HAS EXPIRED AND IS RETAINED FOR AUDIT PURPOSES ONLY.
Current certificate managed via Certbot auto-renewal.
Contact: it-security@vanguard-logistics.internal
-----END CERTIFICATE-----
EOF

echo "[+] Decoy files created in $BACKUP_DIR"
echo "    - id_rsa_admin.bak (corrupted SSH key)"
echo "    - vanguard_full_backup_2024Q3.sql.gz.part1 (truncated archive)"
echo "    - pfsense_export_20240915.xml (firewall config with hints)"
echo "    - .env.production.bak (rotated/fake credentials)"
echo "    - wildcard_vanguard-logistics.com.pem.expired (expired cert)"
echo ""
echo "Total size: < 20 KB"
