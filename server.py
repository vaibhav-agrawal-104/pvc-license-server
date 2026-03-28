from flask import Flask, request, jsonify, send_from_directory
import mysql.connector
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# ======================
# DATABASE CONNECTION
# ======================
db = mysql.connector.connect(
    host=os.environ.get("DB_HOST"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    database=os.environ.get("DB_NAME")
)


# ======================
# 🔐 ACTIVATE LICENSE
# ======================
@app.route("/activate", methods=["POST"])
def activate():
    data = request.json
    key = data.get("license_key")
    device = data.get("device_id")

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM licenses WHERE license_key=%s", (key,))
    license = cursor.fetchone()

    if not license:
        return jsonify({"status": "invalid"})

    # ❌ blocked license
    if license["status"] == "blocked":
        return jsonify({"status": "blocked"})

    # 🟢 first activation
    if not license["device_id"]:
        start = datetime.now()

        # 🔥 use plan_days
        plan_days = license.get("plan_days") or 28
        expiry = start + timedelta(days=plan_days)

        cursor.execute("""
            UPDATE licenses 
            SET device_id=%s, start_date=%s, expiry_date=%s 
            WHERE license_key=%s
        """, (device, start, expiry, key))

        db.commit()

        return jsonify({
            "status": "activated",
            "expiry": str(expiry)
        })

    # ❌ different device
    if license["device_id"] != device:
        return jsonify({"status": "blocked"})

    # ❌ expired
    if license["expiry_date"] and datetime.now() > license["expiry_date"]:
        return jsonify({"status": "expired"})

    return jsonify({
        "status": "valid",
        "expiry": str(license["expiry_date"])
    })


# ======================
# 🔍 CHECK LICENSE
# ======================
@app.route("/check", methods=["POST"])
def check():
    data = request.json
    key = data.get("license_key")
    device = data.get("device_id")

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM licenses WHERE license_key=%s", (key,))
    license = cursor.fetchone()

    if not license:
        return jsonify({"status": "invalid"})

    if license["status"] == "blocked":
        return jsonify({"status": "blocked"})

    if license["device_id"] != device:
        return jsonify({"status": "blocked"})

    if license["expiry_date"] and datetime.now() > license["expiry_date"]:
        return jsonify({"status": "expired"})

    return jsonify({
        "status": "valid",
        "expiry": str(license["expiry_date"])
    })


# ======================
# 🔄 VERSION CHECK (AUTO UPDATE)
# ======================
@app.route("/version", methods=["GET"])
def version():
    try:
        with open("version.json") as f:
            return jsonify(json.load(f))
    except:
        return jsonify({
            "version": "1.0.0",
            "url": ""
        })


# ======================
# 📦 DOWNLOAD UPDATE FILE
# ======================
@app.route("/update.zip", methods=["GET"])
def download_update():
    return send_from_directory(
        directory=os.getcwd(),
        path="update.zip",
        as_attachment=True
    )


# ======================
# 🚀 RUN SERVER
# ======================
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
