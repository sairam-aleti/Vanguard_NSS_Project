# Antigravity Setup Instructions for Project Vanguard

Follow these steps exactly to set up and run the project. Execute each command in the terminal.

## Step 1: Create Virtual Environment

Run this command in the terminal:

```
python -m venv venv
```

If `python` is not found, try `python3 -m venv venv` instead.

## Step 2: Activate the Virtual Environment

Run this command:

```
.\venv\Scripts\Activate.ps1
```

## Step 3: Install Dependencies

Run this command:

```
pip install flask requests cryptography
```

## Step 4: Initialize Database

Run this command:

```
python db_setup.py
```

This creates the database, users, shipment data, and encryption keys.

## Step 5: Start the Web Application

Run this command in the terminal:

```
python app.py
```

## Step 6: Open a SECOND terminal and start the Internal API

Activate venv first, then start the API:

```
.\venv\Scripts\Activate.ps1
python internal_api.py
```

## Step 7: Open a THIRD terminal and start the SIEM Daemon

Activate venv first, then start the SIEM:

```
.\venv\Scripts\Activate.ps1
python siem_daemon.py
```

## Step 8: Test in Browser

Open browser and go to: http://localhost

All pages:
- Home: http://localhost
- About: http://localhost/about
- Tracking: http://localhost/tracking
- Contact: http://localhost/contact
- Staff Portal (hidden): http://localhost/staff_portal
- Internal API: http://localhost:5000

Login credentials: employee1 / operator
