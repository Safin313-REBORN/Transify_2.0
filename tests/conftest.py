"""
Pytest Fixtures and Environment Isolation for Transify V3 Test Suite.
Enforces strict test data isolation:
- Sets TRANSIFY_DB_PATH to an isolated temporary SQLite database in /tmp.
- Never writes test records to data/transify.db.
- Preserves the production database checksum invariant.
"""

import os
import sys

# CRITICAL: Must be set BEFORE importing any application modules
TEST_DB_PATH = "/tmp/isolated_test_transify.db"
os.environ["TRANSIFY_DB_PATH"] = TEST_DB_PATH

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# If old test db exists, remove it
for suffix in ["", "-wal", "-shm"]:
    p = f"{TEST_DB_PATH}{suffix}"
    if os.path.exists(p):
        try:
            os.remove(p)
        except OSError:
            pass

from src.database.db import init_db, create_user
from src.care.db_care import init_care_db
from src.care.clinical_rag import seed_clinical_sources_if_empty

init_db()
init_care_db()
seed_clinical_sources_if_empty(force_reseed=True)

# Seed required baseline test fixtures in the isolated test database
create_user("Dr. Clinician", "clinician@transify.ai", "SecurePassword2026!#", role="clinician", consent_terms=True)
create_user("Standard Patient", "patient@transify.ai", "SecurePassword2026!#", role="user", consent_terms=True)
create_user("Dev Clinician", "dev.clinician@transify.ai", "SecurePassword2026!#", role="dev_clinician", consent_terms=True)

import pytest

@pytest.fixture(scope="session", autouse=True)
def isolate_test_database():
    """Ensure all tests run against an isolated temporary database."""
    chatbot_model_path = "data/chatbot_trained_model.json"
    backup_chatbot = None
    if os.path.exists(chatbot_model_path):
        with open(chatbot_model_path, "rb") as f:
            backup_chatbot = f.read()

    yield

    # Clean up test database
    for suffix in ["", "-wal", "-shm"]:
        p = f"{TEST_DB_PATH}{suffix}"
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    # Restore chatbot model file
    if backup_chatbot is not None and os.path.exists(chatbot_model_path):
        with open(chatbot_model_path, "wb") as f:
            f.write(backup_chatbot)
