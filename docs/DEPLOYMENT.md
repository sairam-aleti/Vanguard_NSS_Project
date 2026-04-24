# Project Vanguard — Deployment Guide

## Complete VirtualBox & pfSense Setup for 16GB RAM Machine

> This guide covers the full deployment of the Vanguard Logistics CTF environment
> across 3 virtual machines with dual-firewall architecture.

---

## 1. Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| Storage | 40 GB free | 80 GB free |
| CPU | 4 cores | 6+ cores |
| Network | NAT capable | NAT + bridged |

### RAM Allocation Plan (16GB Host)

| VM | RAM | Disk | Purpose |
|----|-----|------|---------|
| Edge Firewall (pfSense) | 512 MB | 4 GB | WAN ↔ DMZ gateway |
| Internal Firewall (pfSense) | 512 MB | 4 GB | DMZ ↔ Secure gateway |
| Web Server (Ubuntu) | 2 GB | 15 GB | Flask app + SIEM |
| Database Server (Ubuntu) | 1 GB | 10 GB | Internal API + SQLite |
| **Total VM usage** | **4 GB** | **33 GB** | |
| Host OS overhead | ~4 GB | — | Windows/Linux host |
| **Available headroom** | **~8 GB** | — | For development tools |

---

## 2. Download Required ISOs

1. **pfSense Community Edition**: https://www.pfsense.org/download/
   - Architecture: AMD64 | Installer: USB Memstick | Format: .gz
2. **Ubuntu Server 22.04 LTS**: https://ubuntu.com/download/server
   - Download the "Ubuntu Server 22.04.x LTS" ISO (no GUI)

---

## 3. VirtualBox Network Configuration

### 3.1 Create Internal Networks

Open VirtualBox → File → Preferences → Network or use the command line:

```bash
# Create the two internal networks
VBoxManage natnetwork add --netname "VG-DMZ" --network "192.168.50.0/24" --enable
VBoxManage natnetwork add --netname "VG-SECURE" --network "10.0.0.0/24" --enable
```

Or manually in the GUI:
- **VG-DMZ**: Internal Network name = `intnet-dmz`
- **VG-SECURE**: Internal Network name = `intnet-secure`

### 3.2 VM Network Adapter Configuration

#### Edge Firewall (pfSense #1)
| Adapter | Attached To | Network Name |
|---------|-------------|--------------|
| Adapter 1 | NAT | — (WAN) |
| Adapter 2 | Internal Network | `intnet-dmz` |

#### Internal Firewall (pfSense #2)
| Adapter | Attached To | Network Name |
|---------|-------------|--------------|
| Adapter 1 | Internal Network | `intnet-dmz` |
| Adapter 2 | Internal Network | `intnet-secure` |

#### Web Server (Ubuntu #1)
| Adapter | Attached To | Network Name |
|---------|-------------|--------------|
| Adapter 1 | Internal Network | `intnet-dmz` |

#### Database Server (Ubuntu #2)
| Adapter | Attached To | Network Name |
|---------|-------------|--------------|
| Adapter 1 | Internal Network | `intnet-secure` |

---

## 4. pfSense Installation & Configuration

### 4.1 Edge Firewall Setup

1. Boot from pfSense ISO → Install → Accept defaults
2. After reboot, assign interfaces:
   - `em0` → WAN (NAT adapter, gets DHCP from VirtualBox)
   - `em1` → LAN (rename to DMZ)
3. Set DMZ interface IP:
   - IP: `192.168.50.1`
   - Subnet: `/24`
   - DHCP: Enable (range 192.168.50.100 - 192.168.50.200)

4. **Firewall Rules (via Web GUI at 192.168.50.1)**:

   **WAN Rules:**
   ```
   PASS  TCP  *  →  192.168.50.10:80   [Port Forward HTTP]
   PASS  TCP  *  →  192.168.50.10:58229 [Port Forward SSH]
   ```

   **DMZ Rules:**
   ```
   PASS  TCP  192.168.50.0/24  →  *  [Allow DMZ outbound]
   ```

### 4.2 Internal Firewall Setup

1. Boot from pfSense ISO → Install
2. Assign interfaces:
   - `em0` → OPT1 (rename to DMZ) = `192.168.50.2/24`
   - `em1` → LAN (rename to SECURE) = `10.0.0.1/24`
3. DHCP on SECURE: range 10.0.0.100 - 10.0.0.200

4. **Firewall Rules:**

   **DMZ → SECURE Rules:**
   ```
   PASS  TCP  192.168.50.10  →  10.0.0.15:5000  [Label: Legacy API Sync]
   DROP  *    *              →  10.0.0.0/24       [Label: Block All Inter-Subnet]
   ```

   **SECURE → DMZ Rules:**
   ```
   PASS  TCP  10.0.0.0/24  →  *  [Allow SECURE outbound for updates]
   ```

---

## 5. Ubuntu Server Setup

### 5.1 Web Server VM (192.168.50.10)

```bash
# Set static IP
sudo nano /etc/netplan/00-installer-config.yaml
```

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      addresses: [192.168.50.10/24]
      routes:
        - to: default
          via: 192.168.50.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
sudo netplan apply

# Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git vsftpd

# Create application user
sudo useradd -m -s /bin/bash vanguard
sudo mkdir -p /opt/vanguard
sudo chown vanguard:vanguard /opt/vanguard

# Deploy application
sudo -u vanguard bash -c '
    cd /opt/vanguard
    python3 -m venv venv
    source venv/bin/activate
    pip install flask requests cryptography
'

# Copy project files to /opt/vanguard/
# (Use SCP or USB to transfer files from your dev machine)

# Initialize database
sudo -u vanguard bash -c 'cd /opt/vanguard && source venv/bin/activate && python db_setup.py'

# Install systemd services
sudo cp /opt/vanguard/config/vanguard-web.service /etc/systemd/system/
sudo cp /opt/vanguard/config/vanguard-siem.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vanguard-web vanguard-siem
sudo systemctl start vanguard-web vanguard-siem

# Apply iptables rules
sudo bash /opt/vanguard/config/iptables-rules.sh webserver
sudo apt install -y iptables-persistent
sudo netfilter-persistent save

# SSH hardening
sudo cp /opt/vanguard/config/sshd_config /etc/ssh/sshd_config
sudo systemctl restart sshd

# vsftpd setup
sudo cp /opt/vanguard/config/vsftpd.conf /etc/vsftpd.conf
sudo systemctl restart vsftpd

# Health check crontab
sudo crontab -l 2>/dev/null | { cat; echo "*/2 * * * * /opt/vanguard/scripts/health_check.sh"; } | sudo crontab -

# Move SSH port (update your SSH client config!)
echo "SSH is now on port 58229"
```

### 5.2 Database Server VM (10.0.0.15)

```bash
# Set static IP
sudo nano /etc/netplan/00-installer-config.yaml
```

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      addresses: [10.0.0.15/24]
      routes:
        - to: default
          via: 10.0.0.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

```bash
sudo netplan apply

# Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv

# Create application user & deploy
sudo useradd -m -s /bin/bash vanguard
sudo mkdir -p /opt/vanguard
sudo chown vanguard:vanguard /opt/vanguard

sudo -u vanguard bash -c '
    cd /opt/vanguard
    python3 -m venv venv
    source venv/bin/activate
    pip install flask cryptography
'

# Copy internal_api.py, db_setup.py, vanguard.db, vault.key, manifest.enc

# Install systemd service
sudo cp /opt/vanguard/config/vanguard-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vanguard-api
sudo systemctl start vanguard-api

# Apply iptables rules
sudo bash /opt/vanguard/config/iptables-rules.sh dbserver
sudo apt install -y iptables-persistent
sudo netfilter-persistent save

# SSH hardening
sudo cp /opt/vanguard/config/sshd_config /etc/ssh/sshd_config
sudo systemctl restart sshd
```

---

## 6. Verification Checklist

```bash
# On Web Server (192.168.50.10):
curl http://localhost:80                     # Should return HTML
curl http://localhost:80/robots.txt          # Should show robots.txt
curl http://localhost:80/staff_portal        # Should show login page
systemctl status vanguard-web               # Should be active
systemctl status vanguard-siem              # Should be active

# On Database Server (10.0.0.15):
curl http://localhost:5000/api/health        # Should return JSON
curl http://localhost:5000/api/admin_keys    # Should return admin hash
systemctl status vanguard-api               # Should be active

# From Web Server → Database Server (test the "loophole"):
curl http://10.0.0.15:5000/api/admin_keys   # Should work (firewall allows this)

# From an external machine (should be blocked):
# Direct access to 10.0.0.15 should fail (blocked by pfSense)
```

---

## 7. Log Rotation Setup

```bash
# Prevent disk space exhaustion during Red Team scanning
sudo tee /etc/logrotate.d/vanguard << 'EOF'
/opt/vanguard/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 vanguard vanguard
    size 50M
}
EOF
```

---

## 8. Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 80 not reachable | Check iptables, systemd status, pfSense port forward |
| SSRF can't reach DB server | Verify pfSense Legacy API rule allows 192.168.50.10 → 10.0.0.15:5000 |
| Services crash on boot | Check logs: `journalctl -u vanguard-web -f` |
| SSH connection refused | SSH is on port 58229, not 22: `ssh -p 58229 vanguard@IP` |
| Database locked | Only one writer at a time — check for orphan processes |
