"""
Database Access Layer for Transify.
Provides SQLite-based persistent storage for translation history, user feedback, and accessibility preferences.
"""

import os
import sqlite3
import json
from datetime import datetime, timezone
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


# Initialize database automatically on module import
init_db()
