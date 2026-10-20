import os
import datetime
import base64
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from database.database import get_db, init_db
from services.report_generator import (
    create_police_complaint_docx,
    create_electrical_complaint_docx,
    create_evidence_zip
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "transguard_enterprise_secure_key_2026")

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'captured_images')
VIDEO_FOLDER = os.path.join(app.root_path, 'static', 'captured_videos')
REPORTS_FOLDER = os.path.join(app.root_path, 'static', 'reports')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

init_db()

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT id, username, email, phone, location, role FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return user

# --- AUTHENTICATION & CORE ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        error = "Invalid credentials."
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        transformer_id = request.form.get('transformer_id', '').strip().upper()

        if not all([username, password, email, phone, location, transformer_id]):
            error = "All fields are required."
        else:
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (username, password, email, phone, location) VALUES (?, ?, ?, ?, ?)",
                    (username, hashed_pw, email, phone, location)
                )
                user_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO transformers (user_id, transformer_id, location) VALUES (?, ?, ?)",
                    (user_id, transformer_id, location)
                )
                conn.commit()
                conn.close()
                return redirect(url_for('login'))
            except Exception as e:
                conn.rollback()
                conn.close()
                error = "Registration failed. Username or Transformer ID may already exist."

    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    conn = get_db()
    transformer = conn.execute("SELECT * FROM transformers WHERE user_id = ?", (user['id'],)).fetchone()
    
    active_incident = conn.execute(
        "SELECT * FROM incidents WHERE user_id = ? AND status = 'ACTIVE' ORDER BY id DESC LIMIT 1",
        (user['id'],)
    ).fetchone()

    recent_images = []
    captured_count = 0
    if active_incident:
        recent_images = conn.execute(
            "SELECT * FROM captured_images WHERE incident_id = ? ORDER BY id DESC LIMIT 8",
            (active_incident['id'],)
        ).fetchall()
        captured_count = conn.execute(
            "SELECT COUNT(*) as count FROM captured_images WHERE incident_id = ?",
            (active_incident['id'],)
        ).fetchone()['count']
    else:
        last_inc = conn.execute(
            "SELECT id FROM incidents WHERE user_id = ? AND status != 'DELETED' ORDER BY id DESC LIMIT 1",
            (user['id'],)
        ).fetchone()
        if last_inc:
            recent_images = conn.execute(
                "SELECT * FROM captured_images WHERE incident_id = ? ORDER BY id DESC LIMIT 8",
                (last_inc['id'],)
            ).fetchall()
            captured_count = len(recent_images)

    alert_count = conn.execute(
        "SELECT COUNT(*) as count FROM alerts WHERE user_id = ? AND status = 'ACTIVE'",
        (user['id'],)
    ).fetchone()['count']

    conn.close()
    wokwi_url = os.getenv("WOKWI_PROJECT_URL", "https://wokwi.com")

    return render_template(
        'dashboard.html',
        user=user,
        transformer=transformer,
        active_incident=active_incident,
        recent_images=recent_images,
        captured_count=captured_count,
        alert_count=alert_count,
        wokwi_url=wokwi_url
    )

@app.route('/alerts')
def alerts():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    conn = get_db()
    alerts_list = conn.execute('''
        SELECT a.id as alert_id, a.status as alert_status, i.* 
        FROM alerts a
        JOIN incidents i ON a.incident_id = i.id
        WHERE a.user_id = ? AND a.status = 'ACTIVE'
        ORDER BY a.id DESC
    ''', (user['id'],)).fetchall()
    
    alert_details = []
    for alt in alerts_list:
        incident_id = alt['id']
        imgs = conn.execute("SELECT * FROM captured_images WHERE incident_id = ? ORDER BY id ASC", (incident_id,)).fetchall()
        video_row = conn.execute("SELECT file_path FROM captured_videos WHERE incident_id = ? ORDER BY id DESC LIMIT 1", (incident_id,)).fetchone()
        video_path = video_row['file_path'] if video_row else None
        alert_details.append({"alert": alt, "images": imgs, "video_path": video_path})

    alert_count = len(alerts_list)
    conn.close()
    wokwi_url = os.getenv("WOKWI_PROJECT_URL", "https://wokwi.com")
    return render_template('alerts.html', user=user, alert_details=alert_details, alert_count=alert_count, wokwi_url=wokwi_url)

@app.route('/history')
def history():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    conn = get_db()
    incidents = conn.execute("SELECT * FROM incidents WHERE user_id = ? ORDER BY id DESC", (user['id'],)).fetchall()
    history_details = []
    for inc in incidents:
        imgs = conn.execute("SELECT * FROM captured_images WHERE incident_id = ? ORDER BY id ASC", (inc['id'],)).fetchall()
        video_row = conn.execute("SELECT file_path FROM captured_videos WHERE incident_id = ? ORDER BY id DESC LIMIT 1", (inc['id'],)).fetchone()
        video_path = video_row['file_path'] if video_row else None
        history_details.append({"incident": inc, "images": imgs, "video_path": video_path})

    alert_count = conn.execute("SELECT COUNT(*) as count FROM alerts WHERE user_id = ? AND status = 'ACTIVE'", (user['id'],)).fetchone()['count']
    conn.close()
    wokwi_url = os.getenv("WOKWI_PROJECT_URL", "https://wokwi.com")
    return render_template('history.html', user=user, history_details=history_details, alert_count=alert_count, wokwi_url=wokwi_url)

@app.route('/report', methods=['GET', 'POST'])
def report_page():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    conn = get_db()
    incidents = conn.execute("SELECT * FROM incidents WHERE user_id = ? ORDER BY id DESC", (user['id'],)).fetchall()
    alert_count = conn.execute("SELECT COUNT(*) as count FROM alerts WHERE user_id = ? AND status = 'ACTIVE'", (user['id'],)).fetchone()['count']

    selected_incident = None
    captured_images = []
    video_path = None

    incident_id = request.args.get('incident_id')
    if incident_id:
        selected_incident = conn.execute("SELECT * FROM incidents WHERE id = ? AND user_id = ?", (incident_id, user['id'])).fetchone()
        if selected_incident:
            captured_images = conn.execute("SELECT * FROM captured_images WHERE incident_id = ? ORDER BY id ASC", (selected_incident['id'],)).fetchall()
            v_row = conn.execute("SELECT file_path FROM captured_videos WHERE incident_id = ?", (selected_incident['id'],)).fetchone()
            video_path = v_row['file_path'] if v_row else None

    conn.close()
    wokwi_url = os.getenv("WOKWI_PROJECT_URL", "https://wokwi.com")
    return render_template('report.html', user=user, incidents=incidents, selected=selected_incident, images=captured_images, video_path=video_path, alert_count=alert_count, wokwi_url=wokwi_url)

@app.route('/simulator')
def simulator_console():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    conn = get_db()
    alert_count = conn.execute("SELECT COUNT(*) as count FROM alerts WHERE user_id = ? AND status = 'ACTIVE'", (user['id'],)).fetchone()['count']
    conn.close()

    wokwi_url = os.getenv("WOKWI_PROJECT_URL", "https://wokwi.com")
    return render_template('simulator.html', user=user, alert_count=alert_count, wokwi_url=wokwi_url)

# --- REAL-TIME CAMERA, POLLING & CONTROL APIS ---
@app.route('/api/simulate_alert', methods=['POST'])
def simulate_alert():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.json or {}
    chosen_response = data.get("response", "PENDING")
    threat_level = "HIGH" if chosen_response == "YES" else ("LOW" if chosen_response == "NO" else "PENDING")
    timestamp = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")

    conn = get_db()
    transformer = conn.execute("SELECT * FROM transformers WHERE user_id = ?", (user['id'],)).fetchone()
    if not transformer:
        conn.close()
        return jsonify({"success": False, "message": "No transformer linked to user"}), 400

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO incidents (user_id, transformer_id, incident_type, detected_time, threat_level, owner_response, status, live_feed_status, evidence_status)
        VALUES (?, ?, 'Door Opened', ?, ?, ?, 'ACTIVE', 'ACTIVE', 'IN_PROGRESS')
    ''', (user['id'], transformer['transformer_id'], timestamp, threat_level, chosen_response))
    
    incident_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO alerts (user_id, incident_id, alert_type, status)
        VALUES (?, ?, 'UNAUTHORIZED DOOR OPEN', 'ACTIVE')
    ''', (user['id'], incident_id))

    cursor.execute("UPDATE transformers SET status = 'ALERT' WHERE id = ?", (transformer['id'],))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "incident_id": incident_id, "threat_level": threat_level, "detected_time": timestamp})

# --- HARDWARE & CIRKIT DESIGNER INTEGRATION API ---
@app.route('/api/trigger_alert', methods=['POST'])
def trigger_alert():
    data = request.json or {}
    transformer_id = data.get('transformer_id', 'TG-001')
    threat_level = data.get('threat_level', 'HIGH')
    incident_type = data.get('incident_type', 'MAGNETIC_DOOR_OPENED')
    timestamp = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")

    conn = get_db()
    transformer = conn.execute("SELECT * FROM transformers WHERE transformer_id = ?", (transformer_id,)).fetchone()
    
    if transformer:
        user_id = transformer['user_id']
    else:
        first_user = conn.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1").fetchone()
        user_id = first_user['id'] if first_user else 1

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO incidents (user_id, transformer_id, incident_type, detected_time, threat_level, owner_response, status, live_feed_status, evidence_status)
        VALUES (?, ?, ?, ?, ?, 'PENDING', 'ACTIVE', 'ACTIVE', 'IN_PROGRESS')
    ''', (user_id, transformer_id, incident_type, timestamp, threat_level))
    
    incident_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO alerts (user_id, incident_id, alert_type, status)
        VALUES (?, ?, ?, 'ACTIVE')
    ''', (user_id, incident_id, incident_type))

    cursor.execute("UPDATE transformers SET status = 'ALERT' WHERE transformer_id = ?", (transformer_id,))
    conn.commit()
    conn.close()

    logging.info(f"[HARDWARE/CIRKIT ALERT] Incident created! ID: {incident_id}")
    return jsonify({"success": True, "incident_id": incident_id}), 200

@app.route('/api/update_threat_level', methods=['POST'])
def update_threat_level():
    user = get_current_user()
    if not user:
        return jsonify({"success": False}), 401

    data = request.json or {}
    incident_id = data.get("incident_id")
    chosen_response = data.get("response", "YES")
    threat_level = "HIGH" if chosen_response == "YES" else "LOW"

    conn = get_db()
    conn.execute(
        "UPDATE incidents SET owner_response = ?, threat_level = ? WHERE id = ? AND user_id = ?",
        (chosen_response, threat_level, incident_id, user['id'])
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route('/api/poll')
def poll_dashboard():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False}), 401

    conn = get_db()
    active_incident = conn.execute('''
        SELECT * FROM incidents 
        WHERE user_id = ? AND status = 'ACTIVE' 
        ORDER BY id DESC LIMIT 1
    ''', (user['id'],)).fetchone()

    alert_count = conn.execute(
        "SELECT COUNT(*) as count FROM alerts WHERE user_id = ? AND status = 'ACTIVE'",
        (user['id'],)
    ).fetchone()['count']

    if active_incident:
        imgs = conn.execute(
            "SELECT * FROM captured_images WHERE incident_id = ? ORDER BY id DESC LIMIT 8",
            (active_incident['id'],)
        ).fetchall()
        
        captured_total = conn.execute(
            "SELECT COUNT(*) as count FROM captured_images WHERE incident_id = ?",
            (active_incident['id'],)
        ).fetchone()['count']

        img_list = [{"path": img['file_path'], "captured_at": img['captured_at']} for img in imgs]

        conn.close()
        return jsonify({
            "authenticated": True,
            "has_active": True,
            "alert_count": alert_count,
            "incident": {
                "id": active_incident['id'],
                "transformer_id": active_incident['transformer_id'],
                "detected_time": active_incident['detected_time'],
                "threat_level": active_incident['threat_level'],
                "owner_response": active_incident['owner_response']
            },
            "images": img_list,
            "captured_count": captured_total
        })

    conn.close()
    return jsonify({"authenticated": True, "has_active": False, "alert_count": alert_count, "captured_count": 0})

@app.route('/api/stop_alert', methods=['POST'])
def stop_alert():
    user = get_current_user()
    if not user:
        return jsonify({"success": False}), 401

    data = request.json or {}
    incident_id = data.get("incident_id")

    conn = get_db()
    if incident_id:
        conn.execute("UPDATE incidents SET status = 'COMPLETED' WHERE id = ? AND user_id = ?", (incident_id, user['id']))
    else:
        conn.execute("UPDATE incidents SET status = 'COMPLETED' WHERE user_id = ? AND status = 'ACTIVE'", (user['id'],))
    
    conn.execute("UPDATE transformers SET status = 'SAFE' WHERE user_id = ?", (user['id'],))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route('/api/upload_frame', methods=['POST'])
def upload_frame():
    user = get_current_user()
    if not user:
        return jsonify({"success": False}), 401

    data = request.json or {}
    incident_id = data.get("incident_id")
    image_data = data.get("image")

    if not incident_id or not image_data or len(image_data) < 100:
        return jsonify({"success": False, "message": "Invalid frame payload"}), 400

    try:
        header, encoded = image_data.split(",", 1)
        file_bytes = base64.b64decode(encoded)

        timestamp_str = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")
        filename_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        filename = f"TG-{incident_id}_{filename_str}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        with open(filepath, "wb") as f:
            f.write(file_bytes)

        rel_path = f"captured_images/{filename}"

        conn = get_db()
        conn.execute('''
            INSERT INTO captured_images (incident_id, file_path, captured_at)
            VALUES (?, ?, ?)
        ''', (incident_id, rel_path, timestamp_str))
        conn.commit()

        imgs_total = conn.execute(
            "SELECT COUNT(*) as count FROM captured_images WHERE incident_id = ?",
            (incident_id,)
        ).fetchone()['count']

        conn.close()

        return jsonify({"success": True, "path": rel_path, "captured_at": timestamp_str, "total_count": imgs_total})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/alert/delete', methods=['POST'])
def delete_alert():
    user = get_current_user()
    if not user:
        return jsonify({"success": False}), 401

    data = request.json or {}
    alert_id = data.get("alert_id")

    conn = get_db()
    alert = conn.execute("SELECT * FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user['id'])).fetchone()
    
    if alert:
        incident_id = alert['incident_id']
        
        # 1. Fetch images associated with this incident to remove physical disk files
        imgs = conn.execute("SELECT file_path FROM captured_images WHERE incident_id = ?", (incident_id,)).fetchall()
        for img in imgs:
            if img['file_path']:
                file_abs_path = os.path.join(app.root_path, 'static', img['file_path'])
                if os.path.exists(file_abs_path):
                    try:
                        os.remove(file_abs_path)
                    except Exception as e:
                        logging.error(f"Error removing image file: {e}")

        # 2. Update status in Database
        conn.execute("UPDATE alerts SET status = 'DELETED' WHERE id = ?", (alert_id,))
        conn.execute("UPDATE incidents SET status = 'DELETED' WHERE id = ?", (incident_id,))
        conn.execute("DELETE FROM captured_images WHERE incident_id = ?", (incident_id,))
        conn.commit()

    conn.close()
    return jsonify({"success": True})

@app.route('/api/history/delete_permanent', methods=['POST'])
def delete_history_permanent():
    user = get_current_user()
    if not user:
        return jsonify({"success": False}), 401

    data = request.json or {}
    incident_id = data.get("incident_id")

    conn = get_db()
    
    # 1. Fetch and remove image files physically from disk
    imgs = conn.execute("SELECT file_path FROM captured_images WHERE incident_id = ?", (incident_id,)).fetchall()
    for img in imgs:
        if img['file_path']:
            file_abs_path = os.path.join(app.root_path, 'static', img['file_path'])
            if os.path.exists(file_abs_path):
                try:
                    os.remove(file_abs_path)
                except Exception as e:
                    logging.error(f"Error removing image file: {e}")

    # 2. Fetch and remove video files physically from disk
    videos = conn.execute("SELECT file_path FROM captured_videos WHERE incident_id = ?", (incident_id,)).fetchall()
    for vid in videos:
        if vid['file_path']:
            vid_abs_path = os.path.join(app.root_path, 'static', vid['file_path'])
            if os.path.exists(vid_abs_path):
                try:
                    os.remove(vid_abs_path)
                except Exception as e:
                    logging.error(f"Error removing video file: {e}")

    # 3. Permanently delete database records
    conn.execute("DELETE FROM incidents WHERE id = ? AND user_id = ?", (incident_id, user['id']))
    conn.execute("DELETE FROM alerts WHERE incident_id = ? AND user_id = ?", (incident_id, user['id']))
    conn.execute("DELETE FROM captured_images WHERE incident_id = ?", (incident_id,))
    conn.execute("DELETE FROM captured_videos WHERE incident_id = ?", (incident_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# --- APIS FOR RECORDING & THREE REPORT TYPES ---
@app.route('/api/upload_video', methods=['POST'])
def upload_video():
    user = get_current_user()
    if not user or 'video' not in request.files:
        return jsonify({"success": False, "message": "Invalid request"}), 400

    file = request.files['video']
    incident_id = request.form.get('incident_id')

    if not incident_id or not file:
        return jsonify({"success": False, "message": "Missing incident ID or file"}), 400

    ext = "mp4" if "mp4" in file.filename.lower() else "webm"
    filename = f"TG-{incident_id}_recording.{ext}"
    filepath = os.path.join(VIDEO_FOLDER, filename)
    file.save(filepath)

    rel_path = f"captured_videos/{filename}"

    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS captured_videos (id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id INTEGER, file_path TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("INSERT INTO captured_videos (incident_id, file_path) VALUES (?, ?)", (incident_id, rel_path))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "video_path": rel_path})

@app.route('/api/generate_report', methods=['POST'])
def generate_report():
    user = get_current_user()
    if not user:
        return jsonify({"success": False}), 401

    data = request.json or {}
    incident_id = data.get("incident_id")
    report_type = data.get("report_type")

    conn = get_db()
    incident = conn.execute("SELECT * FROM incidents WHERE id = ? AND user_id = ?", (incident_id, user['id'])).fetchone()
    if not incident:
        conn.close()
        return jsonify({"success": False, "message": "Incident not found"}), 404

    imgs = conn.execute("SELECT * FROM captured_images WHERE incident_id = ?", (incident['id'],)).fetchall()
    v_row = conn.execute("SELECT file_path FROM captured_videos WHERE incident_id = ?", (incident['id'],)).fetchone()
    video_rel_path = v_row['file_path'] if v_row else None

    conn.close()

    report_facts = {
        "id": incident['id'],
        "owner_name": user['username'],
        "phone": user['phone'],
        "email": user['email'],
        "location": user['location'],
        "transformer_id": incident['transformer_id'],
        "detected_time": incident['detected_time'],
        "threat_level": incident['threat_level'],
        "discom_name": "APSPDCL",
        "capacity": "100 KVA",
        "estimated_value": "2,50,000",
        "images": imgs
    }

    if report_type == 'POLICE':
        filename = create_police_complaint_docx(report_facts, REPORTS_FOLDER)
    elif report_type == 'ELECTRICAL':
        filename = create_electrical_complaint_docx(report_facts, REPORTS_FOLDER)
    elif report_type in ['EVIDENCE_PDF', 'ZIP']:
        filename = create_evidence_zip(report_facts, REPORTS_FOLDER, app.static_folder, video_rel_path)
    else:
        return jsonify({"success": False, "message": "Invalid report type"}), 400

    return jsonify({"success": True, "download_url": f"/static/reports/{filename}"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)