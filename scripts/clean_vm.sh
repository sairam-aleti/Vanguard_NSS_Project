#!/bin/bash
# Vanguard Logistics - VM Sanitization Script
# Run this right before shutting down the VM to export the .ova for the TA

if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root (sudo ./clean_vm.sh)"
  exit 1
fi

echo "[*] Stopping Vanguard services..."
systemctl stop vanguard-web vanguard-api vanguard-siem

echo "[*] Cleaning database, logs, and WAF bans..."
rm -f /opt/vanguard/vanguard.db
rm -f /opt/vanguard/vault.key
rm -f /opt/vanguard/manifest.enc
rm -f /opt/vanguard/security.log
rm -f /opt/vanguard/siem_daemon.log
rm -f /opt/vanguard/banned_ips.json

echo "[*] Generating fresh database and encrypted flags..."
cd /opt/vanguard
# We run this as the vanguard user so the file ownership is correct
sudo -u vanguard bash -c 'source venv/bin/activate && python3 db_setup.py'

echo "[*] Restarting services..."
systemctl start vanguard-web vanguard-api vanguard-siem

echo "[*] Emptying bash history to hide commands from TA..."
history -c
cat /dev/null > /root/.bash_history
for user_dir in /home/*; do
    if [ -f "$user_dir/.bash_history" ]; then
        cat /dev/null > "$user_dir/.bash_history"
    fi
done

echo "[+] ────────────────────────────────────────────────────────"
echo "[+] VM is fully sanitized and ready for OVA export!"
echo "[+] You can now run 'poweroff' to shut down the VM."
echo "[+] ────────────────────────────────────────────────────────"
