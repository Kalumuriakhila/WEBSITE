"""Comprehensive automated test suite for the Deepfake Detection application."""

import io
import os
import re
import sqlite3
import sys
import tempfile

import cv2
import numpy as np

# Ensure project dir is on path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

import database
import app as flask_app
from detector import (
    _compute_frame_forensics,
    _get_keras_model,
    _load_face_cascade,
    analyze_video,
)


def _create_synthetic_video(path: str, num_frames: int = 12, width: int = 320, height: int = 240) -> None:
    """Create a valid synthetic AVI video file for testing video upload & analysis."""
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(path, fourcc, 10.0, (width, height))
    assert writer.isOpened(), f"Failed to create synthetic video at {path}"
    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (20 + i * 5, 40), (140 + i * 5, 180), (0, 200, 255), -1)
        cv2.circle(frame, (160, 120), 40, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()


def _extract_csrf(html_bytes: bytes) -> str:
    """Extract csrf_token value from rendered HTML form."""
    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"', html_bytes
    )
    return match.group(1).decode("utf-8") if match else ""


def run_tests() -> bool:
    results = {"passed": 0, "failed": 0, "errors": []}

    def assert_test(name: str, condition: bool, detail: str = "") -> None:
        if condition:
            results["passed"] += 1
            print(f"  PASS: {name}")
        else:
            results["failed"] += 1
            msg = f"  FAIL: {name} - {detail}" if detail else f"  FAIL: {name}"
            results["errors"].append(msg)
            print(msg)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Isolate DB, uploads, and frames inside temporary directory
        test_db = os.path.join(tmpdir, "test_deepfake.db")
        test_uploads = os.path.join(tmpdir, "uploads")
        test_frames = os.path.join(tmpdir, "frames")
        os.makedirs(test_uploads, exist_ok=True)
        os.makedirs(test_frames, exist_ok=True)

        database.DB_PATH = test_db
        flask_app.app.config["TESTING"] = True
        flask_app.app.config["WTF_CSRF_ENABLED"] = False
        flask_app.app.config["UPLOAD_FOLDER"] = test_uploads
        flask_app.app.config["FRAMES_FOLDER"] = test_frames

        client = flask_app.app.test_client()

        # ===================================================================
        print("\n=== PHASE 1: DATABASE TESTS ===")
        # ===================================================================
        database.init_db()
        conn = database.get_connection()
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        fk_status = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        indexes = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        ]
        conn.close()

        assert_test("Users table exists", "users" in tables)
        assert_test("Scans table exists", "scans" in tables)
        assert_test("Contact_messages table exists", "contact_messages" in tables)
        assert_test("Foreign keys pragma enabled", fk_status == 1)
        assert_test("Scans index exists", "idx_scans_user_created" in indexes)

        uid = database.create_user(
            "testuser1", "test1@example.com", "hash123", "Male", "1234567890"
        )
        assert_test("Create user returns ID", uid is not None and uid > 0)

        user = database.get_user_by_id(uid)
        assert_test("Get user by ID", user is not None)
        assert_test(
            "User data correct",
            user["username"] == "testuser1" and user["email"] == "test1@example.com",
        )
        assert_test("Password hash not exposed by get_user_by_id", "password_hash" not in user)

        user2 = database.get_user_by_username_or_email("testuser1")
        assert_test("Get user by username", user2 is not None and user2["username"] == "testuser1")

        user3 = database.get_user_by_username_or_email("test1@example.com")
        assert_test("Get user by email", user3 is not None and user3["email"] == "test1@example.com")

        user4 = database.get_user_by_username_or_email("nonexistent")
        assert_test("Non-existent user returns None", user4 is None)

        cid = database.save_contact_message(
            "Test Name", "contact@test.com", "Test Subject", "Hello!"
        )
        assert_test("Save contact message", cid is not None and cid > 0)

        scan_id = database.create_scan(
            user_id=uid,
            original_filename="test.mp4",
            stored_filename="abc_test.mp4",
            predicted_class="REAL",
            confidence=85.5,
            frames_analyzed=16,
            faces_detected=12,
            temporal_score=92.0,
            artifact_score=15.0,
            duration_seconds=10.5,
            sample_frames_json="[]",
        )
        assert_test("Create scan returns ID", scan_id is not None and scan_id > 0)

        scan = database.get_scan_by_id(scan_id, uid)
        assert_test("Get scan by ID and user", scan is not None)
        assert_test(
            "Scan data correct",
            scan["predicted_class"] == "REAL" and scan["confidence"] == 85.5,
        )

        wrong_scan = database.get_scan_by_id(scan_id, uid + 999)
        assert_test("Scan not returned for wrong user", wrong_scan is None)

        scans_list = database.get_scans_for_user(uid, limit=10)
        assert_test("Get scans for user", len(scans_list) >= 1)

        # ===================================================================
        print("\n=== PHASE 2: ROUTE & PAGE TESTS ===")
        # ===================================================================
        resp = client.get("/")
        assert_test("Home page returns 200", resp.status_code == 200)
        assert_test("Home page has content", b"Deepfake Detection" in resp.data)

        resp = client.get("/login")
        assert_test("Login page returns 200", resp.status_code == 200)
        assert_test("Login page has form", b"Login" in resp.data)

        resp = client.get("/signup")
        assert_test("Signup page returns 200", resp.status_code == 200)
        assert_test("Signup page has form", b"Signup" in resp.data)

        resp = client.get("/contact")
        assert_test("Contact page returns 200", resp.status_code == 200)
        assert_test("Contact page has form", b"Contact" in resp.data)

        resp = client.get("/nonexistent-page")
        assert_test("404 returns correct status", resp.status_code == 404)
        assert_test("404 has error page content", b"Page Not Found" in resp.data)

        resp = client.get("/upload", follow_redirects=True)
        assert_test(
            "Upload redirects to login when unauthenticated",
            b"Please log in" in resp.data or b"Login" in resp.data,
        )

        # ===================================================================
        print("\n=== PHASE 3: AUTHENTICATION TESTS ===")
        # ===================================================================
        resp = client.post(
            "/signup",
            data={
                "username": "authtest",
                "email": "authtest@test.com",
                "password": "password123",
                "gender": "Male",
                "phone": "9876543210",
            },
            follow_redirects=True,
        )
        assert_test("Signup success", b"Account created" in resp.data or b"Login" in resp.data)

        resp = client.post(
            "/signup",
            data={
                "username": "",
                "email": "bad@test.com",
                "password": "123456",
                "gender": "Male",
                "phone": "1234567890",
            },
            follow_redirects=True,
        )
        assert_test(
            "Signup rejects empty username",
            b"required" in resp.data.lower() or b"All registration" in resp.data,
        )

        resp = client.post(
            "/signup",
            data={
                "username": "shortpw",
                "email": "short@test.com",
                "password": "123",
                "gender": "Male",
                "phone": "1234567890",
            },
            follow_redirects=True,
        )
        assert_test("Signup rejects short password", b"6 characters" in resp.data)

        resp = client.post(
            "/signup",
            data={
                "username": "badphone",
                "email": "badphone@test.com",
                "password": "password123",
                "gender": "Male",
                "phone": "abc",
            },
            follow_redirects=True,
        )
        assert_test("Signup rejects invalid phone", b"digits" in resp.data)

        resp = client.post(
            "/signup",
            data={
                "username": "bademail",
                "email": "not-an-email",
                "password": "password123",
                "gender": "Male",
                "phone": "1234567890",
            },
            follow_redirects=True,
        )
        assert_test("Signup rejects invalid email", b"valid email" in resp.data)

        resp = client.post(
            "/signup",
            data={
                "username": "authtest",
                "email": "dup@test.com",
                "password": "password123",
                "gender": "Male",
                "phone": "1234567890",
            },
            follow_redirects=True,
        )
        assert_test("Signup rejects duplicate username", b"already exists" in resp.data)

        resp = client.post(
            "/login",
            data={"username": "authtest", "password": "password123"},
            follow_redirects=True,
        )
        assert_test("Login success", b"Welcome back" in resp.data or b"Upload" in resp.data)

        resp = client.get("/upload")
        assert_test("Upload page accessible when logged in", resp.status_code == 200)
        assert_test("Upload page has upload form", b"Upload" in resp.data)

        # ===================================================================
        print("\n=== PHASE 4: VIDEO UPLOAD & E2E ANALYSIS TESTS ===")
        # ===================================================================
        resp = client.post("/upload", data={}, follow_redirects=True)
        assert_test(
            "Upload rejects no file",
            b"No video" in resp.data or b"choose" in resp.data.lower(),
        )

        resp = client.post(
            "/upload",
            data={"video": (io.BytesIO(b"not a video"), "evil.exe")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert_test("Upload rejects disallowed extension", b"Unsupported file format" in resp.data)

        resp = client.post(
            "/upload",
            data={"video": (io.BytesIO(b"corrupted bytes"), "corrupt.mp4")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert_test("Upload handles corrupted video gracefully", b"Video analysis failed" in resp.data)

        # Real synthetic video E2E upload -> analysis -> result page
        synth_path = os.path.join(tmpdir, "sample_test.avi")
        _create_synthetic_video(synth_path, num_frames=12)
        with open(synth_path, "rb") as vf:
            resp = client.post(
                "/upload",
                data={"video": (vf, "sample_test.avi")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
        assert_test("Valid video upload & analysis succeeds (200)", resp.status_code == 200)
        assert_test("Result page shows verdict", b"Prediction Result" in resp.data)
        assert_test(
            "Result page shows REAL or FAKE class",
            b"REAL" in resp.data or b"FAKE" in resp.data,
        )
        assert_test("Result page shows Frames Analyzed", b"Frames Analyzed" in resp.data)
        assert_test("Sample frame thumbnails created", len(os.listdir(test_frames)) > 0)

        # Verify scan history appears on /upload
        resp = client.get("/upload")
        assert_test("Scan history shows uploaded video", b"sample_test.avi" in resp.data)

        # Verify another user cannot access the scan result
        client.get("/logout")
        client.post(
            "/signup",
            data={
                "username": "otheruser",
                "email": "other@test.com",
                "password": "password123",
                "gender": "Female",
                "phone": "5551234567",
            },
        )
        client.post("/login", data={"username": "otheruser", "password": "password123"})
        resp = client.get(f"/result/{scan_id}", follow_redirects=True)
        assert_test("Cross-user result access blocked", b"Scan report not found" in resp.data)

        client.get("/logout")
        resp = client.post(
            "/login",
            data={"username": "authtest", "password": "wrongpassword"},
            follow_redirects=True,
        )
        assert_test("Login rejects wrong password", b"Invalid" in resp.data)

        resp = client.post(
            "/login", data={"username": "", "password": ""}, follow_redirects=True
        )
        assert_test("Login rejects empty fields", b"enter both" in resp.data)

        # ===================================================================
        print("\n=== PHASE 5: CONTACT FORM TESTS ===")
        # ===================================================================
        resp = client.post(
            "/contact",
            data={
                "name": "John Doe",
                "email": "john@test.com",
                "subject": "Test Subject",
                "message": "This is a test message",
            },
            follow_redirects=True,
        )
        assert_test("Contact form submission success", b"Thank you" in resp.data)

        resp = client.post(
            "/contact",
            data={"name": "", "email": "john@test.com", "subject": "Test", "message": "Test"},
            follow_redirects=True,
        )
        assert_test("Contact form rejects empty name", b"complete all" in resp.data.lower())

        resp = client.post(
            "/contact",
            data={"name": "John", "email": "not-email", "subject": "Test", "message": "Test"},
            follow_redirects=True,
        )
        assert_test("Contact form rejects invalid email", b"valid email" in resp.data)

        # ===================================================================
        print("\n=== PHASE 6: SECURITY & CSRF TESTS ===")
        # ===================================================================
        assert_test(
            "SESSION_COOKIE_HTTPONLY enabled",
            flask_app.app.config.get("SESSION_COOKIE_HTTPONLY") is True,
        )
        assert_test(
            "SESSION_COOKIE_SAMESITE set",
            flask_app.app.config.get("SESSION_COOKIE_SAMESITE") == "Lax",
        )
        assert_test(
            "MAX_CONTENT_LENGTH set",
            flask_app.app.config.get("MAX_CONTENT_LENGTH") == 100 * 1024 * 1024,
        )

        resp = client.get("/")
        assert_test(
            "X-Content-Type-Options header set",
            resp.headers.get("X-Content-Type-Options") == "nosniff",
        )
        assert_test(
            "X-Frame-Options header set",
            resp.headers.get("X-Frame-Options") == "SAMEORIGIN",
        )
        assert_test(
            "Referrer-Policy header set",
            resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin",
        )

        # Test CSRF enforcement when enabled
        flask_app.app.config["WTF_CSRF_ENABLED"] = True
        csrf_client = flask_app.app.test_client()
        resp = csrf_client.post(
            "/login", data={"username": "authtest", "password": "password123"}
        )
        assert_test("POST without CSRF token rejected (400)", resp.status_code == 400)

        login_page = csrf_client.get("/login")
        token = _extract_csrf(login_page.data)
        assert_test("CSRF token rendered in login form", len(token) > 10)
        resp = csrf_client.post(
            "/login",
            data={"username": "authtest", "password": "password123", "csrf_token": token},
            follow_redirects=True,
        )
        assert_test(
            "POST with valid CSRF token succeeds",
            resp.status_code == 200 and b"Welcome back" in resp.data,
        )
        flask_app.app.config["WTF_CSRF_ENABLED"] = False

        # ===================================================================
        print("\n=== PHASE 7: DETECTOR MODULE TESTS ===")
        # ===================================================================
        cascade = _load_face_cascade()
        assert_test("Face cascade loads successfully", cascade is not None and not cascade.empty())

        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        lap_var, hf_ratio = _compute_frame_forensics(test_frame, None)
        assert_test("Laplacian variance computed", lap_var > 0)
        assert_test("HF ratio computed", 0 <= hf_ratio <= 1)

        lap_var2, _ = _compute_frame_forensics(test_frame, (100, 100, 200, 200))
        assert_test("Forensics with face box works", lap_var2 > 0)

        analysis = analyze_video(synth_path, test_frames, "unit_test")
        assert_test(
            "analyze_video returns valid structure",
            analysis["predicted_class"] in ("REAL", "FAKE")
            and 0 <= analysis["confidence"] <= 100
            and analysis["frames_analyzed"] > 0,
        )

        model = _get_keras_model()
        assert_test("No Keras model loaded (expected - no model file)", model is None)

        # ===================================================================
        print("\n=== PHASE 8: FILE STRUCTURE TESTS ===")
        # ===================================================================
        required_files = [
            "app.py",
            "database.py",
            "detector.py",
            "requirements.txt",
            ".env.example",
            "templates/base.html",
            "templates/error.html",
            "static/css/style.css",
            "static/js/main.js",
        ]
        for rel in required_files:
            assert_test(f"{rel} exists", os.path.isfile(os.path.join(PROJECT_DIR, rel)))

    print("\n" + "=" * 60)
    print(f"RESULTS: {results['passed']} passed, {results['failed']} failed")
    print("=" * 60)
    if results["errors"]:
        print("\nFailed tests:")
        for err in results["errors"]:
            print(f"  {err}")

    return results["failed"] == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
