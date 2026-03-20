from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "your_secret_key"

PER_PAGE = 10


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# LOGIN REQUIRED DECORATOR
# =========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# =========================
# USERS TABLE
# =========================
def create_users_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def create_default_user():
    conn = get_db_connection()
    cursor = conn.cursor()

    user = cursor.execute(
        "SELECT * FROM users WHERE username=?",
        ("admin",)
    ).fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", "admin123")
        )
        conn.commit()

    conn.close()


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# =========================
# DASHBOARD
# =========================
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")


# =========================
# CANDIDATES ADD / EDIT
# =========================
@app.route("/candidates_add", methods=["GET", "POST"])
@login_required
def candidates_add():

    conn = get_db_connection()

    edit_id = request.args.get("edit_id")
    candidate = None
    error = None
    duplicate_field = None

    if edit_id:
        candidate = conn.execute(
            "SELECT * FROM candidates WHERE id=?",
            (edit_id,)
        ).fetchone()

    if request.method == "POST":

        form_data = request.form

        name = form_data.get("name")
        email = form_data.get("email")
        phone = form_data.get("phone")

        skills = form_data.get("skills")
        experience = form_data.get("experience")

        linkedin = form_data.get("linkedin")
        other_url = form_data.get("other_url")

        job_title = form_data.get("job_title")
        location = form_data.get("location")

        visa_status = form_data.get("visa_status")
        availability = form_data.get("availability")
        availability_date = form_data.get("availability_date")
        relocate = form_data.get("relocate")

        dod = form_data.get("dod")
        clearance_level = form_data.get("clearance_level")

        payrate = form_data.get("payrate")
        paytype = form_data.get("paytype")
        employment = form_data.get("employment")

        source = form_data.get("source")
        recruiter = form_data.get("recruiter")

        notes = form_data.get("notes")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if edit_id:
            email_duplicate = conn.execute("""
            SELECT id FROM candidates
            WHERE email=? AND id!=?
            """, (email, edit_id)).fetchone()

            phone_duplicate = conn.execute("""
            SELECT id FROM candidates
            WHERE phone=? AND id!=?
            """, (phone, edit_id)).fetchone()
        else:
            email_duplicate = conn.execute("""
            SELECT id FROM candidates
            WHERE email=?
            """, (email,)).fetchone()

            phone_duplicate = conn.execute("""
            SELECT id FROM candidates
            WHERE phone=?
            """, (phone,)).fetchone()

        if email_duplicate:
            error = "Duplicate Email detected"
            duplicate_field = "email"
            conn.close()

            return render_template(
                "candidates_add.html",
                candidate=candidate,
                error=error,
                form_data=form_data,
                duplicate_field=duplicate_field
            )

        if phone_duplicate:
            error = "Duplicate Phone detected"
            duplicate_field = "phone"
            conn.close()

            return render_template(
                "candidates_add.html",
                candidate=candidate,
                error=error,
                form_data=form_data,
                duplicate_field=duplicate_field
            )

        if edit_id:
            conn.execute("""
            UPDATE candidates SET
            name=?,email=?,phone=?,skills=?,experience=?,
            linkedin=?,other_url=?,job_title=?,location=?,
            visa_status=?,availability=?,availability_date=?,relocate=?,
            dod=?,clearance_level=?,payrate=?,paytype=?,employment=?,
            source=?,recruiter=?,notes=?,updated_at=?
            WHERE id=?
            """,
            (name,email,phone,skills,experience,
             linkedin,other_url,job_title,location,
             visa_status,availability,availability_date,relocate,
             dod,clearance_level,payrate,paytype,employment,
             source,recruiter,notes,now,edit_id))

        else:
            conn.execute("""
            INSERT INTO candidates
            (name,email,phone,skills,experience,
            linkedin,other_url,job_title,location,
            visa_status,availability,availability_date,relocate,
            dod,clearance_level,payrate,paytype,employment,
            source,recruiter,notes,status,created_at,updated_at)

            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (name,email,phone,skills,experience,
             linkedin,other_url,job_title,location,
             visa_status,availability,availability_date,relocate,
             dod,clearance_level,payrate,paytype,employment,
             source,recruiter,notes,"New",now,now))

        conn.commit()
        conn.close()

        return redirect(url_for("candidates_view"))

    conn.close()

    return render_template(
        "candidates_add.html",
        candidate=candidate,
        error=error,
        form_data=None,
        duplicate_field=None
    )


# =========================
# CANDIDATES VIEW
# =========================
@app.route("/candidates_view")
@login_required
def candidates_view():

    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * PER_PAGE

    conn = get_db_connection()

    candidates = conn.execute("""
    SELECT * FROM candidates
    WHERE status!='deleted'
    ORDER BY id DESC
    LIMIT ? OFFSET ?
    """, (PER_PAGE, offset)).fetchall()

    total = conn.execute("""
    SELECT COUNT(*) FROM candidates
    WHERE status!='deleted'
    """).fetchone()[0]

    conn.close()

    pages = (total + PER_PAGE - 1) // PER_PAGE

    return render_template(
        "candidates_view.html",
        candidates=candidates,
        total=total,
        page=page,
        pages=pages
    )


# =========================
# DELETE
# =========================
@app.route("/candidates_delete/<int:id>")
@login_required
def candidates_delete(id):

    conn = get_db_connection()

    conn.execute("""
    UPDATE candidates
    SET status='deleted'
    WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("candidates_view"))


# =========================
# RUN APP
# =========================
import os

if __name__ == "__main__":
    create_users_table()
    create_default_user()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
