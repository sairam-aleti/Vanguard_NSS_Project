#!/bin/bash
# ═══════════════════════════════════════════════════════
# Vanguard Logistics — iptables Firewall Hardening
# ═══════════════════════════════════════════════════════
# Run this on the Ubuntu VMs after deployment.
# Usage: sudo bash iptables-rules.sh [webserver|dbserver]
# ═══════════════════════════════════════════════════════

set -e

if [ "$1" == "webserver" ]; then
    echo "[*] Applying iptables rules for WEB SERVER (DMZ)"

    # Flush existing rules
    iptables -F
    iptables -X

    # Default policies: DROP everything
    iptables -P INPUT DROP
    iptables -P FORWARD DROP
    iptables -P OUTPUT ACCEPT

    # Allow loopback
    iptables -A INPUT -i lo -j ACCEPT

    # Allow established/related connections
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    # Allow HTTP (Port 80) from anywhere (public web)
    iptables -A INPUT -p tcp --dport 80 -j ACCEPT

    # Allow HTTPS (Port 443) from anywhere
    iptables -A INPUT -p tcp --dport 443 -j ACCEPT

    # Allow SSH on non-standard port 58229 (restricted)
    iptables -A INPUT -p tcp --dport 58229 -j ACCEPT

    # Allow ICMP ping (for monitoring)
    iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT

    # Log dropped packets
    iptables -A INPUT -j LOG --log-prefix "[VG-DROP] " --log-level 4

    echo "[+] Web Server iptables rules applied"

elif [ "$1" == "dbserver" ]; then
    echo "[*] Applying iptables rules for DATABASE SERVER (Internal)"

    # Flush existing rules
    iptables -F
    iptables -X

    # Default policies: DROP everything
    iptables -P INPUT DROP
    iptables -P FORWARD DROP
    iptables -P OUTPUT ACCEPT

    # Allow loopback
    iptables -A INPUT -i lo -j ACCEPT

    # Allow established/related connections
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    # CRITICAL: Allow Port 5000 ONLY from Web Server (192.168.50.10)
    # This is the "Legacy API Sync" loophole
    iptables -A INPUT -p tcp -s 192.168.50.10 --dport 5000 -j ACCEPT -m comment --comment "Legacy API Sync"

    # Allow SSH on port 58229 (for admin access only)
    iptables -A INPUT -p tcp --dport 58229 -j ACCEPT

    # DROP all other traffic to port 5000
    iptables -A INPUT -p tcp --dport 5000 -j DROP

    # Log dropped packets
    iptables -A INPUT -j LOG --log-prefix "[VG-INT-DROP] " --log-level 4

    echo "[+] Database Server iptables rules applied"

else
    echo "Usage: sudo bash iptables-rules.sh [webserver|dbserver]"
    exit 1
fi

echo ""
echo "[*] Current iptables rules:"
iptables -L -v -n --line-numbers
echo ""
echo "[!] Remember to persist rules: sudo apt install iptables-persistent && sudo netfilter-persistent save"
