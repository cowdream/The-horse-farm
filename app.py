
import os
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__, template_folder="Templates")

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

PRICES = {
    "1h": 30,
    "2h": 50
}

DEPOSITS = {
    "1h": 10,
    "2h": 20
}

HORSES = [
    "Cheval 1",
    "Cheval 2",
    "Cheval 3"
]

SLOTS = [
    "09:00",
    "10:00",
    "14:00",
    "15:00",
]

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)


def supabase_request(method, table, params=None, data=None):
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError("Variables Supabase manquantes.")

    url = f"{SUPABASE_URL}/rest/v1/{table}"

    if params:
        url += "?" + urlencode(params)

    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": "application/json"
    }

    if method == "POST":
        headers["Prefer"] = "return=representation"

    if method == "PATCH":
        headers["Prefer"] = "return=representation"

    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = Request(
        url,
        data=body,
        headers=headers,
        method=method
    )

    try:
        with urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")

            if not raw:
                return []

            return json.loads(raw)

    except HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print("Supabase HTTP error:", e.code, error_body)
        raise

    except URLError as e:
        print("Supabase connection error:", e)
        raise


def available_horses():
    rows = supabase_request(
        "GET",
        "horses",
        {
            "select": "name",
            "available": "eq.true",
            "order": "name.asc"
        }
    )

    return [row["name"] for row in rows]


def booked_count(date, time):
    rows = supabase_request(
        "GET",
        "reservations",
        {
            "select": "riders",
            "date": f"eq.{date}",
            "time": f"eq.{time}",
            "status": "in.(pending,confirmed)"
        }
    )

    total = 0

    for row in rows:
        total += int(row.get("riders", 0))

    return total


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
        return {
            "date": date,
            "slots": []
        }

    capacity = len(available_horses())

    data = []

    for slot in SLOTS:
        used = booked_count(date, slot)

        data.append({
            "time": slot,
            "remaining": max(0, capacity - used)
        })

    return {
        "date": date,
        "slots": data
    }


@app.route("/reserve", methods=["POST"])
def reserve():
    date = request.form.get("date", "").strip()
    time = request.form.get("time", "").strip()
    duration = request.form.get("duration", "").strip()
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    try:
        riders = int(request.form.get("riders", "0"))
    except ValueError:
        riders = 0

    if (
        duration not in PRICES
        or time not in SLOTS
        or not date
        or not name
        or not phone
        or not email
    ):
        flash("Merci de remplir tous les champs.")
        return redirect(url_for("home"))

    if riders < 1 or riders > len(HORSES):
        flash(
            "Le nombre de cavaliers doit être compris entre 1 et 3."
        )
        return redirect(url_for("home"))

    capacity = len(available_horses())

    if riders > capacity - booked_count(date, time):
        flash(
            "Ce créneau n'a plus assez de chevaux disponibles."
        )
        return redirect(url_for("home"))

    total = PRICES[duration] * riders
    deposit = DEPOSITS[duration] * riders

    reservation = {
        "date": date,
        "time": time,
        "duration": duration,
        "riders": riders,
        "name": name,
        "phone": phone,
        "email": email,
        "total": total,
        "deposit": deposit,
        "status": "pending"
    }

    try:
        supabase_request(
            "POST",
            "reservations",
            data=reservation
        )

    except Exception:
        flash(
            "Impossible d'enregistrer la réservation. "
            "Veuillez réessayer."
        )
        return redirect(url_for("home"))

    return render_template(
        "confirmation.html",
        date=date,
        time=time,
        duration=duration,
        riders=riders,
        name=name,
        total=total,
        deposit=deposit,
        balance=total - deposit
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":

        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))

        flash("Mot de passe incorrect.")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    reservations = supabase_request(
        "GET",
        "reservations",
        {
            "select": "*",
            "order": "date.asc,time.asc,id.desc"
        }
    )

    horses = supabase_request(
        "GET",
        "horses",
        {
            "select": "*",
            "order": "name.asc"
        }
    )

    return render_template(
        "admin.html",
        reservations=reservations,
        horses=horses
    )


@app.route(
    "/admin/reservation/<int:rid>/<action>",
    methods=["POST"]
)
def reservation_action(rid, action):

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    status = {
        "confirm": "confirmed",
        "cancel": "cancelled"
    }.get(action)

    if status:
        supabase_request(
            "PATCH",
            "reservations",
            {
                "id": f"eq.{rid}"
            },
            {
                "status": status
            }
        )

    return redirect(url_for("admin"))


@app.route(
    "/admin/horse/<name>/<action>",
    methods=["POST"]
)
def horse_action(name, action):

    if not session.get("admin") or name not in HORSES:
        return redirect(url_for("admin_login"))

    available = action == "enable"

    supabase_request(
        "PATCH",
        "horses",
        {
            "name": f"eq.{name}"
        },
        {
            "available": available
        }
    )

    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
