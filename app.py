from flask import Flask, request, session, redirect, url_for, render_template_string
import sqlite3
import hashlib
import requests
import urllib.parse

app = Flask(__name__)
app.secret_key = "vanguard_super_secret_session_key"

# --- HTML TEMPLATES (Embedded for simplicity) ---
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Vanguard Logistics - Portal</title></head>
<body style="background-color:#1e1e2f; color:#c7c7d4; font-family:Arial; text-align:center; padding-top:50px;">
    <h2>Vanguard Logistics - DMZ Access</h2>
    <form method="POST" action="/login">
        <input type="text" name="username" placeholder="Username" required><br><br>
        <input type="password" name="password" placeholder="Password" required><br><br>
        <input type="submit" value="Login">
    </form>
    <p style="color:red;">{{ error }}</p>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head><title>Vanguard - Dashboard</title></head>
<body style="background-color:#1e1e2f; color:#c7c7d4; font-family:Arial; padding:20px;">
    <h2>Welcome, {{ username }}</h2>
    <p>Role: {{ role }}</p>
    <hr>
    <h3>Customs API Fetcher (Internal Tool)</h3>
    <p>Fetch remote shipping manifests or API data.</p>
    <form method="GET" action="/fetch_data">
        <input type="text" name="url" size="50" placeholder="http://example.com/api" required>
        <input type="submit" value="Fetch Data">
    </form>
    <br>
    <a href="/logout" style="color:#00ffcc;">Logout</a>
</body>
</html>
"""

# --- CORE LOGIC ---

@app.route('/', methods=['GET'])
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML, error="")

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    hashed_pw = hashlib.md5(password.encode()).hexdigest()

    conn = sqlite3.connect('vanguard.db')
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE username=? AND password_hash=?", (username, hashed_pw))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['username'] = username
        session['role'] = user[0]
        return redirect(url_for('dashboard'))
    else:
        return render_template_string(LOGIN_HTML, error="Invalid credentials. Intrusion logged.")

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template_string(DASHBOARD_HTML, username=session['username'], role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- VULNERABILITY: THE SSRF ENDPOINT ---

def is_safe_url(target_url):
    """
    WEAK FILTER: The developer tried to block internal routing, 
    but forgot about Decimal IPs and IPv6 loopbacks.
    """
    blacklist = ['127.0.0.1', 'localhost', '10.0.0.15', '192.168.']
    parsed_url = urllib.parse.urlparse(target_url)
    hostname = parsed_url.hostname
    
    if not hostname:
        return False
        
    for blocked in blacklist:
        if blocked in hostname:
            return False
    return True

@app.route('/fetch_data', methods=['GET'])
def fetch_data():
    if 'username' not in session:
        return redirect(url_for('index'))
        
    target_url = request.args.get('url')
    if not target_url:
        return "Please provide a URL.", 400

    # The Vulnerable Logic
    if is_safe_url(target_url):
        try:
            # SSRF Execution: The server makes the request on behalf of the user
            response = requests.get(target_url, timeout=3)
            return f"<pre>{response.text}</pre>"
        except Exception as e:
            return f"Error fetching remote API: {e}", 500
    else:
        # ... (rest of the fetch_data function above)
        if is_safe_url(target_url):
            try:
                # SSRF Execution: The server makes the request on behalf of the user
                response = requests.get(target_url, timeout=3)
                return f"<pre>{response.text}</pre>"
            except Exception as e:
                return f"Error fetching remote API: {e}", 500
        else:
            # --- NEW CODE: Write to the SIEM log ---
            with open("security.log", "a") as log_file:
                log_file.write(f"BLOCKED SSRF ATTEMPT: {target_url}\n")
            # ---------------------------------------
            return "<b>[SECURITY ALERT]</b> Internal IP addresses are strictly prohibited. Action logged.", 403

if __name__ == '__main__':
    # Running on port 80 locally for testing
    app.run(host='0.0.0.0', port=80, debug=True)