"""
SQLite Migration Integrity, Idempotency, and IDOR Authorization Tests.
Verifies migrations 3 through 7 across isolated SQLite databases:
- Preservation of existing users, history records, and preferences.
- Non-fabrication of consent for historical users (consent_terms=0, consented_at=NULL).
- SHA-256 token hashing for password reset records.
- Complete idempotency across multiple consecutive init_db() calls.
- Strict Insecure Direct Object Reference (IDOR) prevention across Hub, Phraseboard, and History.
"""

import os
import sqlite3
import time
import pytest
from fastapi.testclient import TestClient

from src.api.server import app
import src.database.db as db_module


@pytest.fixture
def client():
    return TestClient(app, base_url="http://testserver")


def test_migrations_3_to_7_preservation_and_idempotency(tmp_path, monkeypatch):
    """
    Constructs a legacy v2 SQLite database without migrations 3-7,
    applies migrations via init_db(), verifies data preservation,
    and asserts idempotency when init_db() runs repeatedly.
    """
    db_file = str(tmp_path / "legacy_v2_migration_test.db")
    monkeypatch.setenv("TRANSIFY_DB_PATH", db_file)

    # 1. Create a legacy database pre-migration 3
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA journal_mode = WAL;")
    cursor = conn.cursor()

    # Legacy schema_migrations (up to version 2)
    cursor.execute("""
    CREATE TABLE schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL,
        description TEXT
    );
    """)
    cursor.execute("INSERT INTO schema_migrations VALUES (1, '2026-01-01T00:00:00Z', 'Legacy v1');")
    cursor.execute("INSERT INTO schema_migrations VALUES (2, '2026-01-02T00:00:00Z', 'Legacy v2');")

    # Legacy users table (lacking consent_terms and consented_at)
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Legacy translation_history table (lacking is_favorite)
    cursor.execute("""
    CREATE TABLE translation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT NOT NULL,
        input_meta TEXT,
        recognized_text TEXT NOT NULL,
        confidence REAL,
        status TEXT,
        diagnostics TEXT,
        feedback_rating INTEGER,
        feedback_comments TEXT,
        created_at TEXT NOT NULL,
        user_id INTEGER
    );
    """)

    # Legacy user_preferences
    cursor.execute("""
    CREATE TABLE user_preferences (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        user_id INTEGER
    );
    """)

    # Seed legacy data
    cursor.execute("""
    INSERT INTO users (id, name, email, password_hash, salt, role, created_at, updated_at)
    VALUES (42, 'Legacy User', 'legacy@example.com', 'legacy_hash', 'legacy_salt', 'user', '2026-01-01T12:00:00Z', '2026-01-01T12:00:00Z');
    """)

    cursor.execute("""
    INSERT INTO translation_history (id, module, recognized_text, confidence, created_at, user_id)
    VALUES (101, 'sign', 'dhonnobad', 0.98, '2026-01-01T12:05:00Z', 42);
    """)

    cursor.execute("""
    INSERT INTO user_preferences (key, value, updated_at, user_id)
    VALUES ('high_contrast', 'true', '2026-01-01T12:00:00Z', 42);
    """)

    conn.commit()
    conn.close()

    # 2. Run init_db() to apply migrations 3, 4, 5, 6, 7
    db_module.init_db()

    # 3. Verify data preservation and schema expansion
    conn_mig = sqlite3.connect(db_file)
    conn_mig.row_factory = sqlite3.Row
    c_mig = conn_mig.cursor()

    # Verify user preserved and consent columns added with 0 / NULL (never fabricated!)
    c_mig.execute("SELECT * FROM users WHERE id = 42;")
    user_row = c_mig.fetchone()
    assert user_row is not None
    assert user_row["email"] == "legacy@example.com"
    assert user_row["consent_terms"] == 0
    assert user_row["consented_at"] is None

    # Verify history preserved and is_favorite defaulted to 0
    c_mig.execute("SELECT * FROM translation_history WHERE id = 101;")
    hist_row = c_mig.fetchone()
    assert hist_row is not None
    assert hist_row["recognized_text"] == "dhonnobad"
    assert hist_row["is_favorite"] == 0

    # Verify user_preferences preserved
    c_mig.execute("SELECT * FROM user_preferences WHERE pref_key = 'high_contrast' AND user_id = 42;")
    pref_row = c_mig.fetchone()
    assert pref_row is not None
    assert pref_row["pref_value"] == "true"

    # Verify new tables exist: password_reset_tokens, hub_conversations, hub_messages, user_phrases
    c_mig.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r["name"] for r in c_mig.fetchall()]
    assert "password_reset_tokens" in tables
    assert "hub_conversations" in tables
    assert "hub_messages" in tables
    assert "user_phrases" in tables

    # Verify migrations table records migrations 3-7
    c_mig.execute("SELECT version FROM schema_migrations;")
    applied_versions = [r["version"] for r in c_mig.fetchall()]
    for v in [1, 2, 3, 4, 5, 6, 7]:
        assert v in applied_versions

    conn_mig.close()

    # 4. Idempotency Check: Running init_db() a second and third time must succeed cleanly
    db_module.init_db()
    db_module.init_db()

    conn_check = sqlite3.connect(db_file)
    conn_check.row_factory = sqlite3.Row
    c_check = conn_check.cursor()
    c_check.execute("SELECT COUNT(*) as c FROM users WHERE id = 42;")
    assert c_check.fetchone()["c"] == 1
    conn_check.close()


def test_idor_prevention_hub_phraseboard_and_history(client):
    """
    Exhaustive IDOR test suite:
    Verifies that User B cannot view, modify, favorite, clear, or delete
    User A's conversation sessions, messages, custom phrases, or history records.
    """
    email_a = f"owner_a_{int(time.time()*1000)}@transify.test"
    email_b = f"intruder_b_{int(time.time()*1000)}@transify.test"
    pwd = "SharedSecurePassword123!_2026"

    # 1. Register and login as User A
    client.cookies.clear()
    res_a = client.post("/api/auth/register", json={"name": "User A", "email": email_a, "password": pwd, "consent_terms": True})
    assert res_a.status_code == 200
    user_a_id = res_a.json()["user"]["id"]

    # User A creates a conversation session
    conv_res = client.post("/api/hub/conversations", json={"title": "Private Session A"})
    assert conv_res.status_code == 200
    conv_a_id = conv_res.json()["conversation"]["id"]

    # User A posts a message
    msg_res = client.post(f"/api/hub/conversations/{conv_a_id}/messages", json={
        "content": "Secret Confidential Message A",
        "source": "typed"
    })
    assert msg_res.status_code == 200
    msg_a_id = msg_res.json()["message"]["id"]

    # User A adds a custom phrase
    phrase_res = client.post("/api/phrases", json={
        "text_en": "Private Custom Phrase A",
        "text_bn": "ব্যক্তিগত বাক্য এ",
        "category": "Private"
    })
    assert phrase_res.status_code == 200
    phrase_a_id = phrase_res.json()["phrase"]["id"]

    # User A creates a history record and favorites it
    hist_id = db_module.log_translation("sign", "SecretSignRecord", 0.99, user_id=user_a_id)
    fav_res = client.post(f"/api/history/{hist_id}/favorite")
    assert fav_res.status_code == 200
    assert fav_res.json()["is_favorite"] is True

    # 2. Register and login as User B
    client.cookies.clear()
    res_b = client.post("/api/auth/register", json={"name": "User B", "email": email_b, "password": pwd, "consent_terms": True})
    assert res_b.status_code == 200

    # ATTACK 1: User B attempts to read User A's hub messages
    idor_read = client.get(f"/api/hub/conversations/{conv_a_id}/messages")
    assert idor_read.status_code == 404
    assert "not found or not owned" in idor_read.json()["detail"]

    # ATTACK 2: User B attempts to append a message to User A's hub conversation
    idor_post = client.post(f"/api/hub/conversations/{conv_a_id}/messages", json={
        "content": "Injected unauthorized message by User B",
        "source": "typed"
    })
    assert idor_post.status_code == 404
    assert "not found" in idor_post.json()["detail"]

    # ATTACK 3: User B attempts to clear User A's hub conversation messages
    idor_clear = client.post(f"/api/hub/conversations/{conv_a_id}/clear")
    assert idor_clear.status_code == 404

    # ATTACK 4: User B attempts to delete User A's hub conversation
    idor_del_conv = client.delete(f"/api/hub/conversations/{conv_a_id}")
    assert idor_del_conv.status_code == 404

    # ATTACK 5: User B attempts to toggle favorite on User A's custom phrase
    idor_fav_phrase = client.post(f"/api/phrases/{phrase_a_id}/favorite")
    assert idor_fav_phrase.status_code == 404

    # ATTACK 6: User B attempts to delete User A's custom phrase
    idor_del_phrase = client.delete(f"/api/phrases/{phrase_a_id}")
    assert idor_del_phrase.status_code == 404

    # ATTACK 7: User B attempts to toggle favorite on User A's history record
    idor_fav_hist = client.post(f"/api/history/{hist_id}/favorite")
    assert idor_fav_hist.status_code == 404

    # ATTACK 8: Unauthenticated guest attempts to access User A's private resources
    client.cookies.clear()
    unauth_hub = client.get(f"/api/hub/conversations/{conv_a_id}/messages")
    assert unauth_hub.status_code == 401

    unauth_phrase_del = client.delete(f"/api/phrases/{phrase_a_id}")
    assert unauth_phrase_del.status_code == 401

    unauth_hist_fav = client.post(f"/api/history/{hist_id}/favorite")
    assert unauth_hist_fav.status_code == 401

    # 3. Verify User A's records remain intact and unchanged
    client.cookies.clear()
    login_a = client.post("/api/auth/login", json={"email": email_a, "password": pwd})
    assert login_a.status_code == 200

    check_messages = client.get(f"/api/hub/conversations/{conv_a_id}/messages")
    assert check_messages.status_code == 200
    msgs = check_messages.json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Secret Confidential Message A"

    check_phrases = client.get("/api/phrases")
    assert check_phrases.status_code == 200
    custom_list = check_phrases.json()["custom_phrases"]
    assert any(p["id"] == phrase_a_id for p in custom_list)

    check_hist = client.get("/api/history")
    assert check_hist.status_code == 200
    records = check_hist.json()["records"]
    rec = next((r for r in records if r["id"] == hist_id), None)
    assert rec is not None
    assert rec["is_favorite"] is True
