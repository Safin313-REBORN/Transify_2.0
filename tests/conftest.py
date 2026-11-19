"""
pytest session configuration for Transify test suite.
Provides isolated temporary database and data directory to ensure
production or default databases (e.g. data/transify.db) are never modified.
"""

import os
import shutil
import tempfile
import socket
import threading
import time
import pytest
import uvicorn
from playwright.sync_api import sync_playwright

_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="transify_test_db_")
_TEST_DB_PATH = os.path.join(_TEST_TEMP_DIR, "test_transify.db")

# Set environment before any tests import src.database.db or src.api.server
os.environ["TRANSIFY_DATA_DIR"] = _TEST_TEMP_DIR
os.environ["TRANSIFY_DB_PATH"] = _TEST_DB_PATH
os.environ["TRANSIFY_ENV"] = "testing"

from src.database.db import init_db
from src.api.email_service import set_email_adapter, MockMailAdapter

init_db()

_DEFAULT_MOCK_ADAPTER = MockMailAdapter(configured=True)
set_email_adapter(_DEFAULT_MOCK_ADAPTER)


@pytest.fixture(autouse=True)
def reset_mock_mail():
    """Clears sent emails and errors before each test."""
    _DEFAULT_MOCK_ADAPTER.clear()
    _DEFAULT_MOCK_ADAPTER.set_configured(True)
    set_email_adapter(_DEFAULT_MOCK_ADAPTER)
    yield _DEFAULT_MOCK_ADAPTER
    _DEFAULT_MOCK_ADAPTER.clear()
    _DEFAULT_MOCK_ADAPTER.set_configured(True)
    set_email_adapter(_DEFAULT_MOCK_ADAPTER)


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


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    from src.api.server import app
    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    max_wait = 10
    start = time.time()
    while time.time() - start < max_wait:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)

    yield base_url
    server.should_exit = True
    thread.join(timeout=2)


@pytest.fixture(scope="session")
def browser_instance():
    with sync_playwright() as p:
        launch_args = ["--no-sandbox", "--disable-dev-shm-usage"]
        executable = None
        for candidate in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                executable = candidate
                break

        try:
            if executable:
                browser = p.chromium.launch(
                    executable_path=executable,
                    headless=True,
                    args=launch_args
                )
            else:
                browser = p.chromium.launch(
                    headless=True,
                    args=launch_args
                )
        except Exception:
            browser = p.chromium.launch(
                headless=True,
                args=launch_args
            )
        yield browser
        browser.close()
