"""
Vanguard Logistics — Main Web Application
==========================================
Flask web application serving the corporate logistics website.
Includes a hidden staff portal with intentional SSRF vulnerability
for CTF demonstration purposes.

SECURITY HARDENING (Red Team Audit v2):
    - SSRF: Scheme whitelist (http/https only), no redirects, response size cap
    - DoS: Request size limit, log rotation, rate limiting on all forms
    - Session: Regeneration on login, IP binding
    - Headers: Server header stripped, full security header set
    - Errors: Custom error pages, no information leaks

DEPLOYMENT:
    - Production: Run with debug=False on port 80
    - Bind to 0.0.0.0 for DMZ network access
"""

from flask import (
    Flask, request, session, redirect, url_for,
    render_template, jsonify, abort, make_response
)
import sqlite3
import hashlib
import requests as http_requests
import urllib.parse
import os
import re
import time
import datetime
import secrets

# ═══════════════════════════════════════════════
# APP CONFIGURATION
# ═══════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = os.environ.get('VG_SECRET_KEY', 'shipping')

# Session Security
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes

# [FIX #3] Request body size limit — prevents memory exhaustion DoS
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1 MB max

# Log file size cap (10 MB) — prevents disk exhaustion DoS [FIX #5]
MAX_LOG_SIZE = 10 * 1024 * 1024

# SSRF response size cap — prevents OOM [FIX #4]
MAX_SSRF_RESPONSE_SIZE = 512 * 1024  # 512 KB

# ═══════════════════════════════════════════════
# SECURITY MIDDLEWARE
# ═══════════════════════════════════════════════

# Unified rate limiting store (used for login, contact, tracking)
_rate_limits = {}
RATE_LIMIT_WINDOW = 60  # 1 minute window

RATE_LIMITS = {
    'login': 5,      # Max 5 login attempts per minute per IP
    'contact': 3,    # Max 3 contact submissions per minute per IP [FIX #8]
    'tracking': 10,  # Max 10 tracking queries per minute per IP [FIX #9]
    'ssrf': 15,      # Max 15 SSRF requests per minute per IP
}


@app.after_request
def apply_security_headers(response):
    """Apply comprehensive security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'

    # [FIX #6] Strip server header to hide technology stack
    response.headers.pop('Server', None)
    response.headers['Server'] = 'Vanguard-Gateway/4.2'

    return response


@app.before_request
def enforce_security():
    """Pre-request security enforcement."""
    # [WAF] Application-Layer Block Check
    try:
        import json
        banned_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banned_ips.json')
        if os.path.exists(banned_file):
            with open(banned_file, 'r') as f:
                banned_ips = json.load(f)
            if request.remote_addr in banned_ips:
                html_response = ERROR_PAGE.replace('{{ code }}', '403') \
                    .replace('{{ title }}', '🚨 VANGUARD SEC-OPS ALARM 🚨') \
                    .replace('{{ message }}', 'Your IP has been temporarily suspended due to a high Behavioral Threat Score. Our SIEM has detected coordinated suspicious activity.')
                
                # Remove the 'Return Home' button since the whole site is suspended
                import re
                html_response = re.sub(r'<a href="/".*?</a>', '', html_response, flags=re.DOTALL)
                
                return make_response(html_response, 403)
    except Exception:
        pass

    # [FIX #12] Block unexpected HTTP methods globally
    allowed_methods = {'GET', 'POST', 'HEAD', 'OPTIONS'}
    if request.method not in allowed_methods:
        log_security_event('BLOCKED_METHOD', request.remote_addr,
                           f'Method: {request.method} Path: {request.path}')
        abort(405)

    # CSRF protection for POST requests
    if request.method == "POST":
        token = session.get('csrf_token')
        form_token = request.form.get('csrf_token')
        if not token or not form_token or token != form_token:
            log_security_event('CSRF_VIOLATION', request.remote_addr, f'Path: {request.path}')
            abort(403)


def generate_csrf_token():
    """Generate a CSRF token for the session."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


# Make csrf_token() available in all templates
app.jinja_env.globals['csrf_token'] = generate_csrf_token


def check_rate_limit(ip, category='login'):
    """Universal rate limiter for any action category."""
    now = time.time()
    key = f"{category}:{ip}"
    max_attempts = RATE_LIMITS.get(category, 5)

    if key in _rate_limits:
        _rate_limits[key] = [t for t in _rate_limits[key] if now - t < RATE_LIMIT_WINDOW]
        if len(_rate_limits[key]) >= max_attempts:
            return False
    return True


def record_rate_limit(ip, category='login'):
    """Record an action for rate limiting."""
    key = f"{category}:{ip}"
    if key not in _rate_limits:
        _rate_limits[key] = []
    _rate_limits[key].append(time.time())

    # Periodic cleanup: remove stale entries to prevent memory growth
    if len(_rate_limits) > 10000:
        cutoff = time.time() - RATE_LIMIT_WINDOW
        stale = [k for k, v in _rate_limits.items() if all(t < cutoff for t in v)]
        for k in stale:
            del _rate_limits[k]


# ═══════════════════════════════════════════════
# DATABASE HELPER
# ═══════════════════════════════════════════════

def get_db():
    """Get a database connection with WAL mode and timeout."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vanguard.db')
    conn = sqlite3.connect(db_path, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ═══════════════════════════════════════════════
# LOGGING (with size cap)
# ═══════════════════════════════════════════════

def log_security_event(event_type, ip, details):
    """
    Write structured security events to security.log.
    [FIX #5] Caps log file at MAX_LOG_SIZE to prevent disk exhaustion.
    """
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'security.log')

    # Check log size before writing — rotate if too large
    try:
        if os.path.exists(log_path) and os.path.getsize(log_path) > MAX_LOG_SIZE:
            # Rotate: keep last 50% of log, discard oldest
            with open(log_path, 'r') as f:
                lines = f.readlines()
            half = len(lines) // 2
            with open(log_path, 'w') as f:
                f.writelines(lines[half:])
    except (IOError, OSError):
        pass

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Sanitize details to prevent log injection
    safe_details = details.replace('\n', ' ').replace('\r', ' ')[:500]
    log_entry = f"[{timestamp}] {event_type} | IP: {ip} | {safe_details}\n"
    try:
        with open(log_path, "a") as f:
            f.write(log_entry)
    except IOError:
        pass


# ═══════════════════════════════════════════════
# PUBLIC ROUTES — The Corporate "Mask"
# ═══════════════════════════════════════════════

@app.route('/', methods=['GET'])
def index():
    """Corporate landing page."""
    return render_template('index.html')


@app.route('/about', methods=['GET'])
def about():
    """Company information page."""
    return render_template('about.html')


@app.route('/tracking', methods=['GET', 'POST'])
def tracking():
    """Shipment tracking page — also acts as a reconnaissance honeypot."""
    result = None
    if request.method == 'POST':
        client_ip = request.remote_addr

        # [FIX #9] Rate limit tracking queries
        if not check_rate_limit(client_ip, 'tracking'):
            log_security_event('RATE_LIMITED', client_ip, 'Tracking query rate limit exceeded')
            return render_template('tracking.html', result=None), 429

        tracking_id = request.form.get('tracking_id', '').strip()
        # Sanitize: only allow alphanumeric and hyphens
        tracking_id = re.sub(r'[^a-zA-Z0-9\-]', '', tracking_id)

        if tracking_id and len(tracking_id) <= 30:
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT tracking_id, origin, destination, status, eta, weight "
                    "FROM shipments WHERE tracking_id=?",
                    (tracking_id,)
                )
                shipment = cursor.fetchone()
                conn.close()

                if shipment:
                    result = {
                        'tracking_id': shipment[0],
                        'origin': shipment[1],
                        'destination': shipment[2],
                        'status': shipment[3],
                        'eta': shipment[4],
                        'weight': shipment[5],
                    }
                else:
                    result = 'not_found'
            except Exception:
                result = 'not_found'

            # Log all tracking queries for SIEM correlation
            log_security_event('TRACKING_QUERY', client_ip, f'Query: {tracking_id}')
        else:
            result = 'not_found'

        record_rate_limit(client_ip, 'tracking')

    return render_template('tracking.html', result=result)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page with form submission."""
    contact_sent = False
    if request.method == 'POST':
        client_ip = request.remote_addr

        # [FIX #8] Rate limit contact form
        if not check_rate_limit(client_ip, 'contact'):
            log_security_event('RATE_LIMITED', client_ip, 'Contact form rate limit exceeded')
            return render_template('contact.html', contact_sent=False), 429

        name = request.form.get('name', '')[:100]
        email = request.form.get('email', '')[:100]
        # Validate email format loosely
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return render_template('contact.html', contact_sent=False)

        log_security_event('CONTACT_FORM', client_ip, f'From: {name}')
        record_rate_limit(client_ip, 'contact')
        contact_sent = True

    return render_template('contact.html', contact_sent=contact_sent)


# ═══════════════════════════════════════════════
# HIDDEN STAFF PORTAL — Accessible only via /staff_portal
# ═══════════════════════════════════════════════

@app.route('/portal', methods=['GET', 'POST'])
def staff_portal():
    """Hidden staff login page — not linked in navigation."""
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        client_ip = request.remote_addr

        # Rate limiting
        if not check_rate_limit(client_ip, 'login'):
            log_security_event('RATE_LIMITED', client_ip, 'Login rate limit exceeded')
            return render_template('portal.html', error='Too many login attempts. Access temporarily suspended. Incident logged.'), 429

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Input validation
        if len(username) > 50 or len(password) > 100:
            return render_template('portal.html', error='Invalid input.')

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return render_template('portal.html', error='Invalid username format.')

        # Authenticate with MD5 hash (intentionally weak for CTF)
        hashed_pw = hashlib.md5(password.encode()).hexdigest()

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role FROM users WHERE username=? AND password_hash=?",
                (username, hashed_pw)
            )
            user = cursor.fetchone()
            conn.close()
        except Exception:
            return render_template('portal.html', error='Authentication service unavailable.')

        record_rate_limit(client_ip, 'login')

        if user:
            # [FIX #7] Session regeneration to prevent session fixation
            # Clear the old session completely, then set new values
            old_csrf = session.get('csrf_token')
            session.clear()
            session.permanent = True
            session['username'] = username
            session['role'] = user[0]
            session['login_ip'] = client_ip
            session['login_time'] = time.time()
            if old_csrf:
                session['csrf_token'] = old_csrf
            log_security_event('LOGIN_SUCCESS', client_ip, f'User: {username}')
            return redirect(url_for('dashboard'))
        else:
            log_security_event('LOGIN_FAILED', client_ip, f'Attempted user: {username}')
            return render_template('portal.html', error='Invalid credentials. This attempt has been logged and reported to SOC.')

    return render_template('portal.html', error=None)


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Staff dashboard — requires authentication."""
    if 'username' not in session:
        return redirect(url_for('staff_portal'))
    return render_template('dashboard.html', username=session['username'], role=session['role'])


@app.route('/logout', methods=['GET'])
def logout():
    """Clear session and redirect to home."""
    if 'username' in session:
        log_security_event('LOGOUT', request.remote_addr, f'User: {session["username"]}')
    session.clear()
    return redirect(url_for('index'))


# ═══════════════════════════════════════════════
# SSRF VULNERABILITY — The Intentional Flaw
# ═══════════════════════════════════════════════

def is_safe_url(target_url):
    """
    SECURITY FILTER for the API Fetcher tool.

    BLOCKS:
      - Non-HTTP schemes (file://, ftp://, gopher://, dict://)  [FIX #1, #2]
      - Known internal IPs (127.0.0.1, localhost, 10.0.0.15, 192.168.x.x)
      - IPv6 loopback (::1, [::1])  [FIX #14]
      - Private network ranges (172.16-31.x.x, 169.254.x.x)

    INTENTIONAL WEAKNESS (CTF Design):
      - Decimal-encoded IPs bypass the string blacklist
      - e.g., 2130706433 = 127.0.0.1 — this is the Red Team attack vector
    """
    parsed = urllib.parse.urlparse(target_url)

    # [FIX #1, #2] SCHEME WHITELIST — block file://, ftp://, gopher://, dict://
    if parsed.scheme not in ('http', 'https'):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Convert to lowercase for case-insensitive matching
    hostname_lower = hostname.lower()

    # IP/hostname blacklist (catches common representations)
    blacklist = [
        '127.0.0.1',
        'localhost',
        '10.0.0.15',
        '192.168.',
        '0.0.0.0',
        '169.254.',     # Link-local
        '172.16.',      # Private class B
        '172.17.',
        '172.18.',
        '172.19.',
        '172.20.',
        '172.21.',
        '172.22.',
        '172.23.',
        '172.24.',
        '172.25.',
        '172.26.',
        '172.27.',
        '172.28.',
        '172.29.',
        '172.30.',
        '172.31.',
    ]

    for blocked in blacklist:
        if blocked in hostname_lower:
            return False

    # [FIX #14] Block IPv6 loopback representations
    ipv6_blacklist = ['::1', '0:0:0:0:0:0:0:1', '::ffff:127.0.0.1']
    # Strip brackets from IPv6 addresses
    stripped = hostname_lower.strip('[]')
    for blocked_v6 in ipv6_blacklist:
        if stripped == blocked_v6:
            return False

    # Block hex-encoded IPs (0x7f.0x0.0x0.0x1)
    if hostname_lower.startswith('0x'):
        return False

    # Block octal-encoded IPs (0177.0.0.1)
    if re.match(r'^0\d+\.', hostname_lower):
        return False

    # ──────────────────────────────────────────────
    # INTENTIONAL GAP: Pure decimal IPs (2130706433)
    # are NOT caught by string matching above.
    # This is the designed Red Team bypass vector.
    # ──────────────────────────────────────────────

    return True


@app.route('/fetch_data', methods=['GET'])
def fetch_data():
    """
    SSRF endpoint — fetches data from a user-supplied URL.
    The weak filter can be bypassed using decimal IP encoding.
    """
    if 'username' not in session:
        return redirect(url_for('staff_portal'))

    client_ip = request.remote_addr

    # Rate limit SSRF requests
    if not check_rate_limit(client_ip, 'ssrf'):
        log_security_event('RATE_LIMITED', client_ip, 'SSRF rate limit exceeded')
        return render_template(
            'dashboard.html',
            username=session['username'],
            role=session['role'],
            fetch_error='Rate limit exceeded. Please wait before making more requests.'
        ), 429

    target_url = request.args.get('url', '').strip()

    if not target_url:
        return render_template(
            'dashboard.html',
            username=session['username'],
            role=session['role'],
            fetch_error='No URL provided. Enter a target endpoint.'
        )

    # Input length check
    if len(target_url) > 500:
        return render_template(
            'dashboard.html',
            username=session['username'],
            role=session['role'],
            fetch_error='URL exceeds maximum length.'
        )

    record_rate_limit(client_ip, 'ssrf')

    if is_safe_url(target_url):
        # ──────────────────────────────────────────────
        # CTF ENGINEERING FIX: Python 'requests' struggles to resolve pure
        # decimal IPs via getaddrinfo on Windows, returning a DNS error.
        # We manually translate it here so the SSRF exploit works cross-platform.
        # ──────────────────────────────────────────────
        try:
            parsed_req = urllib.parse.urlparse(target_url)
            if parsed_req.hostname and parsed_req.hostname.isdigit():
                # Convert decimal IP back to dotted decimal for requests Lib
                ip_int = int(parsed_req.hostname)
                new_host = f"{(ip_int >> 24) & 255}.{(ip_int >> 16) & 255}.{(ip_int >> 8) & 255}.{ip_int & 255}"
                target_url = target_url.replace(parsed_req.hostname, new_host)
        except Exception:
            pass
            
        try:
            # [FIX #10] Disable redirect following — prevents blacklist bypass via 302
            # [FIX #4] Use streaming + size cap to prevent OOM
            response = http_requests.get(
                target_url,
                timeout=5,
                allow_redirects=False,
                stream=True
            )

            # Read response with size cap
            content_chunks = []
            bytes_read = 0
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                bytes_read += len(chunk)
                if bytes_read > MAX_SSRF_RESPONSE_SIZE:
                    content_chunks.append('\n\n[TRUNCATED: Response exceeded 512KB limit]')
                    break
                content_chunks.append(chunk if isinstance(chunk, str) else chunk.decode('utf-8', errors='replace'))
            response.close()

            raw_text = ''.join(content_chunks)

            log_security_event('SSRF_FETCH', client_ip,
                               f'URL: {target_url} | Status: {response.status_code} | Size: {bytes_read}')

            # Sanitize output — Jinja2 autoescapes, but belt-and-suspenders
            safe_text = raw_text.replace('<script', '&lt;script').replace('</script', '&lt;/script')

            return render_template(
                'dashboard.html',
                username=session['username'],
                role=session['role'],
                fetch_result=safe_text
            )

        except http_requests.exceptions.Timeout:
            return render_template(
                'dashboard.html',
                username=session['username'],
                role=session['role'],
                fetch_error='Connection timed out. Target host unreachable.'
            )
        except http_requests.exceptions.ConnectionError:
            return render_template(
                'dashboard.html',
                username=session['username'],
                role=session['role'],
                fetch_error='Connection refused. Host may be offline.'
            )
        except Exception:
            # [FIX #11] Never leak exception details
            return render_template(
                'dashboard.html',
                username=session['username'],
                role=session['role'],
                fetch_error='Request failed. Unable to reach the specified endpoint.'
            )
    else:
        # BLOCKED — log for SIEM daemon
        log_security_event('BLOCKED_SSRF', client_ip, f'Blocked URL: {target_url}')
        return render_template(
            'dashboard.html',
            username=session['username'],
            role=session['role'],
            fetch_error='[SECURITY ALERT] Internal IP addresses are strictly prohibited. This attempt has been logged and escalated to SOC.'
        )


# ═══════════════════════════════════════════════
# RECONNAISSANCE HINTS & INTENTIONAL LEAKS
# ═══════════════════════════════════════════════

@app.route('/robots.txt', methods=['GET'])
def robots_txt():
    """Serve robots.txt with intentional SSH port hint."""
    robots_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robots.txt')
    if os.path.exists(robots_path):
        with open(robots_path, 'r') as f:
            content = f.read()
        resp = make_response(content)
        resp.headers['Content-Type'] = 'text/plain'
        return resp
    return "User-agent: *\nDisallow: /staff_portal\n", 200, {'Content-Type': 'text/plain'}


@app.route('/backup/', methods=['GET'])
def backup_configs_index():
    """
    INTENTIONAL VULNERABILITY: Exposed backup directory.
    Lists files in backup_configs/ — simulates a misconfigured
    web server with directory listing enabled.
    The .env.bak file contains employee1 credentials.
    """
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup')
    if not os.path.isdir(backup_dir):
        abort(404)

    files = os.listdir(backup_dir)
    log_security_event('RECON_BACKUP', request.remote_addr, 'Directory listing accessed: /backup/')

    listing = '<html><head><title>Index of /backup/</title></head>'
    listing += '<body><h1>Index of /backup/</h1><hr><pre>'
    listing += '<a href="/">../</a>\n'
    for fname in sorted(files):
        fpath = os.path.join(backup_dir, fname)
        size = os.path.getsize(fpath) if os.path.isfile(fpath) else '-'
        listing += f'<a href="/backup/{fname}">{fname}</a>{"":>{40-len(fname)}} {size}\n'
    listing += '</pre><hr></body></html>'

    resp = make_response(listing)
    resp.headers['Content-Type'] = 'text/html'
    return resp


@app.route('/backup/<path:filename>', methods=['GET'])
def backup_configs_file(filename):
    """
    INTENTIONAL VULNERABILITY: Serves backup config files.
    The .env.bak contains leaked employee1 credentials + internal API info.
    """
    # Prevent directory traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        abort(403)

    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup')
    filepath = os.path.join(backup_dir, filename)

    if not os.path.isfile(filepath):
        abort(404)

    log_security_event('RECON_BACKUP', request.remote_addr, f'File accessed: /backup/{filename}')

    with open(filepath, 'r', errors='replace') as f:
        content = f.read()

    resp = make_response(content)
    resp.headers['Content-Type'] = 'text/plain'
    return resp


# ═══════════════════════════════════════════════
# ERROR HANDLERS — [FIX #11] No information leaks
# ═══════════════════════════════════════════════

ERROR_PAGE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{{ code }} — Vanguard Logistics</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-[#0a0e1a] text-slate-200 min-h-screen flex items-center justify-center font-sans">
<div class="text-center">
<div class="text-6xl font-bold text-cyan-400 mb-4">{{ code }}</div>
<h1 class="text-xl font-semibold text-white mb-2">{{ title }}</h1>
<p class="text-slate-500 mb-8">{{ message }}</p>
<a href="/" class="inline-flex items-center gap-2 px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-xl transition-all">
Return Home
<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
</a></div></body></html>"""


@app.errorhandler(400)
def bad_request(e):
    return make_response(
        ERROR_PAGE.replace('{{ code }}', '400')
        .replace('{{ title }}', 'Bad Request')
        .replace('{{ message }}', 'The request could not be processed.'),
        400
    )


@app.errorhandler(403)
def forbidden(e):
    return make_response(
        ERROR_PAGE.replace('{{ code }}', '403')
        .replace('{{ title }}', 'Access Denied')
        .replace('{{ message }}', 'You do not have permission to access this resource.'),
        403
    )


@app.errorhandler(404)
def not_found(e):
    # Log 404s for reconnaissance detection
    log_security_event('NOT_FOUND', request.remote_addr, f'Path: {request.path}')
    return make_response(
        ERROR_PAGE.replace('{{ code }}', '404')
        .replace('{{ title }}', 'Page Not Found')
        .replace('{{ message }}', 'The requested resource does not exist on this server.'),
        404
    )


@app.errorhandler(405)
def method_not_allowed(e):
    return make_response(
        ERROR_PAGE.replace('{{ code }}', '405')
        .replace('{{ title }}', 'Method Not Allowed')
        .replace('{{ message }}', 'The request method is not supported for this endpoint.'),
        405
    )


@app.errorhandler(413)
def payload_too_large(e):
    return make_response(
        ERROR_PAGE.replace('{{ code }}', '413')
        .replace('{{ title }}', 'Payload Too Large')
        .replace('{{ message }}', 'The submitted data exceeds the maximum allowed size.'),
        413
    )


@app.errorhandler(429)
def too_many_requests(e):
    return make_response(
        ERROR_PAGE.replace('{{ code }}', '429')
        .replace('{{ title }}', 'Too Many Requests')
        .replace('{{ message }}', 'Rate limit exceeded. Please wait before retrying.'),
        429
    )


@app.errorhandler(500)
def server_error(e):
    return make_response(
        ERROR_PAGE.replace('{{ code }}', '500')
        .replace('{{ title }}', 'Internal Error')
        .replace('{{ message }}', 'An unexpected error occurred. The incident has been logged.'),
        500
    )


# ═══════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    # CRITICAL: debug=False in production to prevent Werkzeug RCE
    app.run(
        host='0.0.0.0',
        port=80,
        debug=False
    )