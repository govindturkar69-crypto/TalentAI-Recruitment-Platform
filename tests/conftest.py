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
