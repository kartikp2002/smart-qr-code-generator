from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3, os, uuid
import qrcode
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "qr_project_secret"

DB = "database.db"
QR_FOLDER = "static/qrcodes"
os.makedirs(QR_FOLDER, exist_ok=True)

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS qrcodes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        data TEXT,
        filename TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect("/dashboard")

    return render_template("login.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name,email,password) VALUES (?,?,?)",
                (
                    request.form["name"],
                    request.form["email"],
                    generate_password_hash(request.form["password"])
                )
            )
            conn.commit()
            conn.close()
            return redirect("/")
        except:
            pass

    return render_template("register.html")

# ---------- DASHBOARD ----------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    qr_image = None

    if request.method == "POST":
        data = request.form["qrdata"]
        filename = f"{uuid.uuid4()}.png"
        path = os.path.join(QR_FOLDER, filename)

        qrcode.make(data).save(path)

        conn = get_db()
        conn.execute(
            "INSERT INTO qrcodes (user_id,data,filename) VALUES (?,?,?)",
            (session["user_id"], data, filename)
        )
        conn.commit()
        conn.close()

        qr_image = path

    conn = get_db()
    history = conn.execute(
        "SELECT * FROM qrcodes WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        name=session["name"],
        qr_image=qr_image,
        history=history
    )

# ---------- DOWNLOAD ----------
@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(QR_FOLDER, filename), as_attachment=True)

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
