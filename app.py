"""Flask web application for Deepfake Video Detection."""

import json
import logging
import os
import re
import secrets
import uuid
from functools import wraps
from typing import Callable

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFError, CSRFProtect
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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WRITABLE_STATIC_DIR = "/tmp" if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "static")
UPLOAD_FOLDER = os.path.join(WRITABLE_STATIC_DIR, "uploads")
FRAMES_FOLDER = os.path.join(WRITABLE_STATIC_DIR, "frames")
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
_env_secret = os.environ.get("FLASK_SECRET_KEY")
if not _env_secret:
    _env_secret = secrets.token_hex(32)
    logger.warning(
        "FLASK_SECRET_KEY not set; using an ephemeral random key for this process."
    )
app.config["SECRET_KEY"] = _env_secret
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["FRAMES_FOLDER"] = FRAMES_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

# Session cookie hardening
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

csrf = CSRFProtect(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(FRAMES_FOLDER, exist_ok=True)
init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Context Processor
# ---------------------------------------------------------------------------
@app.context_processor
def inject_current_user():
    """Make current_user available across all Jinja templates."""
    user = None
    if "user_id" in session:
        user = get_user_by_id(session["user_id"])
        # If user was deleted but session still exists, clean up
        if user is None:
            session.clear()
    return {"current_user": user}


# ---------------------------------------------------------------------------
# Security Headers & Error Handlers
# ---------------------------------------------------------------------------
@app.after_request
def add_security_headers(response):
    """Attach standard security headers to every HTTP response."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle invalid or missing CSRF tokens gracefully."""
    logger.warning("CSRF validation failed: %s", e.description)
    return (
        render_template(
            "error.html",
            error_code=400,
            error_title="Invalid Request",
            error_message="Your form session expired or the security token was invalid. Please go back and try again.",
        ),
        400,
    )


@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 page."""
    return render_template("error.html", error_code=404,
                           error_title="Page Not Found",
                           error_message="The page you are looking for does not exist or has been moved."), 404


@app.errorhandler(413)
def file_too_large(e):
    """Custom 413 — uploaded file exceeds MAX_CONTENT_LENGTH."""
    flash("The uploaded file is too large. Maximum allowed size is 100 MB.", "danger")
    return redirect(url_for("upload"))


@app.errorhandler(500)
def internal_server_error(e):
    """Custom 500 page."""
    logger.exception("Internal server error")
    return render_template("error.html", error_code=500,
                           error_title="Internal Server Error",
                           error_message="Something went wrong on our end. Please try again later."), 500


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
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

        if len(username) < 3 or len(username) > 30:
            flash("Username must be between 3 and 30 characters.", "danger")
            return render_template("signup.html")

        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            flash("Username may only contain letters, numbers, and underscores.", "danger")
            return render_template("signup.html")

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Please enter a valid email address.", "danger")
            return render_template("signup.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("signup.html")

        if not re.match(r"^[0-9]{7,15}$", phone):
            flash("Phone number must be 7–15 digits (numbers only).", "danger")
            return render_template("signup.html")

        if get_user_by_username_or_email(username) or get_user_by_username_or_email(email):
            flash("An account with that username or email already exists.", "danger")
            return render_template("signup.html")

        password_hash = generate_password_hash(password)
        create_user(username, email, password_hash, gender, phone)
        logger.info("New user registered: %s", username)
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
            logger.info("User logged in: %s", user["username"])
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("upload"))

        flash("Invalid username or password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear user session and return to Home Page."""
    username = session.get("username", "unknown")
    session.clear()
    logger.info("User logged out: %s", username)
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

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Please enter a valid email address.", "danger")
            return render_template("contact.html")

        save_contact_message(name, email, subject, message)
        logger.info("Contact message received from %s (%s)", name, email)
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
        if not original_name or "." not in original_name:
            ext = file.filename.rsplit(".", 1)[1].lower()
            original_name = f"uploaded_video.{ext}"
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
            logger.exception("Video analysis failed for %s", original_name)
            if os.path.exists(save_path):
                os.remove(save_path)
            flash("Video analysis failed. Please try uploading a different video.", "danger")
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
        logger.info("Scan %d created for user %d — %s (%.2f%%)",
                     scan_id, user_id, analysis["predicted_class"], analysis["confidence"])
        return redirect(url_for("result", scan_id=scan_id))

    recent_scans = get_scans_for_user(user_id, limit=8)
    return render_template("upload.html", recent_scans=recent_scans)


@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename: str):
    """Serve uploaded videos from UPLOAD_FOLDER (supports /tmp on Vercel)."""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/static/frames/<path:filename>")
def frame_file(filename: str):
    """Serve extracted frame thumbnails from FRAMES_FOLDER (supports /tmp on Vercel)."""
    return send_from_directory(app.config["FRAMES_FOLDER"], filename)


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
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)
