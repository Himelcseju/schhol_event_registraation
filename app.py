"""
School Event Portal - Flask app.
User: / (dashboard, register). Admin: /admin (password-protected).
"""
import os
import re
import time
import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, flash, render_template, request, redirect, url_for, session
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename

from config import (
    DB_CONFIG,
    SCHOOL_NAME,
    ADMIN_PASSWORD,
    DEFAULT_BATCH_NAME,
    SITE_FEE,
    SECRET_KEY,
    DEBUG,
)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if not DEBUG:
    app.config["SESSION_COOKIE_SECURE"] = True  # HTTPS only in production

# Photo uploads: stored under static/uploads/, path saved in DB
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_registration_photo(file, roll_no, event_id):
    """
    Save uploaded photo with unique name: roll_no_eventid_timestamp.ext.
    Returns path relative to static/ (e.g. uploads/2022015_1_1734567890.jpg) or None.
    """
    if not file or not file.filename or not allowed_file(file.filename):
        return None
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_PHOTO_SIZE:
        return None
    safe_roll = re.sub(r"[^\w\-]", "_", str(roll_no))[:50]
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{safe_roll}_{event_id}_{int(time.time())}.{ext}"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    return f"uploads/{filename}"


def save_student_photo(file, roll_no):
    """
    Save uploaded photo for student profile. Unique name: roll_no_timestamp.ext.
    Returns path relative to static/ (e.g. uploads/2022015_1734567890.jpg) or None.
    """
    if not file or not file.filename or not allowed_file(file.filename):
        return None
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_PHOTO_SIZE:
        return None
    safe_roll = re.sub(r"[^\w\-]", "_", str(roll_no))[:50]
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{safe_roll}_{int(time.time())}.{ext}"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    return f"uploads/{filename}"


def get_db():
    """Return a DB connection with DictCursor."""
    return pymysql.connect(**DB_CONFIG, cursorclass=DictCursor)


def get_active_event():
    """Return the single active event or None."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, event_name, description, event_date, base_fee FROM events WHERE is_active = 1 LIMIT 1"
            )
            return cur.fetchone()
    finally:
        conn.close()


def ensure_default_batch():
    """Ensure default batch (e.g. 2008) exists in DB; return its id."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM batches WHERE batch_name = %s LIMIT 1", (DEFAULT_BATCH_NAME,))
            row = cur.fetchone()
            if row:
                return row["id"]
            cur.execute(
                "INSERT INTO batches (batch_name, created_at) VALUES (%s, %s)",
                (DEFAULT_BATCH_NAME, datetime.now()),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def get_batches():
    """Return all batches for dropdown. Ensures default batch exists."""
    ensure_default_batch()
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, batch_name FROM batches ORDER BY batch_name")
            return cur.fetchall()
    finally:
        conn.close()


def get_student_by_student_id(student_id):
    """Get student by student_id (roll/admission no)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, student_id, full_name, email, phone, batch_id FROM students WHERE student_id = %s",
                (student_id.strip(),),
            )
            return cur.fetchone()
    finally:
        conn.close()


def get_student_by_id(sid):
    """Get student by primary key id."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT s.id, s.student_id, s.full_name, s.nickname, s.email, s.phone, s.baria_address, "
                "s.current_address, s.profession, s.organization_name, s.blood_group, s.photo, s.batch_id, b.batch_name "
                "FROM students s LEFT JOIN batches b ON s.batch_id = b.id WHERE s.id = %s",
                (sid,),
            )
            return cur.fetchone()
    finally:
        conn.close()


# ---------- Admin helpers ----------


def get_all_events():
    """All events for admin (newest first)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, event_name, description, event_date, base_fee, is_active, created_at "
                "FROM events ORDER BY event_date DESC, id DESC"
            )
            return cur.fetchall()
    finally:
        conn.close()


def get_event_by_id(eid):
    """Single event by id."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, event_name, description, event_date, base_fee, is_active FROM events WHERE id = %s",
                (eid,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def get_all_students():
    """All students with batch name for admin list."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT s.id, s.student_id, s.full_name, s.email, s.phone, s.batch_id, b.batch_name, s.created_at "
                "FROM students s LEFT JOIN batches b ON s.batch_id = b.id ORDER BY s.created_at DESC"
            )
            return cur.fetchall()
    finally:
        conn.close()


def get_confirmed_members(event_id):
    """Registrations for event with status CONFIRMED or PAID (admin use)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT r.id, r.status, r.created_at, s.student_id AS roll_no, s.full_name, b.batch_name "
                "FROM event_registrations r "
                "JOIN students s ON r.student_id = s.id "
                "LEFT JOIN batches b ON s.batch_id = b.id "
                "WHERE r.event_id = %s AND r.status IN ('CONFIRMED', 'PAID') ORDER BY r.created_at ASC",
                (event_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def get_event_registrations_list(event_id):
    """All registrations from event_registrations for this event (for public list and count)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT r.id, r.status, r.created_at, s.full_name, s.phone, s.student_id AS roll_no, s.photo AS student_photo "
                    "FROM event_registrations r "
                    "JOIN students s ON r.student_id = s.id "
                    "WHERE r.event_id = %s ORDER BY r.created_at ASC",
                    (event_id,),
                )
            except pymysql.OperationalError:
                cur.execute(
                    "SELECT r.id, r.status, r.created_at, s.full_name, s.phone, s.student_id AS roll_no "
                    "FROM event_registrations r "
                    "JOIN students s ON r.student_id = s.id "
                    "WHERE r.event_id = %s ORDER BY r.created_at ASC",
                    (event_id,),
                )
            return cur.fetchall()
    finally:
        conn.close()


def get_registration_by_student_and_event(student_id, event_id):
    """Return existing registration row if this student already registered for this event, else None."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, student_id, event_id, total_amount, txn_no, status FROM event_registrations "
                "WHERE student_id = %s AND event_id = %s LIMIT 1",
                (student_id, event_id),
            )
            return cur.fetchone()
    finally:
        conn.close()


def get_registrations(event_id=None):
    """Registrations; if event_id given, filter by event."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                if event_id:
                    cur.execute(
                        "SELECT r.id, r.student_id, r.event_id, r.base_amount, r.extra_amount, r.total_amount, r.txn_no, r.bkash_to, r.status, r.created_at, "
                        "s.student_id AS roll_no, s.full_name, e.event_name "
                        "FROM event_registrations r "
                        "JOIN students s ON r.student_id = s.id JOIN events e ON r.event_id = e.id "
                        "WHERE r.event_id = %s ORDER BY r.created_at DESC",
                        (event_id,),
                    )
                else:
                    cur.execute(
                        "SELECT r.id, r.student_id, r.event_id, r.total_amount, r.txn_no, r.bkash_to, r.status, r.created_at, "
                        "s.student_id AS roll_no, s.full_name, e.event_name "
                        "FROM event_registrations r "
                        "JOIN students s ON r.student_id = s.id JOIN events e ON r.event_id = e.id "
                        "ORDER BY r.created_at DESC LIMIT 200"
                    )
            except pymysql.OperationalError as oe:
                if oe.args[0] == 1054 or "bkash_to" in str(oe).lower():
                    if event_id:
                        cur.execute(
                            "SELECT r.id, r.student_id, r.event_id, r.base_amount, r.extra_amount, r.total_amount, r.txn_no, r.status, r.created_at, "
                            "s.student_id AS roll_no, s.full_name, e.event_name "
                            "FROM event_registrations r "
                            "JOIN students s ON r.student_id = s.id JOIN events e ON r.event_id = e.id "
                            "WHERE r.event_id = %s ORDER BY r.created_at DESC",
                            (event_id,),
                        )
                    else:
                        cur.execute(
                            "SELECT r.id, r.student_id, r.event_id, r.total_amount, r.txn_no, r.status, r.created_at, "
                            "s.student_id AS roll_no, s.full_name, e.event_name "
                            "FROM event_registrations r "
                            "JOIN students s ON r.student_id = s.id JOIN events e ON r.event_id = e.id "
                            "ORDER BY r.created_at DESC LIMIT 200"
                        )
                else:
                    raise
            return cur.fetchall()
    finally:
        conn.close()


def admin_required(f):
    """Require admin session; redirect to admin login if not logged in."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.url))
        return f(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_active_event():
    """Make active event available in all templates (e.g. for countdown in header)."""
    try:
        event = get_active_event()
        return {"active_event": event}
    except Exception:
        return {"active_event": None}


# ---------- User routes ----------


@app.route("/")
def dashboard():
    """Screen 1: Dashboard - show current active event and Register button."""
    event = get_active_event()
    members_count = len(get_event_registrations_list(event["id"])) if event else 0
    return render_template(
        "dashboard.html",
        school_name=SCHOOL_NAME,
        event=event,
        members_count=members_count,
    )


@app.route("/register", methods=["GET", "POST"])
def register_start():
    """
    Profile check: GET = show 'Enter Roll No'; POST = check profile exists.
    If no profile → redirect to Create Profile; if yes → set session and go to Event Registration.
    """
    event = get_active_event()
    if not event:
        return redirect(url_for("dashboard"))

    if request.method == "GET":
        return render_template(
            "register_start.html",
            school_name=SCHOOL_NAME,
            event=event,
        )

    student_id = (request.form.get("student_id") or "").strip()
    if not student_id:
        return render_template(
            "register_start.html",
            school_name=SCHOOL_NAME,
            event=event,
            error="Please enter your SSC roll no.",
        )
    if not student_id.isdigit():
        return render_template(
            "register_start.html",
            school_name=SCHOOL_NAME,
            event=event,
            error="Roll no must contain only numbers.",
        )

    student = get_student_by_student_id(student_id)
    if not student:
        return redirect(url_for("create_profile", student_id=student_id))
    session["student_id"] = student["id"]
    return redirect(url_for("event_register", event_id=event["id"]))


@app.route("/profile/create", methods=["GET", "POST"])
def create_profile():
    """Screen 3: Create Student Profile (one-time). After save → redirect to Event Registration."""
    try:
        event = get_active_event()
    except Exception as e:
        return _profile_error("Database connection failed. Is MySQL running? Check config.py (host, user, password, database).", str(e))

    if not event:
        return redirect(url_for("dashboard"))

    if request.method == "GET":
        prefilled_id = request.args.get("student_id", "")
        try:
            batches = get_batches()
            default_batch_id = ensure_default_batch()
        except Exception as e:
            return _profile_error("Could not load batches.", str(e))
        return render_template(
            "create_profile.html",
            school_name=SCHOOL_NAME,
            batches=batches,
            student_id_prefill=prefilled_id,
            default_batch_id=default_batch_id,
        )

    student_id = (request.form.get("student_id") or "").strip()
    full_name = (request.form.get("full_name") or "").strip()
    nickname = (request.form.get("nickname") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    baria_address = (request.form.get("baria_address") or "").strip()
    current_address = (request.form.get("current_address") or "").strip()
    profession = (request.form.get("profession") or "").strip()
    organization_name = (request.form.get("organization_name") or "").strip()
    blood_group = (request.form.get("blood_group") or "").strip()
    batch_id = request.form.get("batch_id")

    def _form_data():
        """Return dict of submitted form values so we can re-show them on validation error."""
        return {
            "student_id": student_id,
            "full_name": full_name,
            "nickname": nickname,
            "email": email,
            "phone": phone,
            "baria_address": baria_address,
            "current_address": current_address,
            "profession": profession,
            "organization_name": organization_name,
            "blood_group": blood_group,
            "batch_id": batch_id,
        }

    required_ok = (
        student_id and full_name and email and phone
        and baria_address and current_address and blood_group and batch_id
    )
    if not required_ok:
        try:
            batches = get_batches()
            default_batch_id = ensure_default_batch()
        except Exception:
            batches = []
            default_batch_id = None
        return render_template(
            "create_profile.html",
            school_name=SCHOOL_NAME,
            batches=batches,
            student_id_prefill=student_id,
            default_batch_id=default_batch_id,
            form_data=_form_data(),
            error="All required fields must be filled.",
        )

    if not student_id.isdigit():
        try:
            batches = get_batches()
            default_batch_id = ensure_default_batch()
        except Exception:
            batches = []
            default_batch_id = None
        return render_template(
            "create_profile.html",
            school_name=SCHOOL_NAME,
            batches=batches,
            student_id_prefill=student_id,
            default_batch_id=default_batch_id,
            form_data=_form_data(),
            error="Roll no must contain only numbers.",
        )

    phone_digits = "".join(c for c in phone if c.isdigit())
    if len(phone_digits) != 11:
        try:
            batches = get_batches()
            default_batch_id = ensure_default_batch()
        except Exception:
            batches = []
            default_batch_id = None
        return render_template(
            "create_profile.html",
            school_name=SCHOOL_NAME,
            batches=batches,
            student_id_prefill=student_id,
            default_batch_id=default_batch_id,
            form_data=_form_data(),
            error="Mobile number must be exactly 11 digits.",
        )
    phone = phone_digits  # save cleaned 11 digits to DB

    try:
        batch_id = int(batch_id) if batch_id else None
    except (TypeError, ValueError):
        batch_id = None

    try:
        # Check first: only show "already registered" if this student_id exists in DB
        existing = get_student_by_student_id(student_id)
    except Exception as e:
        return _profile_error("Database error while checking student.", str(e))

    if existing:
        try:
            batches = get_batches()
            default_batch_id = ensure_default_batch()
        except Exception:
            batches = []
            default_batch_id = None
        return render_template(
            "create_profile.html",
            school_name=SCHOOL_NAME,
            batches=batches,
            student_id_prefill=student_id,
            default_batch_id=default_batch_id,
            form_data=_form_data(),
            error="This Student ID / Roll No is already registered.",
        )

    photo_path = None
    if "photo" in request.files:
        f = request.files["photo"]
        if f and f.filename:
            photo_path = save_student_photo(f, student_id)

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO students (student_id, full_name, nickname, email, phone, baria_address, "
                    "current_address, profession, organization_name, blood_group, photo, batch_id, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (student_id, full_name, nickname or None, email or None, phone or None,
                     baria_address or None, current_address or None, profession or None,
                     organization_name or None, blood_group or None, photo_path, batch_id, datetime.now()),
                )
            except pymysql.OperationalError as oe:
                if oe.args[0] == 1054 or "photo" in str(oe).lower():
                    cur.execute(
                        "INSERT INTO students (student_id, full_name, nickname, email, phone, baria_address, "
                        "current_address, profession, organization_name, blood_group, batch_id, created_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (student_id, full_name, nickname or None, email or None, phone or None,
                         baria_address or None, current_address or None, profession or None,
                         organization_name or None, blood_group or None, batch_id, datetime.now()),
                    )
                else:
                    raise
            new_id = cur.lastrowid
        conn.commit()
    except Exception as e:
        try:
            batches = get_batches()
        except Exception:
            batches = []
        try:
            default_batch_id = ensure_default_batch()
        except Exception:
            default_batch_id = None
        return _profile_error("Could not save profile. Check that MySQL is running and the 'school_event' database and 'students' table exist.", str(e), batches=batches, student_id_prefill=student_id, default_batch_id=default_batch_id)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    session["student_id"] = new_id
    return redirect(url_for("event_register", event_id=event["id"]))


def _profile_error(message, detail="", batches=None, student_id_prefill="", default_batch_id=None):
    """Show create-profile page with an error (e.g. DB down)."""
    if batches is None:
        try:
            batches = get_batches()
        except Exception:
            batches = []
    if default_batch_id is None:
        try:
            default_batch_id = ensure_default_batch()
        except Exception:
            pass
    return render_template(
        "create_profile.html",
        school_name=SCHOOL_NAME,
        batches=batches,
        student_id_prefill=student_id_prefill,
        default_batch_id=default_batch_id,
        error=message + " (" + detail + ")" if detail else message,
    )


@app.route("/event/<int:event_id>/register", methods=["GET", "POST"])
def event_register(event_id):
    """Screen 4: Event Registration - student details read-only, base + optional extra, total, confirm."""
    if "student_id" not in session:
        return redirect(url_for("dashboard"))

    event = get_active_event()
    if not event or event["id"] != event_id:
        return redirect(url_for("dashboard"))

    student = get_student_by_id(session["student_id"])
    if not student:
        session.pop("student_id", None)
        return redirect(url_for("dashboard"))

    existing_reg = get_registration_by_student_and_event(student["id"], event_id)
    if existing_reg:
        flash("You are already registered with this roll or number.", "info")
        return redirect(url_for("dashboard"))

    if request.method == "GET":
        return render_template(
            "event_register.html",
            school_name=SCHOOL_NAME,
            event=event,
            student=student,
            site_fee=SITE_FEE,
        )

    base_amount = event["base_fee"] or 0
    site_fee = SITE_FEE
    try:
        extra_amount = int(request.form.get("extra_amount") or 0)
    except (TypeError, ValueError):
        extra_amount = 0
    extra_amount = max(0, extra_amount)
    total_amount = base_amount + extra_amount + site_fee
    txn_no = (request.form.get("txn_no") or "").strip()

    if not txn_no:
        student = get_student_by_id(session["student_id"])
        return render_template(
            "event_register.html",
            school_name=SCHOOL_NAME,
            event=event,
            student=student,
            site_fee=SITE_FEE,
            error="TXN ID is required. Please enter your bKash transaction ID.",
        )

    txn_no = txn_no or None
    bkash_to = (request.form.get("bkash_to") or "").strip().lower()
    if bkash_to not in ("faisal", "guddu"):
        bkash_to = None

    conn = get_db()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO event_registrations "
                    "(student_id, event_id, base_amount, extra_amount, site_fee, total_amount, txn_no, bkash_to, photo, status, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'REGISTERED', %s)",
                    (student["id"], event_id, base_amount, extra_amount, site_fee, total_amount, txn_no, bkash_to, None, datetime.now()),
                )
            except pymysql.OperationalError as oe:
                err = str(oe).lower()
                if oe.args[0] != 1054 and "unknown column" not in err:
                    raise
                # Try with bkash_to but without photo (in case only photo column is missing)
                try:
                    cur.execute(
                        "INSERT INTO event_registrations "
                        "(student_id, event_id, base_amount, extra_amount, site_fee, total_amount, txn_no, bkash_to, status, created_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'REGISTERED', %s)",
                        (student["id"], event_id, base_amount, extra_amount, site_fee, total_amount, txn_no, bkash_to, datetime.now()),
                    )
                except pymysql.OperationalError as oe2:
                    if oe2.args[0] != 1054 and "unknown column" not in str(oe2).lower():
                        raise
                    # Minimal insert if bkash_to column also missing
                    cur.execute(
                        "INSERT INTO event_registrations "
                        "(student_id, event_id, base_amount, extra_amount, site_fee, total_amount, txn_no, status, created_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'REGISTERED', %s)",
                        (student["id"], event_id, base_amount, extra_amount, site_fee, total_amount, txn_no, datetime.now()),
                    )
        conn.commit()
    finally:
        conn.close()

    return redirect(
        url_for(
            "success",
            event_name=event["event_name"],
            total_amount=total_amount,
        )
    )


@app.route("/event/<int:event_id>/members")
def event_members(event_id):
    """Public list of all registered members from event_registrations for this event."""
    event = get_active_event()
    if not event or event["id"] != event_id:
        return redirect(url_for("dashboard"))
    members = get_event_registrations_list(event_id)
    return render_template(
        "event_members.html",
        school_name=SCHOOL_NAME,
        event=event,
        members=members,
        total_count=len(members),
    )


@app.route("/success")
def success():
    """Screen 5: Success page."""
    event_name = request.args.get("event_name", "Event")
    total_amount = request.args.get("total_amount", "0")
    return render_template(
        "success.html",
        school_name=SCHOOL_NAME,
        event_name=event_name,
        total_amount=total_amount,
    )


# ---------- Admin routes (password-protected) ----------


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Simple password check for admin; store in session."""
    if request.method == "GET":
        if session.get("admin_logged_in"):
            return redirect(url_for("admin_dashboard"))
        return render_template("admin/login.html", school_name=SCHOOL_NAME)

    password = (request.form.get("password") or "").strip()
    if password != ADMIN_PASSWORD:
        return render_template(
            "admin/login.html",
            school_name=SCHOOL_NAME,
            error="Incorrect password.",
        )
    session["admin_logged_in"] = True
    next_url = request.args.get("next") or url_for("admin_dashboard")
    return redirect(next_url)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    """Admin home: create event, view registrations, students."""
    events = get_all_events()
    registrations = get_registrations()[:50]
    return render_template(
        "admin/dashboard.html",
        school_name=SCHOOL_NAME,
        events=events,
        registrations=registrations,
    )


@app.route("/admin/create-event", methods=["GET", "POST"])
@admin_required
def admin_create_event():
    """Form to add new event."""
    if request.method == "GET":
        return render_template("admin/create_event.html", school_name=SCHOOL_NAME)

    event_name = (request.form.get("event_name") or "").strip()
    description = (request.form.get("description") or "").strip()
    event_date = request.form.get("event_date")
    base_fee = request.form.get("base_fee")
    is_active = request.form.get("is_active") == "1"

    if not event_name:
        return render_template(
            "admin/create_event.html",
            school_name=SCHOOL_NAME,
            error="Event name is required.",
        )

    try:
        base_fee = int(base_fee) if base_fee else 0
    except (TypeError, ValueError):
        base_fee = 0

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO events (event_name, description, event_date, base_fee, is_active, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (event_name, description or None, event_date or None, base_fee, is_active, datetime.now()),
            )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/students")
@admin_required
def admin_students():
    """View all student profiles."""
    students = get_all_students()
    return render_template(
        "admin/students.html",
        school_name=SCHOOL_NAME,
        students=students,
    )


@app.route("/admin/students/<int:student_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_student_edit(student_id):
    """Edit one student profile."""
    student = get_student_by_id(student_id)
    if not student:
        return redirect(url_for("admin_students"))

    if request.method == "GET":
        batches = get_batches()
        return render_template(
            "admin/student_edit.html",
            school_name=SCHOOL_NAME,
            student=student,
            batches=batches,
        )

    full_name = (request.form.get("full_name") or "").strip()
    nickname = (request.form.get("nickname") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    baria_address = (request.form.get("baria_address") or "").strip()
    current_address = (request.form.get("current_address") or "").strip()
    profession = (request.form.get("profession") or "").strip()
    organization_name = (request.form.get("organization_name") or "").strip()
    blood_group = (request.form.get("blood_group") or "").strip()
    batch_id = request.form.get("batch_id")

    if not full_name:
        batches = get_batches()
        return render_template(
            "admin/student_edit.html",
            school_name=SCHOOL_NAME,
            student=student,
            batches=batches,
            error="Full name is required.",
        )

    if phone:
        phone_digits = "".join(c for c in phone if c.isdigit())
        if len(phone_digits) != 11:
            batches = get_batches()
            return render_template(
                "admin/student_edit.html",
                school_name=SCHOOL_NAME,
                student=student,
                batches=batches,
                error="Mobile number must be exactly 11 digits.",
            )
        phone = phone_digits

    try:
        batch_id = int(batch_id) if batch_id else None
    except (TypeError, ValueError):
        batch_id = None

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE students SET full_name=%s, nickname=%s, email=%s, phone=%s, baria_address=%s, "
                "current_address=%s, profession=%s, organization_name=%s, blood_group=%s, batch_id=%s WHERE id=%s",
                (full_name, nickname or None, email or None, phone or None, baria_address or None,
                 current_address or None, profession or None, organization_name or None, blood_group or None, batch_id, student_id),
            )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return redirect(url_for("admin_students"))


@app.route("/admin/registrations")
@admin_required
def admin_registrations():
    """View registrations; optional event_id filter."""
    event_id = request.args.get("event_id", type=int)
    events = get_all_events()
    registrations = get_registrations(event_id)
    return render_template(
        "admin/registrations.html",
        school_name=SCHOOL_NAME,
        events=events,
        registrations=registrations,
        selected_event_id=event_id,
    )


@app.route("/admin/registrations/<int:reg_id>/confirm", methods=["POST"])
@admin_required
def admin_confirm_registration(reg_id):
    """When admin clicks Confirm, set status to CONFIRMED."""
    event_id = request.form.get("event_id") or None
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE event_registrations SET status = 'CONFIRMED' WHERE id = %s",
                (reg_id,),
            )
        conn.commit()
        flash("Registration confirmed.", "success")
    except Exception:
        if conn:
            conn.rollback()
        flash("Could not confirm registration. Please try again.", "error")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    if event_id:
        return redirect(url_for("admin_registrations", event_id=event_id))
    return redirect(request.referrer or url_for("admin_registrations"))


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT") or 5000)
    app.run(debug=DEBUG, host="0.0.0.0", port=port)
