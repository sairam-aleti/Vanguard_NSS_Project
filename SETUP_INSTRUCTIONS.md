# Automated Setup Instructions for Antigravity

Read this file and execute every command below in order. Do not skip any step. Run each command in the terminal and wait for it to complete before running the next one.

## Step 1
Run this command in the terminal to create a virtual environment:
```
python -m venv venv
```

## Step 2
Run this command to activate the virtual environment:
```
.\venv\Scripts\Activate.ps1
```

## Step 3
Run this command to install all required Python packages:
```
pip install flask requests cryptography
```

## Step 4
Run this command to initialize the database and generate encryption keys:
```
python db_setup.py
```

## Step 5
Start the Internal API server. Run this command:
```
.\venv\Scripts\Activate.ps1; python internal_api.py
```
This will keep running. Do not stop it.

## Step 6
Open a second terminal. Start the SIEM daemon by running:
```
.\venv\Scripts\Activate.ps1; python siem_daemon.py
```
This will keep running. Do not stop it.

## Step 7
Open a third terminal. Start the web application by running:
```
.\venv\Scripts\Activate.ps1; python app.py
```
This will keep running. Do not stop it.

## Done
All three services are now running. Open a browser and go to http://localhost to see the website.
