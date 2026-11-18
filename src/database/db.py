"""
Database Access Layer for Transify.
Provides SQLite-based persistent storage for translation history, user feedback,
accessibility preferences, and secure user authentication with Argon2id / PBKDF2 hashing.
"""

import os
import sqlite3
import json
import re
import secrets
import hashlib
import hmac
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger("transify.db")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_DIR = os.getenv("TRANSIFY_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
DB_PATH = os.getenv("TRANSIFY_DB_PATH", os.path.join(DB_DIR, "transify.db"))

# --- Argon2id Password Hasher Setup ---
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, InvalidHashError
    _ARGON2_HASHER = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)
    HAS_ARGON2 = True
except ImportError:
    _ARGON2_HASHER = None
    HAS_ARGON2 = False


def is_production() -> bool:
    """
    Fail-safe check for production deployment environment.
    Evaluates RAILWAY_ENVIRONMENT, TRANSIFY_ENV, and ENVIRONMENT.
    Normalizes values using whitespace trimming and lowercase conversion.

    Precedence & Safety Rules:
    1. If any authoritative variable explicitly indicates production, production mode is enabled.
    2. RAILWAY_ENVIRONMENT=production must never be overridden by TRANSIFY_ENV=testing.
    3. If production and development indicators conflict, fail closed by enforcing production
       security settings and logging a prominent configuration warning.
    4. If no production indicator exists and the environment explicitly identifies testing/development,
       returns False so that local and CI testing function normally.
    5. Returns False if all environment variables are unset.
    """
    prod_indicators = []
    dev_indicators = []

    for var in ("RAILWAY_ENVIRONMENT", "TRANSIFY_ENV", "ENVIRONMENT"):
        raw = os.getenv(var)
        if raw is None:
            continue
        val = raw.strip().lower()
        if not val:
            continue
        if val in ("production", "prod"):
            prod_indicators.append((var, val))
        elif val in ("test", "testing", "development", "dev", "local", "staging"):
            dev_indicators.append((var, val))

    # Any authoritative production indicator triggers production mode (fail closed on conflict)
    if prod_indicators:
        if dev_indicators:
            logger.warning(
                f"[SECURITY FAIL-CLOSED] Conflicting environment variables detected! "
                f"Production indicators: {prod_indicators}; Development indicators: {dev_indicators}. "
                f"Enforcing strict production security settings."
            )
        return True

    # If no production indicator exists, testing/dev indicators return False
    if dev_indicators:
        return False

    return False


def get_db_path() -> str:
    """Resolves database path dynamically from environment or falls back to project default."""
    db_dir = os.getenv("TRANSIFY_DATA_DIR", DB_DIR)
    return os.getenv("TRANSIFY_DB_PATH", os.path.join(db_dir, "transify.db"))


def get_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database with WAL mode and busy timeout."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0)
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
    data_dir = os.getenv("TRANSIFY_DATA_DIR", DB_DIR)
    if os.path.isdir(seed_dir) and os.path.abspath(seed_dir) != os.path.abspath(data_dir):
        try:
            import shutil
            for item in os.listdir(seed_dir):
                if item == "transify.db" or item.endswith(".db"):
                    continue
                s_item = os.path.join(seed_dir, item)
                d_item = os.path.join(data_dir, item)
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
    """Initializes and migrates the database schema safely while preserving existing data."""
    seed_data_if_needed()
    conn = get_connection()
    cursor = conn.cursor()

    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL,
        description TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS translation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
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
        pref_key TEXT NOT NULL,
        user_id INTEGER DEFAULT 0,
        pref_value TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (pref_key, user_id)
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

    # Safe Schema Migrations for existing tables
    # 1. Add user_id column to translation_history if missing
    cursor.execute("PRAGMA table_info(translation_history);")
    history_cols = [r["name"] for r in cursor.fetchall()]
    if "user_id" not in history_cols:
        cursor.execute("ALTER TABLE translation_history ADD COLUMN user_id INTEGER;")
        logger.info("Migrated translation_history: added user_id column.")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user_id ON translation_history(user_id);")

    # 2. Transactional Table Rebuild for user_preferences composite primary key (pref_key, user_id)
    cursor.execute("PRAGMA table_info(user_preferences);")
    pref_info = cursor.fetchall()
    pref_cols = {r["name"]: r for r in pref_info}
    user_id_is_pk = "user_id" in pref_cols and pref_cols["user_id"]["pk"] > 0

    if not user_id_is_pk:
        logger.info("Rebuilding user_preferences table with composite primary key (pref_key, user_id)...")
        cursor.execute("""
        CREATE TABLE user_preferences_migrated (
            pref_key TEXT NOT NULL,
            user_id INTEGER NOT NULL DEFAULT 0,
            pref_value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (pref_key, user_id)
        );
        """)
        if "user_id" in pref_cols:
            cursor.execute("""
            INSERT OR REPLACE INTO user_preferences_migrated (pref_key, user_id, pref_value, updated_at)
            SELECT pref_key, COALESCE(user_id, 0), pref_value, updated_at FROM user_preferences;
            """)
        else:
            cursor.execute("""
            INSERT OR REPLACE INTO user_preferences_migrated (pref_key, user_id, pref_value, updated_at)
            SELECT pref_key, 0, pref_value, updated_at FROM user_preferences;
            """)
        cursor.execute("DROP TABLE user_preferences;")
        cursor.execute("ALTER TABLE user_preferences_migrated RENAME TO user_preferences;")
        cursor.execute("""
        INSERT OR REPLACE INTO schema_migrations (version, applied_at, description)
        VALUES (2, ?, 'Composite PK (pref_key, user_id) for user_preferences');
        """, (now_iso,))
        logger.info("Rebuilt user_preferences with composite primary key.")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prefs_user_id ON user_preferences(user_id);")

    # 3. Populate default preferences (user_id = 0 for system defaults)
    defaults = {
        "theme": "light",
        "font_size": "medium",
        "tts_speed": "1.0",
        "tts_auto_play": "false",
        "reduce_motion": "false",
        "screen_reader_optimizations": "true"
    }

    for k, v in defaults.items():
        cursor.execute("""
        INSERT OR IGNORE INTO user_preferences (pref_key, user_id, pref_value, updated_at)
        VALUES (?, 0, ?, ?);
        """, (k, v, now_iso))

    # 4. Versioned Migration 1: Revoke legacy plaintext sessions once only
    cursor.execute("SELECT 1 FROM schema_migrations WHERE version = 1;")
    if not cursor.fetchone():
        cursor.execute("DELETE FROM user_sessions;")
        cursor.execute("""
        INSERT INTO schema_migrations (version, applied_at, description)
        VALUES (1, ?, 'Revoke legacy plaintext sessions prior to token hashing');
        """, (now_iso,))
        logger.info("Applied migration 1: revoked legacy plaintext sessions.")
    else:
        # On normal startup, ONLY prune expired sessions, preserving active valid sessions
        cursor.execute("DELETE FROM user_sessions WHERE expires_at < ?;", (now_iso,))

    # 5. Production & Demo Hardening: Ensure demo account cannot authenticate
    cursor.execute("UPDATE users SET role = 'disabled' WHERE email = 'demo@transify.ai' COLLATE NOCASE;")
    cursor.execute("""
    DELETE FROM user_sessions WHERE user_id IN (
        SELECT id FROM users WHERE email = 'demo@transify.ai' COLLATE NOCASE
    );
    """)

    conn.commit()
    conn.close()


# --- Translation History Isolation ---

def log_translation(
    module: str,
    recognized_text: str,
    confidence: Optional[float] = None,
    status: str = "SUCCESS",
    input_meta: Optional[Dict[str, Any]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None
) -> int:
    """Logs a translation event associated with an optional user_id."""
    conn = get_connection()
    cursor = conn.cursor()

    now_iso = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(input_meta or {})
    diag_json = json.dumps(diagnostics or {})
    conf_val = float(confidence) if (confidence is not None and not (isinstance(confidence, float) and (confidence != confidence))) else None

    cursor.execute("""
    INSERT INTO translation_history 
    (user_id, module, input_meta, recognized_text, confidence, status, diagnostics, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (user_id, module, meta_json, recognized_text, conf_val, status, diag_json, now_iso))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_history(limit: int = 50, module: Optional[str] = None, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves recent translation history records.
    If user_id is provided, only that user's records are returned.
    If user_id is None, retrieves records matching module/limit (for internal/admin queries).
    """
    conn = get_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)

    if module:
        conditions.append("module = ?")
        params.append(module)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM translation_history {where_clause} ORDER BY id DESC LIMIT ?;"
    params.append(limit)

    cursor.execute(query, tuple(params))

    rows = cursor.fetchall()
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "user_id": r["user_id"],
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


def count_legacy_history() -> int:
    """Returns the total number of legacy translation history records where user_id IS NULL."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM translation_history WHERE user_id IS NULL;")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def clear_history(user_id: Optional[int] = None, preserve_legacy: bool = True) -> int:
    """
    Clears translation history records strictly for the requesting authenticated user (or all if user_id is None).
    Preserves legacy rows where user_id IS NULL unless preserve_legacy is explicitly False.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("DELETE FROM translation_history WHERE user_id = ?;", (user_id,))
    else:
        if preserve_legacy:
            cursor.execute("DELETE FROM translation_history WHERE user_id IS NOT NULL;")
        else:
            cursor.execute("DELETE FROM translation_history;")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def delete_history_record(record_id: int, user_id: int) -> bool:
    """Deletes a specific history record if owned by the requesting user."""
    if not record_id or not user_id:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM translation_history WHERE id = ? AND user_id = ?;", (record_id, user_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def record_feedback(record_id: int, rating: int, comments: Optional[str] = None, user_id: Optional[int] = None) -> bool:
    """Records user feedback on a translation event owned by user_id."""
    conn = get_connection()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("""
        UPDATE translation_history 
        SET feedback_rating = ?, feedback_comments = ?
        WHERE id = ? AND user_id = ?;
        """, (rating, comments, record_id, user_id))
    else:
        cursor.execute("""
        UPDATE translation_history 
        SET feedback_rating = ?, feedback_comments = ?
        WHERE id = ?;
        """, (rating, comments, record_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# --- Preferences Isolation ---

def get_preferences(user_id: Optional[int] = None) -> Dict[str, str]:
    """Retrieves preferences for the specified user or system defaults."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # First load system defaults (user_id = 0)
    cursor.execute("SELECT pref_key, pref_value FROM user_preferences WHERE user_id = 0 OR user_id IS NULL;")
    prefs = {r["pref_key"]: r["pref_value"] for r in cursor.fetchall()}

    # Overlay user-specific preferences if authenticated
    if user_id:
        cursor.execute("SELECT pref_key, pref_value FROM user_preferences WHERE user_id = ?;", (user_id,))
        for r in cursor.fetchall():
            prefs[r["pref_key"]] = r["pref_value"]

    conn.close()
    return prefs


def update_preference(key: str, value: str, user_id: Optional[int] = None) -> bool:
    """Updates a preference for the user (or default user_id=0) using atomic UPSERT on composite PK."""
    uid = user_id if user_id is not None else 0
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        cursor.execute("""
        INSERT INTO user_preferences (pref_key, user_id, pref_value, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(pref_key, user_id) DO UPDATE SET pref_value = excluded.pref_value, updated_at = excluded.updated_at;
        """, (key, uid, str(value), now_iso))
        conn.commit()
    finally:
        conn.close()
    return True


# --- Password Hashing & Verification (Argon2id + 600k PBKDF2 Fallback) ---

def hash_password(password: str) -> tuple[str, str]:
    """
    Hashes a password using Argon2id (if available) or PBKDF2-HMAC-SHA256 with 600,000 iterations.
    Enforces a cryptographically secure salt and modern parameters.
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
    Supports Argon2id, PBKDF2 600k, and legacy PBKDF2 100k for seamless zero-downtime migration.
    """
    if not password or not password_hash:
        return False

    # Check Argon2id hash
    if password_hash.startswith("$argon2id$") or salt == "argon2id":
        if HAS_ARGON2 and _ARGON2_HASHER:
            try:
                return _ARGON2_HASHER.verify(password_hash, password)
            except Exception:
                return False
        return False

    # PBKDF2 check in constant time
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")

    # Try modern 600k iterations
    computed_600k = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 600_000).hex()
    if hmac.compare_digest(password_hash, computed_600k):
        return True

    # Try legacy 100k iterations for seamless upgrade
    computed_100k = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100_000).hex()
    if hmac.compare_digest(password_hash, computed_100k):
        return True

    return False


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def create_user(name: str, email: str, password: str, role: str = "user") -> Dict[str, Any]:
    """
    Validates and registers a new user in the SQLite database with securely hashed credentials.
    Enforces a minimum password length of 15 characters without arbitrary character-composition rules.
    Raises ValueError on invalid input or duplicate email.
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

    conn = get_connection()
    cursor = conn.cursor()

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
    Transparently upgrades legacy PBKDF2 hashes to Argon2id on successful login.
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

    # Transparent hash upgrade: If user has a legacy PBKDF2 hash, upgrade to Argon2id
    if HAS_ARGON2 and not row["password_hash"].startswith("$argon2id$"):
        try:
            new_hash, new_salt = hash_password(password)
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
            UPDATE users SET password_hash = ?, salt = ?, updated_at = ?
            WHERE id = ?;
            """, (new_hash, new_salt, now_iso, row["id"]))
            conn.commit()
            logger.info(f"Transparently upgraded password hash to Argon2id for user {row['id']}.")
        except Exception as ex:
            logger.warning(f"Password rehash update failed: {ex}")

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


# --- Cryptographic Token Hash Session Management ---

def create_session(user_id: int, duration_days: int = 30) -> str:
    """
    Generates a high-entropy session token (256 bits).
    Stores ONLY the SHA-256 hash of the session token in the database.
    Never stores the raw session token in SQLite.
    Returns the raw session token to be delivered solely via HttpOnly cookie.
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
        "created_at": row["created_at"],
        "is_guest": False
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


# --- Persistent SQLite-Backed Login Rate Limiting (Concurrency Safe) ---

def record_failed_login(key: str, window_seconds: float = 300.0) -> int:
    """
    Atomically records a failed login attempt for a key (IP or normalized email).
    Uses SQLite BEGIN IMMEDIATE transaction with WAL mode and busy timeout
    to guarantee atomic increments without lost updates under high concurrency.

    Rate Limiting Policy:
    Fixed-window policy of 5 failed attempts within 300 seconds (5 minutes)
    anchored at `first_attempt_at`. Once `now - first_attempt_at >= window_seconds`,
    the attempt counter automatically resets to 1.

    Returns the current number of failed attempts within the active fixed window.
    """
    conn = get_connection()
    now = datetime.now(timezone.utc).timestamp()
    
    try:
        conn.execute("BEGIN IMMEDIATE;")
        cursor = conn.cursor()
        cursor.execute("SELECT attempts, first_attempt_at FROM login_rate_limits WHERE limit_key = ?;", (key,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("""
            INSERT INTO login_rate_limits (limit_key, attempts, first_attempt_at, last_attempt_at)
            VALUES (?, 1, ?, ?);
            """, (key, now, now))
            attempts = 1
        else:
            first_at = float(row["first_attempt_at"])
            if (now - first_at) >= window_seconds:
                cursor.execute("""
                UPDATE login_rate_limits 
                SET attempts = 1, first_attempt_at = ?, last_attempt_at = ?
                WHERE limit_key = ?;
                """, (now, now, key))
                attempts = 1
            else:
                cursor.execute("""
                UPDATE login_rate_limits 
                SET attempts = attempts + 1, last_attempt_at = ?
                WHERE limit_key = ?;
                """, (now, key))
                attempts = int(row["attempts"]) + 1

        # Prune expired rate-limit rows (> 1 hour old) to keep table lightweight
        cursor.execute("DELETE FROM login_rate_limits WHERE (? - last_attempt_at) > 3600;", (now,))

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return attempts


def is_login_rate_limited(key: str, max_attempts: int = 5, window_seconds: float = 300.0) -> bool:
    """
    Checks if a key (IP or normalized email) currently exceeds the maximum allowed failed attempts.
    Evaluates against the fixed window of `window_seconds` (default 300s / 5 minutes)
    anchored at `first_attempt_at`. Returns True if attempts >= max_attempts within the window.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).timestamp()
    try:
        cursor.execute("SELECT attempts, first_attempt_at FROM login_rate_limits WHERE limit_key = ?;", (key,))
        row = cursor.fetchone()
        if not row:
            return False
        if (now - float(row["first_attempt_at"])) >= window_seconds:
            return False
        return int(row["attempts"]) >= max_attempts
    finally:
        conn.close()


def clear_failed_logins(key: str):
    """
    Clears failed login attempts strictly for the specified key (e.g. email:user@transify.ai).
    Never inadvertently clears shared IP rate limiters, ensuring network-level brute-force
    protection remains active even after an individual user logs in successfully.
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("DELETE FROM login_rate_limits WHERE limit_key = ?;", (key,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Initialize database automatically on module import
init_db()
