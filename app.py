
import os
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)


app = Flask(
    __name__,
    template_folder="Templates"
)


# =========================================================
# CONFIGURATION
# =========================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)


SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

# Lire le fichier secret Render si les variables d'environnement sont absentes
secret_file = "/etc/secrets/supabase.env"
print("FICHIER SECRET EXISTE :", os.path.exists(secret_file))
if os.path.exists(secret_file):
    with open(secret_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or "=" not in line:
                continue

            key, value = [part.strip() for part in line.split("=", 1)]

            if key == "SUPABASE_URL" and not SUPABASE_URL:
                SUPABASE_URL = value.strip().rstrip("/")

            if key == "SUPABASE_SECRET_KEY" and not SUPABASE_SECRET_KEY:
                SUPABASE_SECRET_KEY = value.strip()

print("SUPABASE CONFIG :", bool(SUPABASE_URL), bool(SUPABASE_SECRET_KEY))


# =========================================================
# PRIX
# =========================================================

PRICES = {
    "1h": 30,
    "2h": 50
}


DEPOSITS = {
    "1h": 10,
    "2h": 20
}


# =========================================================
# CHEVAUX
# =========================================================

HORSES = [
    "Cheval 1",
    "Cheval 2",
    "Cheval 3"
]


# =========================================================
# HORAIRES
# =========================================================

SLOTS = [
    "09:00",
    "10:00",
    "14:00",
    "15:00"
]


# =========================================================
# MOT DE PASSE ADMIN
# =========================================================

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)


# =========================================================
# CONNEXION SUPABASE
# =========================================================

def supabase_request(
    method,
    table,
    params=None,
    data=None
):

    # Diagnostic précis :
    # on indique uniquement le nom de la variable manquante.
    # La valeur secrète n'est jamais affichée.

    missing = []

    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")

    if not SUPABASE_SECRET_KEY:
        missing.append("SUPABASE_SECRET_KEY")

    if missing:
        raise RuntimeError(
            "Variables Supabase manquantes : "
            + ", ".join(missing)
        )


    url = (
        f"{SUPABASE_URL}"
        f"/rest/v1/{table}"
    )


    if params:
        url += "?" + urlencode(params)


    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json"
    }


    if method == "POST":
        headers["Prefer"] = "return=representation"


    if method == "PATCH":
        headers["Prefer"] = "return=representation"


    body = None


    if data is not None:
        body = json.dumps(data).encode(
            "utf-8"
        )


    req = Request(
        url,
        data=body,
        headers=headers,
        method=method
    )


    try:

        with urlopen(
            req,
            timeout=15
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )


            if not raw:
                return []


            return json.loads(raw)


    except HTTPError as e:

        error_body = e.read().decode(
            "utf-8",
            errors="replace"
        )

        print(
            "Supabase HTTP error:",
            e.code,
            error_body
        )

        raise


    except URLError as e:

        print(
            "Supabase connection error:",
            e
        )

        raise


# =========================================================
# CHEVAUX DISPONIBLES
# =========================================================

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


    return [
        row["name"]
        for row in rows
    ]


# =========================================================
# NOMBRE DE CAVALIERS DEJA RESERVES
# =========================================================

def booked_count(
    date,
    time
):

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

        total += int(
            row.get(
                "riders",
                0
            )
        )


    return total


# =========================================================
# PAGE D'ACCUEIL
# =========================================================

@app.route("/")
def home():

    return render_template(
        "home.html",
        prices=PRICES,
        deposits=DEPOSITS,
        slots=SLOTS,
        max_riders=len(HORSES)
    )
@app.route("/pension-chevaux")
def pension_chevaux():
    return render_template("pension-chevaux.html")
@app.route("/elevage-quarter-horse")
def elevage_quarter_horse():
    return render_template("elevage-quarter-horse.html")

@app.route("/debourrage-travail-cheval")
def debourrage_travail_cheval():
    return render_template("debourrage-travail-cheval.html")
@app.route("/cadre-unique")
def cadre_unique():
    return render_template("Cadre-unique.html")
# =========================================================
# DISPONIBILITES
# =========================================================

@app.route("/availability")
def availability():

    date = request.args.get(
        "date",
        ""
    )


    if not date:

        return {
            "date": date,
            "slots": []
        }


    capacity = len(
        available_horses()
    )


    data = []


    for slot in SLOTS:

        used = booked_count(
            date,
            slot
        )


        data.append({
            "time": slot,
            "remaining": max(
                0,
                capacity - used
            )
        })


    return {
        "date": date,
        "slots": data
    }


# =========================================================
# RESERVATION
# =========================================================

@app.route(
    "/reserve",
    methods=["POST"]
)
def reserve():

    date = request.form.get(
        "date",
        ""
    ).strip()


    time = request.form.get(
        "time",
        ""
    ).strip()


    duration = request.form.get(
        "duration",
        ""
    ).strip()


    name = request.form.get(
        "name",
        ""
    ).strip()


    phone = request.form.get(
        "phone",
        ""
    ).strip()


    email = request.form.get(
        "email",
        ""
    ).strip()


    try:

        riders = int(
            request.form.get(
                "riders",
                "0"
            )
        )

    except ValueError:

        riders = 0


    # Vérification des champs

    if (
        duration not in PRICES
        or time not in SLOTS
        or not date
        or not name
        or not phone
        or not email
    ):

        flash(
            "Merci de remplir tous les champs."
        )

        return redirect(
            url_for("home")
        )


    # Maximum 3 cavaliers

    if (
        riders < 1
        or riders > len(HORSES)
    ):

        flash(
            "Le nombre de cavaliers "
            "doit être compris entre 1 et 3."
        )

        return redirect(
            url_for("home")
        )


    # Vérification des chevaux

    capacity = len(
        available_horses()
    )


    if riders > (
        capacity
        - booked_count(
            date,
            time
        )
    ):

        flash(
            "Ce créneau n'a plus assez "
            "de chevaux disponibles."
        )

        return redirect(
            url_for("home")
        )


    # Calcul du prix

    total = (
        PRICES[duration]
        * riders
    )


    deposit = (
        DEPOSITS[duration]
        * riders
    )


    # Création de la réservation

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
        # Notification Telegram
        try:
            import urllib.parse
            import urllib.request

            telegram_token = ""
            telegram_chat_id = ""

            with open("/etc/secrets/telegram.env", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key.strip() == "TELEGRAM_BOT_TOKEN":
                        telegram_token = value.strip()
                    elif key.strip() == "TELEGRAM_CHAT_ID":
                        telegram_chat_id = value.strip()

            if telegram_token and telegram_chat_id:
                message = (
                    "🔔 Nouvelle réservation – The Horse Farm\n\n"
                    f"Nom : {reservation.get('name', '')}\n"
                    f"Téléphone : {reservation.get('phone', '')}\n"
                    f"Date : {reservation.get('date', '')}\n"
                    f"Heure : {reservation.get('time', '')}\n"
                    f"Cavaliers : {reservation.get('riders', '')}\n"
                    f"Total : {reservation.get('total', '')} €\n"
                    f"Acompte : {reservation.get('deposit', '')} €"
                )

                data = urllib.parse.urlencode({
                    "chat_id": telegram_chat_id,
                    "text": message
                }).encode()

                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"

                urllib.request.urlopen(
                    urllib.request.Request(url, data=data),
                    timeout=10
                )

        except Exception as telegram_error:
            print("Erreur notification Telegram :", telegram_error)


    except Exception as e:

        print(
            "Erreur réservation:",
            e
        )

        flash(
            "Impossible d'enregistrer "
            "la réservation. "
            "Veuillez réessayer."
        )

        return redirect(
            url_for("home")
        )


    # Page de confirmation

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


# =========================================================
# CONNEXION ADMIN
# =========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        if (
            request.form.get(
                "password"
            )
            == ADMIN_PASSWORD
        ):

            session["admin"] = True

            return redirect(
                url_for("admin")
            )


        flash(
            "Mot de passe incorrect."
        )


    return render_template(
        "admin_login.html"
    )


# =========================================================
# DECONNEXION ADMIN
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin",
        None
    )


    return redirect(
        url_for("admin_login")
    )


# =========================================================
# ESPACE ADMIN
# =========================================================

@app.route("/admin")
def admin():

    if not session.get("admin"):

        return redirect(
            url_for("admin_login")
        )


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


# =========================================================
# CONFIRMER / ANNULER UNE RESERVATION
# =========================================================

@app.route(
    "/admin/reservation/<int:rid>/<action>",
    methods=["POST"]
)
def reservation_action(
    rid,
    action
):

    if not session.get("admin"):

        return redirect(
            url_for("admin_login")
        )


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


    return redirect(
        url_for("admin")
    )


# =========================================================
# ACTIVER / DESACTIVER UN CHEVAL
# =========================================================

@app.route(
    "/admin/horse/<name>/<action>",
    methods=["POST"]
)
def horse_action(
    name,
    action
):

    if (
        not session.get("admin")
        or name not in HORSES
    ):

        return redirect(
            url_for("admin_login")
        )


    available = (
        action == "enable"
    )


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


    return redirect(
        url_for("admin")
    )


# =========================================================
# LANCEMENT
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),

        debug=False
    )
