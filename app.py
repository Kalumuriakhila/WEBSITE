"""Flask web application for Deepfake Video Detection."""

import json
import os
import re
import uuid
from functools import wraps
from typing import Callable

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import (
    create_scan,
    create_user,
    get_scan_by_id,
    get_scans_for_user,
    get_user_by_id,
    get_user_by_username_or_email,
    init_db,
    save_contact_message,
)
from detector import analyze_video

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
FRAMES_FOLDER = os.path.join(BASE_DIR, "static", "frames")
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "deepfake-flask-project-secret-key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["FRAMES_FOLDER"] = FRAMES_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FRAMES_FOLDER, exist_ok=True)
init_db()


def allowed_file(filename: str) -> bool:
    """Check whether the uploaded file has an allowed video extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view: Callable) -> Callable:
    """Redirect unauthenticated visitors to the login page."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access the video analysis portal.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_current_user():
    """Make current_user available across all Jinja templates."""
    user = None
    if "user_id" in session:
        user = get_user_by_id(session["user_id"])
    return {"current_user": user}


@app.route("/")
def home():
    """Home Page."""
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """User Signup / Registration Page."""
    if "user_id" in session:
        return redirect(url_for("upload"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        gender = request.form.get("gender", "Male").strip()
        phone = request.form.get("phone", "").strip()

        if not all([username, email, password, gender, phone]):
            flash("All registration fields are required.", "danger")
            return render_template("signup.html")

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Please enter a valid email address.", "danger")
            return render_template("signup.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("signup.html")

        if get_user_by_username_or_email(username) or get_user_by_username_or_email(email):
            flash("An account with that username or email already exists.", "danger")
            return render_template("signup.html")

        password_hash = generate_password_hash(password)
        create_user(username, email, password_hash, gender, phone)
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login Page."""
    if "user_id" in session:
        return redirect(url_for("upload"))

    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        user = get_user_by_username_or_email(identifier)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("upload"))

        flash("Invalid username or password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear user session and return to Home Page."""
    session.clear()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("home"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact Us Page."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not all([name, email, subject, message]):
            flash("Please complete all fields before sending your message.", "danger")
            return render_template("contact.html")

        save_contact_message(name, email, subject, message)
        flash("Thank you! Your message has been received by our team.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Video Upload Page and recent scan history."""
    user_id = session["user_id"]

    if request.method == "POST":
        if "video" not in request.files:
            flash("No video file was provided in the request.", "danger")
            return redirect(url_for("upload"))

        file = request.files["video"]
        if not file or file.filename == "":
            flash("Please choose a video file to upload.", "warning")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename):
            flash(
                "Unsupported file format. Please upload MP4, AVI, MOV, MKV, or WEBM.",
                "danger",
            )
            return redirect(url_for("upload"))

        original_name = secure_filename(file.filename)
        unique_prefix = uuid.uuid4().hex[:12]
        stored_name = f"{unique_prefix}_{original_name}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        file.save(save_path)

        try:
            analysis = analyze_video(
                video_path=save_path,
                frames_output_dir=app.config["FRAMES_FOLDER"],
                scan_prefix=unique_prefix,
            )
        except Exception as exc:
            if os.path.exists(save_path):
                os.remove(save_path)
            flash(f"Video analysis failed: {exc}", "danger")
            return redirect(url_for("upload"))

        scan_id = create_scan(
            user_id=user_id,
            original_filename=original_name,
            stored_filename=stored_name,
            predicted_class=analysis["predicted_class"],
            confidence=analysis["confidence"],
            frames_analyzed=analysis["frames_analyzed"],
            faces_detected=analysis["faces_detected"],
            temporal_score=analysis["temporal_score"],
            artifact_score=analysis["artifact_score"],
            duration_seconds=analysis["duration_seconds"],
            sample_frames_json=json.dumps(analysis["sample_frames"]),
        )
        return redirect(url_for("result", scan_id=scan_id))

    recent_scans = get_scans_for_user(user_id, limit=8)
    return render_template("upload.html", recent_scans=recent_scans)


@app.route("/result/<int:scan_id>")
@login_required
def result(scan_id: int):
    """Prediction Result Page displaying verdict, confidence, video player, and frame forensics."""
    scan = get_scan_by_id(scan_id, session["user_id"])
    if not scan:
        flash("Scan report not found.", "danger")
        return redirect(url_for("upload"))

    try:
        sample_frames = json.loads(scan["sample_frames_json"])
    except Exception:
        sample_frames = []

    return render_template("result.html", scan=scan, sample_frames=sample_frames)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
