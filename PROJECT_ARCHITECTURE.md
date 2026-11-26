# Project Architecture — DeepGuard AI

## Overview

DeepGuard AI is a monolithic Flask web application that allows users to upload videos and analyze them for deepfake manipulation. The system uses OpenCV for frame extraction and face detection, combined with forensic signal analysis (Laplacian sharpness, DCT spectral anomalies, temporal consistency) to classify videos as REAL or FAKE.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Client)                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Jinja2 Templates + CSS + Vanilla JavaScript      │   │
│  │  - base.html (layout, nav, flash messages)        │   │
│  │  - index.html, login.html, signup.html, etc.      │   │
│  │  - main.js (drag-drop, flash dismiss, mobile nav) │   │
│  │  - style.css (dark theme, responsive grid)        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP (GET/POST)
┌─────────────────────▼───────────────────────────────────┐
│                   Flask Application (app.py)             │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Routes:                                             │  │
│  │  GET  /            → home()                         │  │
│  │  GET/POST /signup  → signup()                       │  │
│  │  GET/POST /login   → login()                        │  │
│  │  GET  /logout      → logout()                       │  │
│  │  GET/POST /contact → contact()                      │  │
│  │  GET/POST /upload  → upload()  [login_required]     │  │
│  │  GET  /result/<id> → result()  [login_required]     │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ Middleware:                                          │  │
│  │  - login_required decorator                         │  │
│  │  - inject_current_user context processor            │  │
│  │  - Error handlers (404, 413, 500)                   │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ Security:                                           │  │
│  │  - Werkzeug password hashing                        │  │
│  │  - Session cookie hardening (HttpOnly, SameSite)    │  │
│  │  - Input validation (email, phone, password, file)  │  │
│  │  - secure_filename for uploads                      │  │
│  │  - MAX_CONTENT_LENGTH (100 MB)                      │  │
│  └────────────────────────────────────────────────────┘  │
└──────┬──────────────────────────────┬───────────────────┘
       │                              │
┌──────▼──────────────┐    ┌──────────▼──────────────────┐
│  database.py         │    │  detector.py                 │
│  ┌────────────────┐  │    │  ┌────────────────────────┐  │
│  │ SQLite 3       │  │    │  │ OpenCV Pipeline         │  │
│  │  - users       │  │    │  │  1. Open video          │  │
│  │  - scans       │  │    │  │  2. Sample N frames     │  │
│  │  - contact_msgs│  │    │  │  3. Haar face detection │  │
│  │                │  │    │  │  4. Laplacian variance   │  │
│  │ Row factory    │  │    │  │  5. DCT spectral ratio  │  │
│  │ Parameterized  │  │    │  │  6. Temporal diff        │  │
│  │ queries        │  │    │  │  7. Keras model (opt.)  │  │
│  └────────────────┘  │    │  │  8. Score combination   │  │
│                      │    │  │  9. REAL/FAKE verdict   │  │
│  deepfake_app.db     │    │  └────────────────────────┘  │
└──────────────────────┘    └──────────────────────────────┘
```

## Component Descriptions

### 1. Flask Application (`app.py`)
- Central entry point and route controller
- Handles all HTTP request/response cycles
- Manages user sessions and authentication flow
- Coordinates video upload → analysis → result display pipeline

### 2. Database Layer (`database.py`)
- SQLite database with three tables: `users`, `scans`, `contact_messages`
- All queries use parameterized statements (SQL injection safe)
- Row factory enabled for dict-like access to query results
- Functions: `create_user`, `get_user_by_*`, `create_scan`, `get_scan_by_id`, `get_scans_for_user`, `save_contact_message`

### 3. Detector Pipeline (`detector.py`)
- `analyze_video()` — Main pipeline entry point
- Samples up to 16 frames uniformly across the video
- Detects faces using Haar cascade classifier
- Computes per-frame forensic metrics:
  - **Laplacian variance** — detects over-smoothed (synthetic) faces
  - **DCT high-frequency ratio** — detects spectral anomalies from GANs
  - **Temporal frame difference** — detects unnatural motion patterns
- Optionally runs a custom Keras model if present at `models/deepfake_detector.keras`
- Combines forensic signals into a calibrated fake probability
- Returns structured dict with verdict, confidence, and metrics

### 4. Frontend (Templates + Static Assets)
- Jinja2 template inheritance with `base.html` as the layout
- Dark-themed CSS with CSS custom properties
- Responsive grid layout with mobile hamburger menu
- Vanilla JavaScript for drag-and-drop upload, flash message dismiss, and mobile nav toggle

## Data Flow

1. **User registers** → password hashed → stored in `users` table
2. **User logs in** → credentials verified → session created
3. **User uploads video** → file saved to `static/uploads/` → `analyze_video()` called
4. **Analysis runs** → frames extracted → faces detected → forensic scores computed → verdict generated
5. **Scan saved** → result stored in `scans` table with all metrics
6. **Result displayed** → video player + metrics dashboard + annotated frame thumbnails

## Database Schema

### users
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| username | TEXT | NOT NULL UNIQUE |
| email | TEXT | NOT NULL UNIQUE |
| password_hash | TEXT | NOT NULL |
| gender | TEXT | NOT NULL |
| phone | TEXT | NOT NULL |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### scans
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FK → users(id) |
| original_filename | TEXT | NOT NULL |
| stored_filename | TEXT | NOT NULL |
| predicted_class | TEXT | NOT NULL |
| confidence | REAL | NOT NULL |
| frames_analyzed | INTEGER | NOT NULL |
| faces_detected | INTEGER | NOT NULL |
| temporal_score | REAL | NOT NULL |
| artifact_score | REAL | NOT NULL |
| duration_seconds | REAL | NOT NULL |
| sample_frames_json | TEXT | NOT NULL |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### contact_messages
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | TEXT | NOT NULL |
| email | TEXT | NOT NULL |
| subject | TEXT | NOT NULL |
| message | TEXT | NOT NULL |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
