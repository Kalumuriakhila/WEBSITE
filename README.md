# DeepGuard AI — Deepfake Detection using Deep Learning and Flask

A full-stack Python & Flask web application for deepfake video verification, featuring user authentication, video upload, OpenCV frame & face forensic analysis, and interactive prediction results.

## Features

- **User Authentication** — Signup, login, logout with hashed passwords (Werkzeug) and session management
- **Video Upload** — Drag-and-drop or click-to-upload with file type/size validation (MP4, AVI, MOV, MKV, WEBM up to 100 MB)
- **Deepfake Analysis** — OpenCV-based frame sampling, Haar cascade face detection, Laplacian sharpness scoring, DCT spectral anomaly detection, and temporal consistency analysis
- **Optional Keras Model** — Plug in a custom TensorFlow/Keras model at `models/deepfake_detector.keras` for neural inference
- **Prediction Results** — REAL/FAKE verdict with confidence percentage, embedded video player, forensic metrics dashboard, and annotated sample frame thumbnails
- **Contact Form** — Inquiry form with validation, persisted to SQLite
- **Scan History** — Recent scan history per user on the upload page
- **Responsive Design** — Mobile-friendly with hamburger navigation menu
- **Error Handling** — Custom 404/500 error pages
- **Security** — Secure session cookies (HttpOnly, SameSite), input validation, parameterized SQL queries

## Project Structure

```
WEBSITE/
├── app.py                  # Flask application (routes, auth, error handlers)
├── database.py             # SQLite initialization and data access layer
├── detector.py             # Video analysis pipeline (OpenCV + forensic scoring)
├── requirements.txt        # Python dependencies
├── tests.py                # Automated test suite (63 tests)
├── .env.example            # Environment variable template
├── .gitignore
├── README.md
├── PROJECT_ARCHITECTURE.md
├── BUG_REPORT.md
├── TEST_REPORT.md
├── CHANGELOG.md
├── static/
│   ├── css/style.css       # Dark-themed responsive stylesheet
│   ├── js/main.js          # Drag-drop upload, flash dismiss, mobile nav
│   ├── images/
│   │   ├── logo.jpg
│   │   └── founder.jpg
│   ├── uploads/            # Uploaded video files (gitignored)
│   └── frames/             # Extracted frame thumbnails (gitignored)
├── templates/
│   ├── base.html           # Base layout (navbar, flash alerts, footer)
│   ├── index.html          # Home page
│   ├── login.html          # Login form
│   ├── signup.html         # Registration form
│   ├── contact.html        # Contact Us form
│   ├── upload.html         # Video upload + scan history
│   ├── result.html         # Prediction result page
│   └── error.html          # Custom error page (404/500)
└── models/                 # (Optional) Custom Keras model directory
    └── deepfake_detector.keras
```

## Prerequisites

- Python 3.10 or later
- pip

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd WEBSITE

# Install dependencies
pip install -r requirements.txt

# (Optional) Set environment variables
cp .env.example .env
# Edit .env with a strong FLASK_SECRET_KEY
```

## Run Locally

```bash
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Run Tests

```bash
python tests.py
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `FLASK_SECRET_KEY` | Secret key for session signing | `deepfake-flask-project-secret-key` |
| `FLASK_DEBUG` | Enable debug mode (`1`/`0`) | `1` |

> **Important:** Always set a strong random `FLASK_SECRET_KEY` for production:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

## Pages

| Route | Page | Auth Required |
|---|---|---|
| `/` | Home — platform overview with feature cards | No |
| `/signup` | User registration | No |
| `/login` | User login | No |
| `/contact` | Contact Us inquiry form | No |
| `/upload` | Video upload + scan history | Yes |
| `/result/<scan_id>` | Prediction result with forensics | Yes |

## Technology Stack

- **Backend:** Python 3, Flask 3, Werkzeug
- **Database:** SQLite 3
- **Computer Vision:** OpenCV (Haar cascades, Laplacian, DCT)
- **ML (optional):** TensorFlow/Keras
- **Frontend:** Jinja2 templates, vanilla CSS/JS
- **Security:** Werkzeug password hashing, parameterized queries, session hardening

## License

This project is for educational purposes.
