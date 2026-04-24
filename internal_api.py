"""
Vanguard Logistics — Internal API Server
==========================================
Runs on the Database VM (10.0.0.15:5000) inside the Secure Zone.
Serves admin credentials and flag location when accessed.

This API is only reachable via the SSRF vulnerability in app.py.
The Web Server (192.168.50.10) can reach this via the "Legacy API
Sync" firewall rule on port 5000.

DEPLOYMENT:
    - Run on Database VM only
    - Listen on port 5000, bind 0.0.0.0
    - debug=False (CRITICAL: no Werkzeug debugger)
"""

from flask import Flask, jsonify, request
import sqlite3
import os
import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max


@app.after_request
def hide_server_header(response):
    """Strip technology stack from response headers."""
    response.headers.pop('Server', None)
    response.headers['Server'] = 'Vanguard-Internal/2.1'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def get_db():
    """Get database connection."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vanguard.db')
    return sqlite3.connect(db_path)


def log_access(endpoint, ip):
    """Log all API access for audit trail."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_access.log')
    try:
        with open(log_path, 'a') as f:
            f.write(f"[{timestamp}] {endpoint} | IP: {ip}\n")
    except IOError:
        pass


@app.route('/', methods=['GET'])
def api_root():
    """API root — reveals available endpoints."""
    log_access('/', request.remote_addr)
    return jsonify({
        "service": "Vanguard Internal Secure API",
        "version": "2.1.4",
        "status": "operational",
        "classification": "INTERNAL USE ONLY",
        "endpoints": [
            "/api/admin_keys",
            "/api/health",
            "/api/manifest_info"
        ]
    })


@app.route('/api/admin_keys', methods=['GET'])
def get_admin_keys():
    """
    Serves the admin MD5 hash and flag file location.
    This is the critical endpoint the Red Team accesses via SSRF.
    """
    log_access('/api/admin_keys', request.remote_addr)
    print(f"[!] ALERT: /api/admin_keys accessed from {request.remote_addr}")

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username, password_hash, role FROM users WHERE username='admin'")
        admin_data = cursor.fetchone()
        conn.close()

        if admin_data:
            return jsonify({
                "status": "success",
                "system": "Vanguard Internal Secure Zone",
                "classification": "CONFIDENTIAL",
                "user": admin_data[0],
                "role": admin_data[2],
                "md5_hash": admin_data[1],
                "note": "Hash can be reversed via rainbow table or hashcat",
                "flag_location": "manifest.enc (Requires vault.key to decrypt)",
                "vault_key_path": "/opt/vanguard/data/vault.key"
            })
        else:
            return jsonify({"error": "Admin account not found"}), 404

    except Exception:
        return jsonify({"error": "Internal service error"}), 500


@app.route('/api/manifest_info', methods=['GET'])
def manifest_info():
    """Provides information about the encrypted manifest."""
    log_access('/api/manifest_info', request.remote_addr)
    return jsonify({
        "file": "manifest.enc",
        "encryption": "Fernet (AES-128-CBC + HMAC-SHA256)",
        "key_file": "vault.key",
        "contents": "Classified cargo manifest — CTF flag embedded",
        "decrypt_command": "python decrypt_flag.py",
        "note": "Key and encrypted file must be in the same directory"
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    log_access('/api/health', request.remote_addr)
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "user_count": count,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception:
        return jsonify({
            "status": "degraded",
            "error": "database connection failed"
        }), 500


if __name__ == '__main__':
    print("=" * 50)
    print("  Vanguard Internal API Server")
    print("  Listening on 0.0.0.0:5000")
    print("  CLASSIFICATION: INTERNAL ONLY")
    print("=" * 50)
    # CRITICAL: debug=False to prevent Werkzeug debugger RCE
    app.run(host='0.0.0.0', port=5000, debug=False)