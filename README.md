# DeepGuard AI — Deepfake Detection using Deep Learning and Flask

A full-stack Python & Flask web application for deepfake video verification, featuring user authentication, video upload, OpenCV frame & face forensic analysis, and interactive prediction results.

## Pages Included
- **Home (`/`)**: Overview of the platform with Login, Signup, and Contact Us navigation.
- **Signup (`/signup`)**: User registration with username, email, password, gender, and phone number.
- **Login (`/login`)**: Session-based authentication with hashed passwords.
- **Contact Us (`/contact`)**: Inquiry form persisted to SQLite.
- **Video Upload (`/upload`)**: Drag-and-drop video upload (`MP4`, `AVI`, `MOV`, `MKV`, `WEBM`) and recent scan history.
- **Prediction Result (`/result/<scan_id>`)**: Displays `REAL` or `FAKE` verdict, confidence percentage, embedded video player, forensic metrics, and sampled frame thumbnails.

## Run Locally
```bash
pip install -r requirements.txt
python app.py
```
Then open `http://127.0.0.1:5000` in your browser.
