import os

from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
import random
import string
from database import insert_data, get_user_by_email, create_user, link_family, get_child_id_by_family, get_user_by_id
from model_utils import predict_emotion
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "feelbuddy_secret_2024"

def generate_family_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    data = request.json
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "").strip()
    family_code = data.get("family_code", "").strip().upper()
    if not all([name, email, password, role]):
        return jsonify({"success": False, "message": "Saare fields bharo!"})
    if role == "child":
        family_code = generate_family_code()
    elif role in ["parent", "therapist"]:
        if not family_code:
            return jsonify({"success": False, "message": "Family code daalo!"})
        child_id = get_child_id_by_family(family_code)
        if not child_id:
            return jsonify({"success": False, "message": "Invalid family code!"})
    password_hash = generate_password_hash(password)
    user_id = create_user(name, email, password_hash, role, family_code)
    if not user_id:
        return jsonify({"success": False, "message": "Email already registered!"})
    link_family(family_code, user_id, role)
    return jsonify({"success": True, "message": "Registration successful!", "family_code": family_code, "role": role})

@app.route("/login", methods=["POST"])
def do_login():
    data = request.json
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    user = get_user_by_email(email)
    if not user:
        return jsonify({"success": False, "message": "Email nahi mila!"})
    if not check_password_hash(user[3], password):
        return jsonify({"success": False, "message": "Password galat hai!"})
    session["user_id"] = user[0]
    session["user_name"] = user[1]
    session["user_role"] = user[4]
    session["family_code"] = user[5]
    role = user[4]
    if role == "child":
        return jsonify({"success": True, "redirect": "/child"})
    elif role == "parent":
        return jsonify({"success": True, "redirect": "/dashboard"})
    elif role == "therapist":
        return jsonify({"success": True, "redirect": "/therapist"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

def check_auth(required_role=None):
    if "user_id" not in session:
        return False
    if required_role and session.get("user_role") != required_role:
        return False
    return True

@app.route("/child")
def child():
    if not check_auth("child"):
        return redirect("/")
    return render_template("index.html", user_name=session.get("user_name"))

@app.route("/parent")
def parent():
    return redirect("/dashboard")

@app.route("/aac")
def aac():
    if not check_auth("child"):
        return redirect("/")
    return render_template("aac.html")

@app.route("/schedule")
def schedule():
    if not check_auth("child"):
        return redirect("/")
    return render_template("schedule.html")

@app.route("/predict", methods=["POST"])
def predict():
    if not check_auth():
        return jsonify({"error": "Not logged in"})
    user_input = request.json["message"]
    prediction, reply = predict_emotion(user_input)
    user_id = session.get("user_id", 1)
    insert_data(user_input, prediction, user_id)
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM emotions WHERE user_id = ?", (user_id,))
    msg_count = cur.fetchone()[0]
    cur.execute("SELECT emotion FROM emotions WHERE user_id = ? ORDER BY id DESC LIMIT 3", (user_id,))
    last3 = [r[0] for r in cur.fetchall()]
    conn.close()
    redirect_to_calm = (len(last3) == 3 and all(x in ["sad", "anger", "fear"] for x in last3))
    reward = ""
    if msg_count % 5 == 0:
        reward = " ⭐ You earned a star!"
    return jsonify({"emotion": prediction, "reply": reply + reward, "redirect_calm": redirect_to_calm})

@app.route("/dashboard")
def dashboard():
    if not check_auth("parent"):
        return redirect("/")
    family_code = session.get("family_code")
    child_id = get_child_id_by_family(family_code)
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    if child_id:
        cur.execute("SELECT emotion, COUNT(*) FROM emotions WHERE user_id = ? GROUP BY emotion", (child_id,))
    else:
        cur.execute("SELECT emotion, COUNT(*) FROM emotions GROUP BY emotion")
    data = cur.fetchall()
    if child_id:
        cur.execute("SELECT COUNT(*) FROM emotions WHERE user_id = ?", (child_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM emotions")
    total = cur.fetchone()[0]
    conn.close()
    emotions = [r[0] for r in data]
    counts = [r[1] for r in data]
    if counts:
        common = emotions[counts.index(max(counts))]
    else:
        common = "neutral"
    insight = f"Child mostly feels {common}"
    return render_template("dashboard.html", total=total, common=common, insight=insight)

@app.route("/dashboard-data")
def dashboard_data():
    if not check_auth("parent"):
        return jsonify({})
    family_code = session.get("family_code")
    child_id = get_child_id_by_family(family_code)
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    if child_id:
        cur.execute("SELECT emotion, COUNT(*) FROM emotions WHERE user_id = ? GROUP BY emotion", (child_id,))
    else:
        cur.execute("SELECT emotion, COUNT(*) FROM emotions GROUP BY emotion")
    data = cur.fetchall()
    try:
        if child_id:
            cur.execute("SELECT DATE(timestamp), COUNT(*) FROM emotions WHERE user_id = ? GROUP BY DATE(timestamp) ORDER BY DATE(timestamp)", (child_id,))
        else:
            cur.execute("SELECT DATE(timestamp), COUNT(*) FROM emotions GROUP BY DATE(timestamp) ORDER BY DATE(timestamp)")
        daily = cur.fetchall()
    except:
        daily = []
    conn.close()
    return jsonify({"labels": [x[0] for x in data], "counts": [x[1] for x in data], "daily_labels": [x[0] for x in daily], "daily_counts": [x[1] for x in daily]})

@app.route("/alerts")
def alerts():
    if not check_auth("parent"):
        return jsonify({"alerts": []})
    family_code = session.get("family_code")
    child_id = get_child_id_by_family(family_code)
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    alerts_list = []
    cur.execute("SELECT DATE(timestamp) FROM emotions ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    today = row[0] if row else None
    if today and child_id:
        cur.execute("SELECT COUNT(*) FROM emotions WHERE emotion='fear' AND user_id=? AND DATE(timestamp)=?", (child_id, today))
        fear_count = cur.fetchone()[0]
        if fear_count >= 2:
            alerts_list.append(f"Anxiety detected {fear_count} times today — check in with child.")
        cur.execute("SELECT COUNT(*) FROM emotions WHERE emotion='anger' AND user_id=? AND DATE(timestamp)=?", (child_id, today))
        anger_count = cur.fetchone()[0]
        if anger_count >= 2:
            alerts_list.append(f"Anger detected {anger_count} times today — possible frustration trigger.")
        cur.execute("SELECT COUNT(*) FROM emotions WHERE emotion='sad' AND user_id=? AND DATE(timestamp)=?", (child_id, today))
        sad_count = cur.fetchone()[0]
        if sad_count >= 2:
            alerts_list.append(f"Sadness detected {sad_count} times today — child may need extra support.")
    conn.close()
    return jsonify({"alerts": alerts_list})

@app.route("/save-task", methods=["POST"])
def save_task():
    if not check_auth("child"):
        return jsonify({"ok": False})
    data = request.json
    task = data["task"]
    status = data["status"]
    user_id = session.get("user_id")
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS schedule_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        task TEXT, status TEXT,
        date DATE DEFAULT (DATE('now')))""")
    cur.execute("DELETE FROM schedule_tasks WHERE task=? AND user_id=? AND date=DATE('now')", (task, user_id))
    if status == "done":
        cur.execute("INSERT INTO schedule_tasks (task, status, user_id) VALUES (?, ?, ?)", (task, status, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/schedule-progress")
def schedule_progress():
    if not check_auth("parent"):
        return jsonify({"done": 0, "total": 9, "tasks": []})
    family_code = session.get("family_code")
    child_id = get_child_id_by_family(family_code)
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    try:
        if child_id:
            cur.execute("SELECT COUNT(*) FROM schedule_tasks WHERE status='done' AND user_id=? AND date=DATE('now')", (child_id,))
            done = cur.fetchone()[0]
            cur.execute("SELECT task FROM schedule_tasks WHERE status='done' AND user_id=? AND date=DATE('now')", (child_id,))
        else:
            done = 0
        tasks = [r[0] for r in cur.fetchall()]
    except:
        done = 0
        tasks = []
    conn.close()
    return jsonify({"done": done, "total": 9, "tasks": tasks})

@app.route("/calm")
def calm():
    return render_template("calm.html")

@app.route("/therapist")
def therapist():
    if not check_auth("therapist"):
        return redirect("/")
    family_code = session.get("family_code")
    child_id = get_child_id_by_family(family_code)
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    if child_id:
        cur.execute("SELECT COUNT(*) FROM emotions WHERE user_id = ?", (child_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM emotions")
    total = cur.fetchone()[0]
    if child_id:
        cur.execute("SELECT emotion, COUNT(*) FROM emotions WHERE user_id = ? GROUP BY emotion", (child_id,))
    else:
        cur.execute("SELECT emotion, COUNT(*) FROM emotions GROUP BY emotion")
    data = cur.fetchall()
    if data:
        common = max(data, key=lambda x: x[1])[0]
    else:
        common = "neutral"
    if common in ["sad", "fear", "anger"]:
        risk = "Moderate"
    else:
        risk = "Low"
    insight = "Mood stable."
    if child_id:
        cur.execute("SELECT emotion FROM emotions WHERE user_id = ? ORDER BY id DESC LIMIT 5", (child_id,))
    else:
        cur.execute("SELECT emotion FROM emotions ORDER BY id DESC LIMIT 5")
    recent = [r[0] for r in cur.fetchall()]
    if recent.count("fear") >= 3:
        insight = "Possible anxiety pattern detected."
    elif recent.count("sad") >= 3:
        insight = "Repeated sadness trend detected."
    elif recent.count("anger") >= 3:
        insight = "Possible trigger-based frustration pattern."
    conn.close()
    return render_template("therapist.html", total=total, common=common, risk=risk, insight=insight)

@app.route("/add-goal", methods=["POST"])
def add_goal():
    if not check_auth("therapist"):
        return jsonify({"ok": False})
    goal = request.json["goal"]
    family_code = session.get("family_code")
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_code TEXT, goal TEXT, done INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("INSERT INTO goals (goal, family_code) VALUES (?, ?)", (goal, family_code))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/get-goals")
def get_goals():
    family_code = session.get("family_code")
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, family_code TEXT, goal TEXT, done INTEGER DEFAULT 0, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("SELECT goal, done FROM goals WHERE family_code=? ORDER BY id DESC", (family_code,))
    data = cur.fetchall()
    conn.close()
    return jsonify({"goals": [{"goal": r[0], "done": r[1]} for r in data]})

@app.route("/add-note", methods=["POST"])
def add_note():
    if not check_auth("therapist"):
        return jsonify({"ok": False})
    note = request.json["note"]
    family_code = session.get("family_code")
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_code TEXT, note TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("INSERT INTO notes (note, family_code) VALUES (?, ?)", (note, family_code))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/get-notes")
def get_notes():
    family_code = session.get("family_code")
    conn = sqlite3.connect("emotions.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, family_code TEXT, note TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("SELECT note, timestamp FROM notes WHERE family_code=? ORDER BY id DESC LIMIT 10", (family_code,))
    data = cur.fetchall()
    conn.close()
    return jsonify({"notes": [{"note": r[0], "timestamp": r[1]} for r in data]})

if __name__ == "__main__":
    import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port, debug=False)