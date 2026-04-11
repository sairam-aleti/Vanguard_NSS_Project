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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vanguard Secure Gateway</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-200 min-h-screen flex items-center justify-center font-sans selection:bg-cyan-500/30">
    <div class="w-full max-w-md p-8 bg-slate-800/80 backdrop-blur-sm border border-slate-700/50 rounded-xl shadow-2xl shadow-cyan-900/20">
        <div class="mb-8 text-center">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-900/50 border border-cyan-500/30 mb-4 shadow-[0_0_15px_rgba(34,211,238,0.15)]">
                <svg class="w-8 h-8 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                </svg>
            </div>
            <h2 class="text-2xl font-bold tracking-tight text-white">Vanguard Secure Gateway</h2>
            <p class="text-sm text-slate-400 mt-2">Authorized Access Only</p>
        </div>

        {% if error %}
        <div class="mb-6 p-4 bg-red-900/30 border border-red-500/50 rounded-lg text-red-200 text-sm flex items-center">
            <svg class="w-5 h-5 mr-3 flex-shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>
            {{ error }}
        </div>
        {% endif %}

        <form method="POST" action="/login" class="space-y-6">
            <div>
                <label for="username" class="block text-sm font-medium text-slate-400 mb-1">Username</label>
                <input type="text" id="username" name="username" required 
                    class="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-all duration-200">
            </div>
            <div>
                <label for="password" class="block text-sm font-medium text-slate-400 mb-1">Password</label>
                <input type="password" id="password" name="password" required 
                    class="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-all duration-200">
            </div>
            <button type="submit" 
                class="w-full py-3 px-4 flex justify-center items-center bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 focus:ring-offset-slate-900">
                Authenticate
                <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path>
                </svg>
            </button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vanguard Command Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-200 min-h-screen font-sans">
    
    <!-- Navigation -->
    <nav class="bg-slate-800/90 border-b border-slate-700/50 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center space-x-3">
                    <svg class="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"></path>
                    </svg>
                    <span class="font-bold text-lg tracking-wide text-white">Vanguard Command Center</span>
                </div>
                <div>
                    <a href="/logout" class="flex items-center text-slate-400 hover:text-red-400 transition-colors duration-200 text-sm font-medium">
                        <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
                        </svg>
                        Logout
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        
        <!-- Profile Card -->
        <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6 shadow-lg flex items-center space-x-5">
            <div class="w-14 h-14 rounded-full bg-slate-900 border-2 border-cyan-500/50 flex items-center justify-center relative shadow-[0_0_10px_rgba(34,211,238,0.2)]">
                <svg class="w-7 h-7 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                </svg>
                <div class="absolute bottom-0 right-0 w-3.5 h-3.5 bg-green-500 border-2 border-slate-800 rounded-full"></div>
            </div>
            <div>
                <p class="text-sm font-medium text-slate-400 mb-0.5">Active Session</p>
                <h3 class="text-xl font-semibold text-white">{{ username }}</h3>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-900/30 text-cyan-300 border border-cyan-500/20 mt-1">
                    Role: {{ role }}
                </span>
            </div>
        </div>

        <!-- Core Tool -->
        <div class="bg-slate-800/80 border border-slate-700/50 rounded-xl overflow-hidden shadow-xl">
            <div class="px-6 py-5 border-b border-slate-700/50 bg-slate-800/50 flex items-center">
                <div class="w-2 h-2 rounded-full bg-cyan-400 mr-3 animate-pulse"></div>
                <h3 class="text-lg font-medium text-white">Customs API Fetcher</h3>
            </div>
            <div class="p-6">
                <div class="mb-5">
                    <p class="text-sm text-slate-400">Diagnostic Tool: Fetch remote shipping manifests or structured API data over internal network.</p>
                </div>
                <form method="GET" action="/fetch_data" class="flex flex-col sm:flex-row gap-4">
                    <div class="flex-grow relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <svg class="h-5 w-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"></path>
                            </svg>
                        </div>
                        <input type="text" name="url" placeholder="http://internal-api.vanguard/manifests" required
                            class="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 transition-all font-mono text-sm shadow-inner">
                    </div>
                    <button type="submit" 
                        class="w-full sm:w-auto px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg flex justify-center items-center hover:shadow-[0_0_15px_rgba(6,182,212,0.4)] transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 focus:ring-offset-slate-900 whitespace-nowrap">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path>
                        </svg>
                        Fetch Data
                    </button>
                </form>
            </div>
        </div>

    </main>
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