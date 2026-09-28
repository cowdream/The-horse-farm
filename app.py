import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__,template_folder="Templates")
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB = os.path.join(os.path.dirname(__file__), "reservations.db")

PRICES = {"1h": 30, "2h": 50}
DEPOSITS = {"1h": 10, "2h": 20}
HORSES = ["Cheval 1", "Cheval 2", "Cheval 3"]
SLOTS = ["09:00", "10:30", "14:00", "15:30", "17:30"]
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        duration TEXT NOT NULL,
        riders INTEGER NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT NOT NULL,
        total REAL NOT NULL,
        deposit REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS horses (
        name TEXT PRIMARY KEY,
        available INTEGER NOT NULL DEFAULT 1
    )""")
    for horse in HORSES:
        conn.execute("INSERT OR IGNORE INTO horses(name, available) VALUES(?,1)", (horse,))
    conn.commit()
    conn.close()

def available_horses():
    conn = db()
    rows = conn.execute("SELECT name FROM horses WHERE available=1 ORDER BY name").fetchall()
    conn.close()
    return [r["name"] for r in rows]

def booked_count(date, time):
    conn = db()
    row = conn.execute(
        "SELECT COALESCE(SUM(riders),0) AS n FROM reservations "
        "WHERE date=? AND time=? AND status IN ('pending','confirmed')",
        (date, time)
    ).fetchone()
    conn.close()
    return int(row["n"])

@app.route("/")
def home():
    return render_template(
        "home.html",
        prices=PRICES,
        deposits=DEPOSITS,
        slots=SLOTS,
        max_riders=len(HORSES)
    )

@app.route("/availability")
def availability():
    date = request.args.get("date", "")
    if not date:
        return {"date": date, "slots": []}
    capacity = len(available_horses())
    data=[]
    for slot in SLOTS:
        used=booked_count(date, slot)
        data.append({"time": slot, "remaining": max(0, capacity-used)})
    return {"date": date, "slots": data}

@app.route("/reserve", methods=["POST"])
def reserve():
    date=request.form.get("date","").strip()
    time=request.form.get("time","").strip()
    duration=request.form.get("duration","").strip()
    name=request.form.get("name","").strip()
    phone=request.form.get("phone","").strip()
    email=request.form.get("email","").strip()
    try:
        riders=int(request.form.get("riders","0"))
    except ValueError:
        riders=0

    if duration not in PRICES or time not in SLOTS or not date or not name or not phone or not email:
        flash("Merci de remplir tous les champs.")
        return redirect(url_for("home"))

    if riders < 1 or riders > len(HORSES):
        flash("Le nombre de cavaliers doit être compris entre 1 et 3.")
        return redirect(url_for("home"))

    capacity=len(available_horses())
    if riders > capacity - booked_count(date,time):
        flash("Ce créneau n'a plus assez de chevaux disponibles.")
        return redirect(url_for("home"))

    total=PRICES[duration]*riders
    deposit=DEPOSITS[duration]*riders

    conn=db()
    conn.execute(
        """INSERT INTO reservations
        (date,time,duration,riders,name,phone,email,total,deposit,status,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (date,time,duration,riders,name,phone,email,total,deposit,"pending",
         datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()
    conn.close()

    return render_template(
        "confirmation.html",
        date=date, time=time, duration=duration, riders=riders,
        name=name, total=total, deposit=deposit, balance=total-deposit
    )

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        if request.form.get("password")==ADMIN_PASSWORD:
            session["admin"]=True
            return redirect(url_for("admin"))
        flash("Mot de passe incorrect.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin",None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn=db()
    reservations=conn.execute("SELECT * FROM reservations ORDER BY date,time,id DESC").fetchall()
    horses=conn.execute("SELECT * FROM horses ORDER BY name").fetchall()
    conn.close()
    return render_template("admin.html", reservations=reservations, horses=horses)

@app.route("/admin/reservation/<int:rid>/<action>", methods=["POST"])
def reservation_action(rid, action):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    status = {"confirm":"confirmed", "cancel":"cancelled"}.get(action)
    if status:
        conn=db()
        conn.execute("UPDATE reservations SET status=? WHERE id=?", (status,rid))
        conn.commit()
        conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/horse/<name>/<action>", methods=["POST"])
def horse_action(name, action):
    if not session.get("admin") or name not in HORSES:
        return redirect(url_for("admin_login"))
    available = 1 if action=="enable" else 0
    conn=db()
    conn.execute("UPDATE horses SET available=? WHERE name=?", (available,name))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=False)

