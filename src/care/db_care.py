"""
Transify Care Database Layer.
Provides SQLite-based persistence for accessible healthcare intake, clinical RAG sources,
deterministic triage decisions, clinician reviews, and HIPAA/GDPR-aligned audit logging.
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "transify.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
    except Exception:
        pass
    return conn


def init_care_db():
    """Initializes Transify Care relational tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS care_patient_intakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        input_modality TEXT NOT NULL,
        raw_input TEXT,
        confirmed_text TEXT NOT NULL,
        chief_complaint TEXT NOT NULL,
        symptom_description TEXT NOT NULL,
        onset_duration TEXT,
        trajectory TEXT,
        severity INTEGER DEFAULT 1,
        medical_context TEXT,
        allergies_medications TEXT,
        consent_granted INTEGER DEFAULT 1,
        status TEXT NOT NULL,
        urgency_level TEXT NOT NULL,
        triage_explanation TEXT,
        triage_rule_id TEXT,
        evidence_citations TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS care_clinical_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        publisher TEXT NOT NULL,
        url TEXT,
        publication_date TEXT,
        version TEXT,
        document_type TEXT,
        licensing_status TEXT,
        checksum TEXT,
        status TEXT NOT NULL,
        reviewer TEXT,
        chunks_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS care_clinical_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        section_heading TEXT,
        content TEXT NOT NULL,
        keywords TEXT,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS care_clinician_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intake_id INTEGER NOT NULL,
        clinician_id TEXT NOT NULL,
        clinician_name TEXT NOT NULL,
        action TEXT NOT NULL,
        urgency_override TEXT,
        override_reason TEXT,
        clinical_notes TEXT,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS care_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        actor_role TEXT NOT NULL,
        target_id TEXT,
        details TEXT,
        prev_hash TEXT,
        entry_hash TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Safe migration for existing care_audit_logs tables
    cursor.execute("PRAGMA table_info(care_audit_logs);")
    audit_cols = [r["name"] for r in cursor.fetchall()]
    if "prev_hash" not in audit_cols:
        cursor.execute("ALTER TABLE care_audit_logs ADD COLUMN prev_hash TEXT;")
    if "entry_hash" not in audit_cols:
        cursor.execute("ALTER TABLE care_audit_logs ADD COLUMN entry_hash TEXT;")

    # Append-only enforcement via SQLite triggers
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS prevent_care_audit_logs_update
    BEFORE UPDATE ON care_audit_logs
    BEGIN
        SELECT RAISE(ABORT, 'care_audit_logs is append-only: UPDATE disallowed');
    END;
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS prevent_care_audit_logs_delete
    BEFORE DELETE ON care_audit_logs
    BEGIN
        SELECT RAISE(ABORT, 'care_audit_logs is append-only: DELETE disallowed');
    END;
    """)

    conn.commit()
    conn.close()


def log_care_audit(event_type: str, actor_id: str, actor_role: str, target_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    """
    Appends an entry to the auditable event log.
    Enforces tamper-evident cryptographic chaining (SHA-256) linked to the previous entry hash.
    Direct SQL UPDATE and DELETE operations are rejected by SQLite database triggers.
    Threat model note: protects against application-level modifications; host administrator with direct raw disk access could modify the SQLite file.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("SELECT entry_hash FROM care_audit_logs ORDER BY id DESC LIMIT 1;")
    prev_row = cursor.fetchone()
    prev_hash = prev_row["entry_hash"] if prev_row and prev_row["entry_hash"] else "GENESIS_AUDIT_HASH_BLOCK_0"

    details_str = json.dumps(details or {}, sort_keys=True)
    entry_payload = f"{prev_hash}:{event_type}:{actor_id}:{actor_role}:{target_id or ''}:{details_str}:{now_iso}"
    entry_hash = hashlib.sha256(entry_payload.encode("utf-8")).hexdigest()

    cursor.execute("""
    INSERT INTO care_audit_logs (event_type, actor_id, actor_role, target_id, details, prev_hash, entry_hash, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (event_type, actor_id, actor_role, target_id, details_str, prev_hash, entry_hash, now_iso))
    conn.commit()
    conn.close()


def create_intake(
    patient_id: str,
    input_modality: str,
    raw_input: str,
    confirmed_text: str,
    chief_complaint: str,
    symptom_description: str,
    onset_duration: str = "",
    trajectory: str = "stable",
    severity: int = 1,
    medical_context: str = "",
    allergies_medications: str = "",
    consent_granted: bool = True,
    status: str = "SUBMITTED",
    urgency_level: str = "UNKNOWN",
    triage_explanation: str = "",
    triage_rule_id: str = "",
    evidence_citations: Optional[List[Dict[str, Any]]] = None
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    citations_json = json.dumps(evidence_citations or [])

    cursor.execute("""
    INSERT INTO care_patient_intakes (
        patient_id, input_modality, raw_input, confirmed_text, chief_complaint,
        symptom_description, onset_duration, trajectory, severity, medical_context,
        allergies_medications, consent_granted, status, urgency_level,
        triage_explanation, triage_rule_id, evidence_citations, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        patient_id, input_modality, raw_input, confirmed_text, chief_complaint,
        symptom_description, onset_duration, trajectory, severity, medical_context,
        allergies_medications, 1 if consent_granted else 0, status, urgency_level,
        triage_explanation, triage_rule_id, citations_json, now_iso, now_iso
    ))
    intake_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log_care_audit("INTAKE_CREATED", patient_id, "PATIENT", str(intake_id), {"chief_complaint": chief_complaint, "modality": input_modality})
    return intake_id


def get_intake(intake_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM care_patient_intakes WHERE id = ?;", (intake_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["evidence_citations"] = json.loads(d.get("evidence_citations") or "[]")
    except Exception:
        d["evidence_citations"] = []
    return d


def list_intakes(patient_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM care_patient_intakes WHERE 1=1"
    params = []
    if patient_id:
        query += " AND patient_id = ?"
        params.append(patient_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["evidence_citations"] = json.loads(d.get("evidence_citations") or "[]")
        except Exception:
            d["evidence_citations"] = []
        results.append(d)
    return results


def update_intake_triage(intake_id: int, urgency_level: str, explanation: str, rule_id: str, citations: List[Dict[str, Any]], status: str = "SUBMITTED"):
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    UPDATE care_patient_intakes
    SET urgency_level = ?, triage_explanation = ?, triage_rule_id = ?, evidence_citations = ?, status = ?, updated_at = ?
    WHERE id = ?;
    """, (urgency_level, explanation, rule_id, json.dumps(citations), status, now_iso, intake_id))
    conn.commit()
    conn.close()
    log_care_audit("TRIAGE_UPDATED", "SYSTEM_TRIAGE", "SYSTEM", str(intake_id), {"urgency_level": urgency_level, "rule_id": rule_id})


def add_clinician_review(
    intake_id: int,
    clinician_id: str,
    clinician_name: str,
    action: str,
    urgency_override: Optional[str] = None,
    override_reason: Optional[str] = None,
    clinical_notes: str = ""
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT INTO care_clinician_reviews (
        intake_id, clinician_id, clinician_name, action, urgency_override, override_reason, clinical_notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (intake_id, clinician_id, clinician_name, action, urgency_override, override_reason, clinical_notes, now_iso))
    review_id = cursor.lastrowid

    # If action completes or overrides, update intake status
    new_status = "REVIEW_COMPLETED" if action in ("COMPLETED", "MODIFIED", "OVERRIDDEN") else "UNDER_REVIEW"
    update_query = "UPDATE care_patient_intakes SET status = ?, updated_at = ?"
    params = [new_status, now_iso]
    if urgency_override and urgency_override != "NONE":
        update_query += ", urgency_level = ?"
        params.append(urgency_override)
    update_query += " WHERE id = ?;"
    params.append(intake_id)

    cursor.execute(update_query, tuple(params))
    conn.commit()
    conn.close()

    log_care_audit("CLINICIAN_REVIEWED", clinician_id, "CLINICIAN", str(intake_id), {"action": action, "override": urgency_override})
    return review_id


def get_clinician_reviews(intake_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM care_clinician_reviews WHERE intake_id = ? ORDER BY id DESC;", (intake_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
