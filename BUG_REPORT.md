# Bug Report — DeepGuard AI

## Bugs Discovered and Fixed

### BUG-001: TensorFlow required but not needed
- **Severity:** High
- **Location:** `requirements.txt`
- **Description:** `tensorflow>=2.18.0` was listed as a mandatory dependency, causing `pip install -r requirements.txt` to fail on many systems (especially Windows with Python 3.13, ARM architectures, or systems without GPU). TensorFlow is only used if a custom Keras model file exists on disk.
- **Fix:** Moved TensorFlow to an optional/commented dependency. The app functions fully without it using the forensic-scoring fallback.
- **Status:** ✅ Fixed

### BUG-002: Missing custom error handlers
- **Severity:** Medium
- **Location:** `app.py`
- **Description:** No custom 404/500 error handlers were defined. Users seeing raw Flask error pages could be confused and potentially see internal stack trace information in debug mode.
- **Fix:** Added `@app.errorhandler(404)`, `@app.errorhandler(413)`, and `@app.errorhandler(500)` with a new `error.html` template.
- **Status:** ✅ Fixed

### BUG-003: Session cookie security flags missing
- **Severity:** Medium (Security)
- **Location:** `app.py`
- **Description:** Session cookies were not configured with `HttpOnly` or `SameSite` flags, leaving them vulnerable to XSS session theft and CSRF attacks.
- **Fix:** Added `SESSION_COOKIE_HTTPONLY = True` and `SESSION_COOKIE_SAMESITE = "Lax"` to app config.
- **Status:** ✅ Fixed

### BUG-004: Error message leaks internal exception details
- **Severity:** Medium (Security)
- **Location:** `app.py` line 212 (original)
- **Description:** `flash(f"Video analysis failed: {exc}", "danger")` exposed internal Python exception messages to users, potentially leaking file paths, library versions, or stack details.
- **Fix:** Changed to generic error message `"Video analysis failed. Please try uploading a different video."` with detailed logging via `logger.exception()`.
- **Status:** ✅ Fixed

### BUG-005: No phone number validation
- **Severity:** Low
- **Location:** `app.py` signup route
- **Description:** Phone number field accepted any string value including letters and special characters.
- **Fix:** Added regex validation `^[0-9]{7,15}$` requiring 7–15 digits only.
- **Status:** ✅ Fixed

### BUG-006: No username validation
- **Severity:** Low
- **Location:** `app.py` signup route
- **Description:** No length or character restrictions on usernames.
- **Fix:** Added validation for 3–30 characters, alphanumeric and underscores only.
- **Status:** ✅ Fixed

### BUG-007: Mobile navigation broken
- **Severity:** Medium (UX)
- **Location:** `base.html`, `style.css`
- **Description:** No hamburger menu for mobile screens. Navigation links overflowed and became inaccessible on screens < 700px.
- **Fix:** Added hamburger button in `base.html`, mobile nav styles in CSS, and toggle logic in `main.js`.
- **Status:** ✅ Fixed

### BUG-008: Flash messages never auto-dismiss
- **Severity:** Low (UX)
- **Location:** `base.html`, `main.js`, `style.css`
- **Description:** Flash messages stacked up and never disappeared, cluttering the UI.
- **Fix:** Added auto-dismiss after 5 seconds with fade-out animation, plus manual close button (×).
- **Status:** ✅ Fixed

### BUG-009: Missing .gitkeep files
- **Severity:** Low
- **Location:** `static/uploads/`, `static/frames/`
- **Description:** `.gitignore` referenced `.gitkeep` files that didn't exist, so the directories wouldn't be tracked in git.
- **Fix:** Created `.gitkeep` files in both directories.
- **Status:** ✅ Fixed

### BUG-010: No .env.example file
- **Severity:** Low
- **Location:** Project root
- **Description:** No reference file for environment variables, making deployment setup unclear.
- **Fix:** Created `.env.example` documenting `FLASK_SECRET_KEY` and `FLASK_DEBUG`.
- **Status:** ✅ Fixed

### BUG-011: Stale session when user deleted
- **Severity:** Low
- **Location:** `app.py` context processor
- **Description:** If a user record was deleted while a session was active, the `inject_current_user` context processor would silently return `None` but leave the session intact, potentially causing confusing behavior.
- **Fix:** Added session cleanup when user lookup returns None.
- **Status:** ✅ Fixed

### BUG-012: No logging configured
- **Severity:** Low
- **Location:** `app.py`
- **Description:** No logging was configured. Important events (signups, logins, errors) were not recorded.
- **Fix:** Added Python logging configuration and log statements for auth events, contact messages, and scan creation.
- **Status:** ✅ Fixed

### BUG-013: Contact form email validation missing
- **Severity:** Low
- **Location:** `app.py` contact route
- **Description:** Contact form email field was not validated on the server side (only HTML `type="email"` on frontend).
- **Fix:** Added server-side email regex validation.
- **Status:** ✅ Fixed

## Known Limitations

- **CSRF protection enabled** — `Flask-WTF` (`CSRFProtect`) is enabled globally across all `POST` forms (`login`, `signup`, `contact`, `upload`) with a custom 400 error handler (`CSRFError`).
- **No rate limiting** — Brute-force protection on login/signup is not implemented. Consider adding `flask-limiter` for production.
- **SQLite is single-writer** — Suitable for development and small deployments; for high-concurrency production use, consider PostgreSQL.
- **No password reset** — Users cannot recover accounts if they forget their password.
- **Browser automation** — Headless/live Chrome DevTools testing could not run because Chrome remote debugging (`DevToolsActivePort`) is not enabled in the local environment; live HTTP end-to-end verification was performed via Python `urllib` with cookie & CSRF handling instead.
