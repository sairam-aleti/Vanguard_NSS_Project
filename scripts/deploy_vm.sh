#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Project Vanguard — Single VM Automated Deployment Script
# ═══════════════════════════════════════════════════════════
#  Instructions:
#  1. SSH into your college VM
#  2. Copy this file into the VM (e.g. nano deploy_vm.sh, paste, save)
#  3. Make it executable: chmod +x deploy_vm.sh
#  4. Run it: sudo ./deploy_vm.sh
# ═══════════════════════════════════════════════════════════

set -e

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run as root (sudo ./deploy_vm.sh)"
  exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  PROJECT VANGUARD — VM Automated Deployment"
echo "═══════════════════════════════════════════════════"
echo ""

# 1. System Updates & Dependencies
echo "[1/7] Updating system and installing dependencies..."
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git gcc make iptables

# 2. Clone Repository
echo "[2/7] Cloning Project Vanguard repository..."
if [ -d "/opt/vanguard" ]; then
    echo "       /opt/vanguard already exists. Removing old version..."
    rm -rf /opt/vanguard
fi
git clone https://github.com/sairam-aleti/Vanguard_NSS_Project.git /opt/vanguard
cd /opt/vanguard

# 3. Create Dedicated User
echo "[3/7] Setting up dedicated 'vanguard' user..."
if id "vanguard" &>/dev/null; then
    echo "       User vanguard already exists."
else
    useradd -m -s /bin/bash vanguard
fi
chown -R vanguard:vanguard /opt/vanguard

# 4. Setup Python Environment & Database
echo "[4/7] Setting up Python virtual environment and database..."
sudo -u vanguard bash -c '
    cd /opt/vanguard
    python3 -m venv venv
    source venv/bin/activate
    pip install flask requests cryptography
    python3 db_setup.py
'

# 5. Deploy Buffer Overflow Exploit (Phase 6)
echo "[5/7] Compiling and deploying SUID buffer overflow vulnerability..."
cd /opt/vanguard/exploit
chmod +x deploy_bof.sh
./deploy_bof.sh
cd /opt/vanguard

# 6. Apply SSH Hardening Misconfiguration (Phase 5)
echo "[6/7] Applying SSH configuration for CTF..."
cp /opt/vanguard/config/sshd_config /etc/ssh/sshd_config
systemctl restart sshd

# 7. Setup Systemd Services (Background Daemons)
echo "[7/7] Installing background services and internal firewall..."

# Simulate the "Internal Secure Zone" on a single VM
# Block external access to Port 5000, only allow localhost (SSRF vector)
iptables -A INPUT -p tcp --dport 5000 -s 127.0.0.1 -j ACCEPT
iptables -A INPUT -p tcp --dport 5000 -j DROP
netfilter-persistent save || true
cat << 'EOF' > /etc/systemd/system/vanguard-web.service
[Unit]
Description=Vanguard Web App (Port 80)
After=network.target

[Service]
User=root
WorkingDirectory=/opt/vanguard
ExecStart=/opt/vanguard/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat << 'EOF' > /etc/systemd/system/vanguard-api.service
[Unit]
Description=Vanguard Internal API (Port 5000)
After=network.target

[Service]
User=vanguard
WorkingDirectory=/opt/vanguard
ExecStart=/opt/vanguard/venv/bin/python internal_api.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat << 'EOF' > /etc/systemd/system/vanguard-siem.service
[Unit]
Description=Vanguard SIEM Daemon
After=network.target

[Service]
User=root
WorkingDirectory=/opt/vanguard
ExecStart=/opt/vanguard/venv/bin/python siem_daemon.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vanguard-web vanguard-api vanguard-siem
systemctl start vanguard-web vanguard-api vanguard-siem

echo ""
echo "═══════════════════════════════════════════════════"
echo "  DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════"
echo "  Services Running:"
echo "  - Web Application:   http://<VM_IP> (Port 80)"
echo "  - Internal API:      http://<VM_IP>:5000 (Blocked from outside)"
echo "  - SIEM Daemon:       Background monitoring active"
echo "  - Vulnerable SSH:    Port 58229"
echo ""
echo "  You can monitor logs using:"
echo "  journalctl -u vanguard-web -f"
echo "  journalctl -u vanguard-siem -f"
echo "═══════════════════════════════════════════════════"
