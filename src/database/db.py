"""
Database Access Layer for Transify.
Provides SQLite-based persistent storage for translation history, user feedback, and accessibility preferences.
"""

import os
import sqlite3
import json
import re
import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_DIR = os.getenv("TRANSIFY_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
DB_PATH = os.getenv("TRANSIFY_DB_PATH", os.path.join(DB_DIR, "transify.db"))


def get_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database with WAL mode and busy timeout."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass
    return conn


def seed_data_if_needed():
    """Seeds sample datasets into TRANSIFY_DATA_DIR if mounted from an empty volume."""
    seed_dir = os.environ.get("TRANSIFY_DATA_SEED_DIR", "/app/data_seed")
    if os.path.isdir(seed_dir) and os.path.abspath(seed_dir) != os.path.abspath(DB_DIR):
        try:
            import shutil
            for item in os.listdir(seed_dir):
                if item == "transify.db" or item.endswith(".db"):
                    continue
                s_item = os.path.join(seed_dir, item)
                d_item = os.path.join(DB_DIR, item)
                if not os.path.exists(d_item):
                    if os.path.isdir(s_item):
                        shutil.copytree(s_item, d_item, dirs_exist_ok=True)
                        logger.info(f"Seeded sample resource directory: {item} -> {d_item}")
                    else:
                        shutil.copy2(s_item, d_item)
                        logger.info(f"Seeded sample resource file: {item} -> {d_item}")
        except Exception as ex:
            logger.error(f"Failed to seed data resources from {seed_dir}: {ex}")


def init_db():
    """Initializes the database schema if tables do not exist."""
    seed_data_if_needed()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS translation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT NOT NULL,
        input_meta TEXT,
        recognized_text TEXT NOT NULL,
        confidence REAL,
        status TEXT NOT NULL,
        diagnostics TEXT,
        feedback_rating INTEGER,
        feedback_comments TEXT,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
        pref_key TEXT PRIMARY KEY,
        pref_value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        session_token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
    """)

    # Populate default preferences if empty
    defaults = {
        "theme": "light",          # 'light', 'dark', 'high-contrast'
        "font_size": "medium",     # 'medium', 'large', 'x-large'
        "tts_speed": "1.0",
        "tts_auto_play": "false",
        "reduce_motion": "false",
        "screen_reader_optimizations": "true"
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    for k, v in defaults.items():
        cursor.execute("""
        INSERT OR IGNORE INTO user_preferences (pref_key, pref_value, updated_at)
        VALUES (?, ?, ?);
        """, (k, v, now_iso))

    # Seed default verified demo account if it does not exist
    cursor.execute("SELECT id FROM users WHERE email = 'demo@transify.ai' COLLATE NOCASE;")
    if not cursor.fetchone():
        demo_salt = secrets.token_hex(16)
        demo_hash = hashlib.pbkdf2_hmac(
            "sha256", "transify2026".encode("utf-8"), demo_salt.encode("utf-8"), 100_000
        ).hex()
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, salt, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, ("Sarah Ahmed", "demo@transify.ai", demo_hash, demo_salt, "user", now_iso, now_iso))

    conn.commit()
    conn.close()


def log_translation(
    module: str,
    recognized_text: str,
    confidence: Optional[float] = None,
    status: str = "SUCCESS",
    input_meta: Optional[Dict[str, Any]] = None,
    diagnostics: Optional[Dict[str, Any]] = None
) -> int:
    """Logs a translation event to database and returns the new history record ID."""
    conn = get_connection()
    cursor = conn.cursor()

    now_iso = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(input_meta or {})
    diag_json = json.dumps(diagnostics or {})
    conf_val = float(confidence) if (confidence is not None and not (isinstance(confidence, float) and (confidence != confidence))) else None

    cursor.execute("""
    INSERT INTO translation_history 
    (module, input_meta, recognized_text, confidence, status, diagnostics, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (module, meta_json, recognized_text, conf_val, status, diag_json, now_iso))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_history(limit: int = 50, module: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves recent translation history records."""
    conn = get_connection()
    cursor = conn.cursor()

    if module:
        cursor.execute("""
        SELECT * FROM translation_history 
        WHERE module = ? 
        ORDER BY id DESC LIMIT ?;
        """, (module, limit))
    else:
        cursor.execute("""
        SELECT * FROM translation_history 
        ORDER BY id DESC LIMIT ?;
        """, (limit,))

    rows = cursor.fetchall()
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "module": r["module"],
            "input_meta": json.loads(r["input_meta"]) if r["input_meta"] else {},
            "recognized_text": r["recognized_text"],
            "confidence": r["confidence"],
            "status": r["status"],
            "diagnostics": json.loads(r["diagnostics"]) if r["diagnostics"] else {},
            "feedback_rating": r["feedback_rating"],
            "feedback_comments": r["feedback_comments"],
            "created_at": r["created_at"]
        })

    conn.close()
    return results


def clear_history() -> int:
    """Clears all translation history records. Returns number of deleted rows."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM translation_history;")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def record_feedback(record_id: int, rating: int, comments: Optional[str] = None) -> bool:
    """Records user feedback on a translation event."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE translation_history 
    SET feedback_rating = ?, feedback_comments = ?
    WHERE id = ?;
    """, (rating, comments, record_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_preferences() -> Dict[str, str]:
    """Retrieves user preferences dictionary."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pref_key, pref_value FROM user_preferences;")
    rows = cursor.fetchall()
    prefs = {r["pref_key"]: r["pref_value"] for r in rows}
    conn.close()
    return prefs


def update_preference(key: str, value: str) -> bool:
    """Updates or sets a preference key/value pair."""
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT INTO user_preferences (pref_key, pref_value, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(pref_key) DO UPDATE SET 
        pref_value = excluded.pref_value,
        updated_at = excluded.updated_at;
    """, (key, str(value), now_iso))
    conn.commit()
    conn.close()
    return True


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a cryptographically secure salt."""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    pwd_hash = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100_000).hex()
    return pwd_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifies a plain password against a stored hash and salt in constant time."""
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    computed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100_000).hex()
    return hmac.compare_digest(password_hash, computed)


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def create_user(name: str, email: str, password: str, role: str = "user") -> Dict[str, Any]:
    """
    Validates and registers a new user in the SQLite database with securely hashed credentials.
    Raises ValueError on invalid input or duplicate email.
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""

    if not name or len(name) < 2:
        raise ValueError("Name must be at least 2 characters long.")
    if not email or not EMAIL_REGEX.match(email):
        raise ValueError("A valid email address is required.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    conn = get_connection()
    cursor = conn.cursor()

    # Check email duplicate
    cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE;", (email,))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"An account with email '{email}' already exists.")

    pwd_hash, salt = hash_password(password)
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
    INSERT INTO users (name, email, password_hash, salt, role, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (name, email, pwd_hash, salt, role, now_iso, now_iso))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": user_id,
        "name": name,
        "email": email,
        "role": role,
        "created_at": now_iso
    }


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticates a user against stored password hash.
    Returns user dict without sensitive fields on success, or None on failure.
    """
    email = (email or "").strip().lower()
    if not email or not password:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, email, password_hash, salt, role, created_at 
    FROM users 
    WHERE email = ? COLLATE NOCASE;
    """, (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    if not verify_password(password, row["password_hash"], row["salt"]):
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"]
    }


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by email (excluding password hash/salt)."""
    email = (email or "").strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, created_at FROM users WHERE email = ? COLLATE NOCASE;", (email,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by ID (excluding password hash/salt)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, created_at FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def create_session(user_id: int, duration_days: int = 7) -> str:
    """Generates a secure cryptographic session token and records it in the database."""
    session_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=duration_days)).isoformat()
    now_iso = now.isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_sessions (session_token, user_id, expires_at, created_at)
    VALUES (?, ?, ?, ?);
    """, (session_token, user_id, expires_at, now_iso))
    conn.commit()
    conn.close()

    return session_token


def get_user_by_session(session_token: str) -> Optional[Dict[str, Any]]:
    """
    Validates a session token and returns the authenticated user info.
    Automatically purges expired sessions.
    """
    if not session_token:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
    SELECT s.session_token, s.expires_at, u.id, u.name, u.email, u.role, u.created_at
    FROM user_sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.session_token = ?;
    """, (session_token,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    if row["expires_at"] < now_iso:
        # Session expired: clean up
        cursor.execute("DELETE FROM user_sessions WHERE session_token = ?;", (session_token,))
        conn.commit()
        conn.close()
        return None

    conn.close()
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
        "is_guest": False
    }


def revoke_session(session_token: str) -> bool:
    """Revokes and removes a session token."""
    if not session_token:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_sessions WHERE session_token = ?;", (session_token,))
    revoked = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return revoked


# Initialize database automatically on module import
init_db()
