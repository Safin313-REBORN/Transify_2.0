"""
Database Access Layer for Transify.
Provides SQLite-based persistent storage for translation history, user feedback, and accessibility preferences.
"""

import os
import sqlite3
import json
import hashlib
import secrets
import hmac
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

try:
    import argon2
    _ARGON2_HASHER = argon2.PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16
    )
    HAS_ARGON2 = True
except ImportError:
    _ARGON2_HASHER = None
    HAS_ARGON2 = False

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "transify.db")


def is_production() -> bool:
    """
    Fail-safe check for production deployment environment.
    Evaluates RAILWAY_ENVIRONMENT, TRANSIFY_ENV, and ENVIRONMENT.
    """
    railway_env = (os.getenv("RAILWAY_ENVIRONMENT") or "").strip().lower()
    transify_env = (os.getenv("TRANSIFY_ENV") or "").strip().lower()
    general_env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    for val in (railway_env, transify_env, general_env):
        if val in ("production", "prod"):
            return True
    return False


def is_dev_clinician_enabled() -> bool:
    """
    Returns True only in non-production environments when development clinician mode is enabled.
    In production environments, always returns False.
    """
    if is_production():
        return False
    val = (os.getenv("TRANSIFY_DEV_CLINICIAN_ENABLED") or "true").strip().lower()
    return val in ("true", "1", "yes")


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


def init_db():
    """Initializes the database schema if tables do not exist."""
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
        consent_terms INTEGER DEFAULT 1,
        consented_at REAL,
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
    CREATE TABLE IF NOT EXISTS login_rate_limits (
        limit_key TEXT PRIMARY KEY,
        attempts INTEGER NOT NULL DEFAULT 1,
        first_attempt_at REAL NOT NULL,
        last_attempt_at REAL NOT NULL
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_key ON login_rate_limits(limit_key);")

    # Safe schema migration for translation_history if user_id missing
    cursor.execute("PRAGMA table_info(translation_history);")
    history_cols = [r["name"] for r in cursor.fetchall()]
    if "user_id" not in history_cols:
        cursor.execute("ALTER TABLE translation_history ADD COLUMN user_id INTEGER;")

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

    conn.commit()
    conn.close()


def log_translation(
    module: str,
    recognized_text: str,
    confidence: float,
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

    cursor.execute("""
    INSERT INTO translation_history 
    (module, input_meta, recognized_text, confidence, status, diagnostics, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (module, meta_json, recognized_text, float(confidence), status, diag_json, now_iso))

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


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def hash_password(password: str) -> tuple[str, str]:
    """
    Hashes a password using Argon2id (if available) or PBKDF2-HMAC-SHA256 with 600,000 iterations.
    Enforces a cryptographically secure salt.
    """
    if HAS_ARGON2 and _ARGON2_HASHER:
        pwd_hash = _ARGON2_HASHER.hash(password)
        return pwd_hash, "argon2id"
    else:
        salt = secrets.token_hex(16)
        pwd_bytes = password.encode("utf-8")
        salt_bytes = salt.encode("utf-8")
        pwd_hash = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 600_000).hex()
        return pwd_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Verifies a plain password against stored hash and salt in constant time.
    Supports Argon2id and PBKDF2 with constant-time comparison.
    """
    if not password or not password_hash:
        return False

    if password_hash.startswith("$argon2id$") or salt == "argon2id":
        if HAS_ARGON2 and _ARGON2_HASHER:
            try:
                return _ARGON2_HASHER.verify(password_hash, password)
            except Exception:
                return False
        return False

    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")

    computed_600k = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 600_000).hex()
    if hmac.compare_digest(password_hash, computed_600k):
        return True

    computed_100k = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100_000).hex()
    if hmac.compare_digest(password_hash, computed_100k):
        return True

    return False


def create_user(name: str, email: str, password: str, role: str = "user", consent_terms: bool = False) -> Dict[str, Any]:
    """
    Validates and registers a new user in the SQLite database with securely hashed credentials.
    Enforces a minimum password length of 15 characters without arbitrary character-composition rules.
    Requires explicit consent to Terms of Service and Privacy Policy.
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""

    if not name or len(name) < 2:
        raise ValueError("Name must be at least 2 characters long.")
    if not email or not EMAIL_REGEX.match(email):
        raise ValueError("A valid email address is required.")
    if not password or len(password) < 15:
        raise ValueError("Password must be at least 15 characters long.")
    if not consent_terms:
        raise ValueError("Consent to Terms of Service and Privacy Policy is required to create an account.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE;", (email,))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f"An account with email '{email}' already exists.")

    pwd_hash, salt = hash_password(password)
    now_iso = datetime.now(timezone.utc).isoformat()
    now_ts = datetime.now(timezone.utc).timestamp()

    cursor.execute("""
    INSERT INTO users (name, email, password_hash, salt, role, consent_terms, consented_at, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (name, email, pwd_hash, salt, role, 1 if consent_terms else 0, now_ts, now_iso, now_iso))

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
    Returns user dict on success, or None on failure.
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

    if not row:
        conn.close()
        return None

    if row["role"] == "disabled" or (row["email"].lower() == "demo@transify.ai" and is_production()):
        conn.close()
        return None

    if not verify_password(password, row["password_hash"], row["salt"]):
        conn.close()
        return None

    # Transparent hash upgrade to Argon2id if available
    if HAS_ARGON2 and not row["password_hash"].startswith("$argon2id$"):
        try:
            new_hash, new_salt = hash_password(password)
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("UPDATE users SET password_hash = ?, salt = ?, updated_at = ? WHERE id = ?;", (new_hash, new_salt, now_iso, row["id"]))
            conn.commit()
        except Exception:
            pass

    user_data = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"]
    }
    conn.close()
    return user_data


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by email."""
    if not email:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, created_at FROM users WHERE email = ? COLLATE NOCASE;", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by integer ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, created_at FROM users WHERE id = ?;", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_user_account(user_id: int) -> bool:
    """Deletes a user account and associated sessions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def create_session(user_id: int, duration_days: int = 30) -> str:
    """
    Generates a high-entropy session token (256 bits).
    Stores ONLY the SHA-256 hash of the session token in the database.
    Returns the raw session token to be delivered solely via HttpOnly cookie or Authorization header.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=duration_days)).isoformat()
    now_iso = now.isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO user_sessions (session_token, user_id, expires_at, created_at)
    VALUES (?, ?, ?, ?);
    """, (token_hash, user_id, expires_at, now_iso))
    conn.commit()
    conn.close()

    return raw_token


def get_user_by_session(raw_token: str) -> Optional[Dict[str, Any]]:
    """
    Validates a session by computing the SHA-256 hash of raw_token and querying user_sessions.
    Automatically purges expired sessions.
    """
    if not raw_token:
        return None

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
    SELECT s.session_token, s.expires_at, u.id, u.name, u.email, u.role, u.created_at
    FROM user_sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.session_token = ?;
    """, (token_hash,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    if row["expires_at"] < now_iso:
        cursor.execute("DELETE FROM user_sessions WHERE session_token = ?;", (token_hash,))
        conn.commit()
        conn.close()
        return None

    conn.close()
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"]
    }


def revoke_session(raw_token: str) -> bool:
    """Revokes a session by hashing the raw token and deleting from user_sessions."""
    if not raw_token:
        return False
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_sessions WHERE session_token = ?;", (token_hash,))
    revoked = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return revoked


def revoke_all_sessions(user_id: Optional[int] = None) -> int:
    """Revokes all active sessions for a user, or all sessions repository-wide."""
    conn = get_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("DELETE FROM user_sessions WHERE user_id = ?;", (user_id,))
    else:
        cursor.execute("DELETE FROM user_sessions;")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def record_failed_login(key: str, window_seconds: float = 300.0) -> int:
    """Records a failed login attempt for brute-force rate-limiting."""
    conn = get_connection()
    cursor = conn.cursor()
    now_ts = datetime.now(timezone.utc).timestamp()

    cursor.execute("SELECT attempts, first_attempt_at FROM login_rate_limits WHERE limit_key = ?;", (key,))
    row = cursor.fetchone()

    if not row or (now_ts - row["first_attempt_at"]) > window_seconds:
        cursor.execute("""
        INSERT OR REPLACE INTO login_rate_limits (limit_key, attempts, first_attempt_at, last_attempt_at)
        VALUES (?, 1, ?, ?);
        """, (key, now_ts, now_ts))
        attempts = 1
    else:
        attempts = row["attempts"] + 1
        cursor.execute("""
        UPDATE login_rate_limits 
        SET attempts = ?, last_attempt_at = ? 
        WHERE limit_key = ?;
        """, (attempts, now_ts, key))

    conn.commit()
    conn.close()
    return attempts


def is_login_rate_limited(key: str, max_attempts: int = 5, window_seconds: float = 300.0) -> bool:
    """Checks whether an IP or account key is currently rate-limited."""
    conn = get_connection()
    cursor = conn.cursor()
    now_ts = datetime.now(timezone.utc).timestamp()
    cursor.execute("SELECT attempts, first_attempt_at FROM login_rate_limits WHERE limit_key = ?;", (key,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False
    if (now_ts - row["first_attempt_at"]) > window_seconds:
        return False
    return row["attempts"] >= max_attempts


def clear_failed_logins(key: str):
    """Clears failed login attempts upon successful authentication."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM login_rate_limits WHERE limit_key = ?;", (key,))
    conn.commit()
    conn.close()


# Initialize database automatically on module import
init_db()
