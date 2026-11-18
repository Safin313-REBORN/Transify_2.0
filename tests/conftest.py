"""
pytest session configuration for Transify test suite.
Provides isolated temporary database and data directory to ensure
production or default databases (e.g. data/transify.db) are never modified.
"""

import os
import shutil
import tempfile
import pytest

_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="transify_test_db_")
_TEST_DB_PATH = os.path.join(_TEST_TEMP_DIR, "test_transify.db")

# Set environment before any tests import src.database.db or src.api.server
os.environ["TRANSIFY_DATA_DIR"] = _TEST_TEMP_DIR
os.environ["TRANSIFY_DB_PATH"] = _TEST_DB_PATH
os.environ["TRANSIFY_ENV"] = "testing"

from src.database.db import init_db

init_db()


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    """Ensure test database is isolated and clean up after test session."""
    yield _TEST_DB_PATH
    try:
        shutil.rmtree(_TEST_TEMP_DIR, ignore_errors=True)
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    try:
        shutil.rmtree(_TEST_TEMP_DIR, ignore_errors=True)
    except Exception:
        pass
