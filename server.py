from flask import Flask, request, jsonify, send_from_directory
import mysql.connector
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# ======================
# DATABASE CONNECTION (SAFE)
# ======================
def get_db():
    try:
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME")
        )
    except Exception as e:
        print("DB ERROR:", e)
        return None


# ======================
# 🟢 ROOT CHECK (IMPORTANT)
# ======================
@app.route("/")
def home():
    return "Server is running"


# ======================
# 🔐 ACTIVATE LICENSE
# ======================
@app.route("/activate", methods=["POST"])
def activate():
    data = request.json
    key = data.get("license_key")
    device = data.get("device_id")

    db = get_db()
    if not db:
        return jsonify({"status": "server_error"})

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM licenses WHERE license_key=%s", (key,))
    license = cursor.fetchone()

    if not license:
        return jsonify({"status": "invalid"})

    if license["status"] == "blocked":
        return jsonify({"status": "blocked"})

    # First activation
    if not license["device_id"]:
        start = datetime.now()
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

    if license["device_id"] != device:
        return jsonify({"status": "blocked"})

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

    db = get_db()
    if not db:
        return jsonify({"status": "server_error"})

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
# 🔄 VERSION CHECK
# ======================
@app.route("/version", methods=["GET"])
def version():
    return jsonify({
        "version": "1.0.1",
        "url": ""
    })


# ======================
# 📦 DOWNLOAD UPDATE
# ======================
@app.route("/update.zip", methods=["GET"])
def download_update():
    return send_from_directory(
        directory=os.getcwd(),
        path="update.zip",
        as_attachment=True
    )
