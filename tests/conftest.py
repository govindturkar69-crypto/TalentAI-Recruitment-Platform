"""Shared pytest setup.

conftest.py is picked up by pytest automatically. Anything defined here
(especially fixtures) is available to every test file without importing it.

The `client` fixture below gives each test a fake browser it can use to
send requests to the app, without running a real server or database.
"""

import os

import pytest

# Tell app.py we're testing BEFORE it is imported, so the DB pool doesn't
# try to open real connections at startup.
os.environ["TESTING"] = "True"
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    # CSRF tokens are generated per-request in real use; turn the check off
    # here so route tests can post without fetching a token first.
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.test_client() as client:
        yield client


from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_db():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.close = MagicMock()
    mock_cursor.close = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit = MagicMock()

    targets = [
        "app.get_db_connection",
        "core.get_db_connection",
        "routes.auth.get_db_connection",
        "routes.candidate.get_db_connection",
        "routes.recruiter.get_db_connection",
        "routes.analytics.get_db_connection",
        "services.notification_service.get_db_connection",
        "services.candidate_service.get_db_connection",
        "services.recruiter_service.get_db_connection",
        "services.analytics_service.get_db_connection",
    ]

    patchers = []
    for target in targets:
        try:
            p = patch(target, return_value=mock_conn)
            p.start()
            patchers.append(p)
        except (ImportError, AttributeError):
            pass

    yield mock_cursor

    for p in patchers:
        p.stop()
