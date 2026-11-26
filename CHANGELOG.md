# Changelog — DeepGuard AI

All notable changes to this project are documented in this file.

## [1.1.0] — 2026-11-26

### Added
- **Custom error pages** — 404 (Page Not Found), 413 (File Too Large), 500 (Internal Server Error) with new `error.html` template
- **Mobile-responsive navigation** — Hamburger menu for screens < 700px with animated toggle
- **Flash message auto-dismiss** — Messages auto-fade after 5 seconds with manual close button
- **Input validation enhancements** — Server-side phone number validation (7–15 digits), username validation (3–30 chars, alphanumeric + underscores), contact form email validation
- **Stale session cleanup** — Context processor clears session if referenced user no longer exists
- **Application logging** — Structured logging for auth events, contact messages, scan creation, and errors
- **CSRF protection** — Enabled `Flask-WTF` `CSRFProtect` across all `POST` forms (`login.html`, `signup.html`, `contact.html`, `upload.html`) with custom 400 `CSRFError` handler
- **Security headers** — Added `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, and `Referrer-Policy: strict-origin-when-cross-origin` via `@app.after_request`
- **Database hardening** — Enabled `PRAGMA foreign_keys = ON`, added `idx_scans_user_created` index, and added `_db_session()` context manager so SQLite connections always close cleanly
- **Ephemeral secret key fallback** — Removed hardcoded `SECRET_KEY` fallback; generates `secrets.token_hex(32)` with a warning log when `FLASK_SECRET_KEY` is unset
- **Automated test suite** — 77 comprehensive tests in `tests.py` using isolated temporary directories, including synthetic video upload E2E analysis and CSRF enforcement tests
- **Project documentation** — `README.md` (expanded), `PROJECT_ARCHITECTURE.md`, `BUG_REPORT.md`, `TEST_REPORT.md`, `CHANGELOG.md`, `.env.example`
- **Git directory markers** — `.gitkeep` files for `static/uploads/` and `static/frames/`
- **flask-wtf** dependency added to `requirements.txt`

### Changed
- **requirements.txt** — TensorFlow moved from mandatory to optional (commented out) since the app works fully with forensic scoring when no Keras model is present
- **Error messages** — Video analysis failure no longer leaks internal exception details to the user; uses generic message with server-side logging instead
- **Session cookies** — Added `HttpOnly` and `SameSite=Lax` security flags
- **Debug mode** — Now controlled by `FLASK_DEBUG` environment variable (defaults to `1`)

### Fixed
- **BUG-001:** `pip install -r requirements.txt` failing on systems without TensorFlow support
- **BUG-002:** Missing error handlers showing raw Flask errors
- **BUG-003:** Session cookies lacking security flags
- **BUG-004:** Internal exception details exposed in flash messages
- **BUG-005:** Phone number accepting arbitrary text
- **BUG-006:** No username length/character restrictions
- **BUG-007:** Navigation links overflowing on mobile screens
- **BUG-008:** Flash messages stacking without dismissal
- **BUG-009:** Missing `.gitkeep` files preventing directory tracking
- **BUG-010:** No `.env.example` for deployment reference
- **BUG-011:** Stale session when user record deleted
- **BUG-012:** No application logging configured
- **BUG-013:** Contact form email not validated server-side

### Security
- Session cookie hardening (HttpOnly + SameSite)
- Error messages sanitized to prevent information leakage
- Enhanced input validation on all forms

## [1.0.0] — Initial Release

### Features
- Home page with platform overview and feature cards
- User signup with email, username, password, gender, phone
- User login/logout with hashed passwords
- Contact Us form persisted to SQLite
- Video upload with drag-and-drop interface
- OpenCV-based deepfake analysis pipeline
- Prediction result page with verdict, confidence, video player, and forensic metrics
- Scan history per user
- Dark-themed responsive UI
