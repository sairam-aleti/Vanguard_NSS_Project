from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/api/admin_keys', methods=['GET'])
def get_admin_keys():
    print("[!] INTERNAL API HIT: Serving Admin Credentials")
    try:
        conn = sqlite3.connect('vanguard.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username='admin'")
        admin_data = cursor.fetchone()
        conn.close()

        if admin_data:
            return jsonify({
                "status": "success",
                "system": "Vanguard Internal Secure Zone",
                "user": "admin",
                "md5_hash": admin_data[0],
                "flag_location": "manifest.enc (Requires vault.key)"
            })
        else:
            return jsonify({"error": "Admin not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Running on port 5000. In production, this sits behind Firewall 2.
    app.run(host='0.0.0.0', port=5000, debug=True)