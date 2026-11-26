"""SQLite database initialization and data access helpers."""

from contextlib import contextmanager
import os
import sqlite3
from typing import Any, Dict, Iterator, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "deepfake_app.db")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _db_session() -> Iterator[sqlite3.Connection]:
    """Context manager that commits/rolls back and always closes the SQLite connection."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create application tables if they do not already exist."""
    with _db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                gender TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                predicted_class TEXT NOT NULL,
                confidence REAL NOT NULL,
                frames_analyzed INTEGER NOT NULL,
                faces_detected INTEGER NOT NULL,
                temporal_score REAL NOT NULL,
                artifact_score REAL NOT NULL,
                duration_seconds REAL NOT NULL,
                sample_frames_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_scans_user_created
            ON scans (user_id, created_at DESC, id DESC);
            """
        )


def create_user(
    username: str,
    email: str,
    password_hash: str,
    gender: str,
    phone: str,
) -> int:
    """Insert a new user and return the created user ID."""
    with _db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (username, email, password_hash, gender, phone)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, email, password_hash, gender, phone),
        )
        return int(cursor.lastrowid)


def get_user_by_username_or_email(identifier: str) -> Optional[Dict[str, Any]]:
    """Fetch a user record by username or email."""
    with _db_session() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (identifier, identifier),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a user record by primary key."""
    with _db_session() as conn:
        row = conn.execute(
            "SELECT id, username, email, gender, phone, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def create_scan(
    user_id: int,
    original_filename: str,
    stored_filename: str,
    predicted_class: str,
    confidence: float,
    frames_analyzed: int,
    faces_detected: int,
    temporal_score: float,
    artifact_score: float,
    duration_seconds: float,
    sample_frames_json: str,
) -> int:
    """Persist a video deepfake scan result and return its ID."""
    with _db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scans (
                user_id, original_filename, stored_filename, predicted_class,
                confidence, frames_analyzed, faces_detected, temporal_score,
                artifact_score, duration_seconds, sample_frames_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                original_filename,
                stored_filename,
                predicted_class,
                confidence,
                frames_analyzed,
                faces_detected,
                temporal_score,
                artifact_score,
                duration_seconds,
                sample_frames_json,
            ),
        )
        return int(cursor.lastrowid)


def get_scan_by_id(scan_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a scan belonging to the specified user."""
    with _db_session() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE id = ? AND user_id = ?",
            (scan_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def get_scans_for_user(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Return recent scans for a user ordered newest-first."""
    with _db_session() as conn:
        rows = conn.execute(
            """
            SELECT * FROM scans
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def save_contact_message(name: str, email: str, subject: str, message: str) -> int:
    """Store a Contact Us submission."""
    with _db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO contact_messages (name, email, subject, message)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, subject, message),
        )
        return int(cursor.lastrowid)
