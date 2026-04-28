# Step-by-Step Local VM Setup Guide

This guide will walk you through exactly how to set up the Vanguard Logistics CTF environment inside a Virtual Machine on your Windows laptop. By following this, you will create the exact `.ova` file you need to submit to your TA.

---

## STEP 1: Download Required Software

You only need to download two things. Both are completely free.

### 1. Download VirtualBox
*   **What it is:** The software that lets you run a "virtual computer" inside your Windows laptop.
*   **Where to get it:** Go to [virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads)
*   **What to click:** Click on **"Windows hosts"** to download the `.exe` installer.
*   **Installation:** Double-click the downloaded file and click "Next" through the standard installation. Leave all default settings.

### 2. Download Ubuntu Server 22.04 LTS
*   **What it is:** The Linux Operating System (ISO file) that will act as our vulnerable web server. We are using the "Server" version because it has no heavy graphical UI, meaning it will run incredibly fast on your 8GB laptop.
*   **Where to get it:** Go to [ubuntu.com/download/server](https://ubuntu.com/download/server)
*   **What to click:** Click the green **"Download Ubuntu Server 22.04.4 LTS"** button. (Do not get 24.04, stick to 22.04 LTS for maximum stability).
*   **File:** It will download a file ending in `.iso` (around 2GB). Wait for it to finish.

---

## STEP 2: Create the Virtual Machine

Now we will build the "fake computer" inside VirtualBox.

1. Open **Oracle VM VirtualBox**.
2. Click the blue **"New"** button at the top.
3. Fill in the details:
   *   **Name:** `Vanguard_CTF_Server`
   *   **Folder:** Leave as default.
   *   **ISO Image:** Click the dropdown, select "Other...", and find the `ubuntu-22.04...live-server-amd64.iso` file you just downloaded.
   *   Check the box that says **"Skip Unattended Installation"** (This is very important!).
   *   Click **Next**.
4. **Hardware Settings:**
   *   **Base Memory:** Set to `1024 MB` (This is 1GB RAM. Your laptop has 8GB, so this leaves plenty for Windows).
   *   **Processors:** Set to `1` or `2` CPUs.
   *   Click **Next**.
5. **Virtual Hard disk:**
   *   Leave "Create a Virtual Hard Disk Now" checked.
   *   Set the size to `15.00 GB`.
   *   Click **Next**, then **Finish**.

---

## STEP 3: Configure VM Network (CRITICAL)

Before turning the VM on, we must ensure your Windows laptop can talk to it, and that the VM has internet access to download the project.

1. In VirtualBox, click on `Vanguard_CTF_Server` on the left side to select it.
2. Click the orange **"Settings"** gear icon at the top.
3. On the left menu, click **"Network"**.
4. **Adapter 1:** Leave this set to **NAT**. *(This gives the VM internet access).*
5. Click the tab for **Adapter 2** at the top.
6. Check the box to **"Enable Network Adapter"**.
7. Change "Attached to" to **"Host-only Adapter"**. *(This creates a private tunnel so your Windows laptop can hack the VM).*
8. Click **OK**.

---

## STEP 4: Install Ubuntu Server

Now we turn on the machine and install the OS.

1. Click the green **"Start"** arrow to turn on the VM. A black window will pop up.
2. Use your keyboard arrows to select **"Try or Install Ubuntu Server"** and press Enter.
3. The installer will load (it looks like a retro hacking terminal). Use **Arrow Keys** to move, **Spacebar** to select, and **Enter** to confirm.
4. **Follow these steps in the installer:**
   *   Language: **English**
   *   Keyboard: **Done**
   *   Network: It should say something like `enp0s3 dhcp 192.168.x.x`. Hit **Done**.
   *   Proxy: Leave blank, hit **Done**.
   *   Archive mirror: Hit **Done**.
   *   Storage: Leave "Use an entire disk" checked. Hit **Done**, then **Done** again, then **Continue**.
5. **Profile Setup (Important!):**
   *   Your name: `student`
   *   Your server's name: `vanguard-server`
   *   Pick a username: `student`
   *   Choose a password: `password123` (Keep it simple, this is just for you to log in to set it up).
   *   Hit **Done**.
6. **Ubuntu Pro:** Select "Skip for now", hit **Done**.
7. **SSH Setup:** Check the box that says **"Install OpenSSH server"** (press Spacebar). Hit **Done**.
8. **Featured Server Snaps:** Don't select anything, just hit **Done**.

The system will now install. This takes about 5-10 minutes. When it says **"Install complete!"** at the top, click **"Reboot Now"** at the bottom.
*(Press Enter if it says "Please remove the installation medium".)*

---

## STEP 5: Run the Magic Deployment Script

Your VM will restart. You will see a black screen asking for a login.

1. Type `student` and press Enter.
2. Type `password123` and press Enter. (You won't see the password typing, this is normal in Linux).
3. First, let's find the IP address of your VM. Type:
   ```bash
   ip a
   ```
   *Look for `enp0s8` or `eth1`. It will say `inet 192.168.56.X`. Write this IP address down!*
4. Now, we download and run the script I made for you. Type these exact three lines:
   ```bash
   wget https://raw.githubusercontent.com/sairam-aleti/Vanguard_NSS_Project/main/scripts/deploy_vm.sh
   chmod +x deploy_vm.sh
   sudo ./deploy_vm.sh
   ```
   *(It will ask for your `password123` once. Enter it.)*

**Sit back and watch.** The script will automatically download Python, clone your GitHub project, set up the database, compile the buffer overflow C exploit, misconfigure the SSH settings, and start the web server in the background.

When it finishes, it will say **DEPLOYMENT COMPLETE!**

---

## STEP 6: Export the .OVA File for your TA

Once you have verified the deployment works:

1. In the Ubuntu VM terminal, type `sudo poweroff` and press Enter to shut it down.
2. Go back to the main VirtualBox window on your laptop.
3. Click **File → Export Appliance**.
4. Select `Vanguard_CTF_Server` and click **Next**.
5. Choose where to save the file (e.g., your Desktop). The format should be **Open Virtualization Format 1.0**. Click **Next**.
6. Click **Export**.

VirtualBox will compress the VM into a single `.ova` file. This is the exact file you will upload/give to your TA!

---

## STEP 7: You Are Ready to Attack!

To practice attacking it yourself:
1. Start the VM again in VirtualBox.
2. Do not close the VirtualBox window, but you can minimize it.
3. On your **Windows laptop**, open Chrome or Edge and type in the IP address you wrote down in Step 5 (e.g., `http://192.168.1.50`).

You will see the Vanguard Logistics website! You have successfully built the target. You can now follow the `RED_TEAM_PLAYBOOK.md` from top to bottom.
