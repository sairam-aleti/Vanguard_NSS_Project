# 🛡️ Vanguard Logistics — Enterprise Network & Security Architecture

> **Notice:** This repository contains the deployable infrastructure for the Vanguard Logistics Corporate Network. This system was designed to emulate a secure, segmented enterprise environment with active monitoring and strict access controls.

---

## 1. System Overview & Architecture

Vanguard Logistics utilizes a segmented, two-tier logical architecture designed to protect sensitive shipping manifests and internal databases from external threats.

### 🌐 Tier 1: The Perimeter (Web Tier)
*   **Service:** Corporate Web Application & Staff Portal
*   **Port:** 80 (HTTP)
*   **Access:** Publicly routable
*   **Purpose:** Serves the public-facing corporate website, shipment tracking features, and the secure staff authentication portal. 

### 🗄️ Tier 2: The Secure Zone (Internal API & Database)
*   **Service:** Internal Logistics API & Vault
*   **Port:** 5000 (HTTP API)
*   **Access:** **Strictly Airgapped.** Blocked by internal `iptables` hardware-level firewalls. Only the Web Application (Tier 1) is authorized to communicate with this layer.
*   **Purpose:** Houses the encrypted `vanguard.db` database and the highly classified VIP Cargo Manifest.

---

## 2. Claimed Security Posture & Access Controls

Our network relies on a defense-in-depth strategy. We claim the following controls are fully implemented and effectively protect the network:

### 🔐 Authentication & Session Management
*   **Staff Portal:** Access to the internal staff dashboard requires valid credentials. Sessions are securely signed using Flask's state-of-the-art cryptographic cookie management to prevent tampering.
*   **Server Administration (SSH):** Remote administration is moved off the standard Port 22 to evade automated scanners. Furthermore, **Password Authentication is explicitly disabled.** Access requires 2048-bit RSA cryptographic keys, rendering brute-force attacks impossible.

### 🛡️ Active Threat Intelligence (Vanguard SIEM)
Vanguard Logistics does not rely solely on static firewalls. We have deployed a custom **Security Information and Event Management (SIEM) Daemon** that provides Advanced Active Defense:
*   **Multi-Signal Detection:** Continuously monitors logs for diverse attack signatures (Failed Logins, SSRF attempts, Rate Limit violations, CSRF mismatch).
*   **Behavioral Correlation:** Correlates disparate events originating from the same IP address to detect coordinated reconnaissance or exploitation attempts.
*   **Escalating Threat Levels:** Dynamically assigns Threat Scores to external IPs, escalating from GREEN (Normal) to DEFCON 1 (Critical).
*   **Active Defense:** At critical threat levels, the SIEM actively alters the environment (e.g., deploying honeypot data to mislead attackers) and dynamically injects `iptables` rules to temporarily ban hostile actors.

---

## 3. Project Deployment (For Grading/TAs)

The entire Vanguard Logistics network has been consolidated into a single, highly-stable automated deployment script for ease of testing on centralized VM servers. The script dynamically creates the users, builds the internal firewalls, compiles binaries, and registers the background systemd daemons.

### Automated VM Deployment
1. Install a fresh **Ubuntu Server 22.04 LTS** virtual machine.
2. Log in as any user and download the deployment script:
   ```bash
   wget https://raw.githubusercontent.com/sairam-aleti/Vanguard_NSS_Project/main/scripts/deploy_vm.sh
   ```
3. Make the script executable and run it as root:
   ```bash
   chmod +x deploy_vm.sh
   sudo ./deploy_vm.sh
   ```
4. The script will output the accessible IPs and ports upon completion. 

*Note: All services (`vanguard-web`, `vanguard-api`, `vanguard-siem`) run as background `systemd` daemons. You can monitor the active defense system in real-time via `journalctl -u vanguard-siem -f`.*

---

## ⚠️ Red Team Notice (Course Project Clause)

**As per the Networks and Systems Security II requirements, the security posture claimed above contains intentional deviations from the actual deployment.** 

This system is deliberately seeded with realistic, non-trivial vulnerabilities (arising from misconfiguration, weak assumptions, and overexposure). The Red Team is expected to interact with the system, identify where the "Claimed Posture" fails, and chain those vulnerabilities to extract the final encrypted VIP Cargo Manifest. 

*Happy Hunting.*
