import os
from unittest.mock import MagicMock, patch

import pytest

# Mock SENTRY_DSN for tests
os.environ["SENTRY_DSN"] = "https://mock@o0.ingest.sentry.io/0"

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


@patch("app.get_db_connection")
def test_healthz_healthy(mock_get_db, client):
    mock_conn = MagicMock()
    mock_get_db.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur

    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "database": "connected"}
    mock_cur.execute.assert_called_with("SELECT 1")


@patch("app.get_db_connection")
def test_healthz_unhealthy(mock_get_db, client):
    mock_get_db.side_effect = Exception("DB Connection Failed")

    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.json == {"status": "error", "database": "unreachable"}


def test_404_handler(client):
    response = client.get("/non_existent_route_123")
    assert response.status_code == 404


def test_500_handler(client):
    from app import app, internal_error
    with app.test_request_context("/"):
        response_tuple = internal_error(Exception("Test Exception"))
        assert response_tuple[1] == 500
        assert "500" in response_tuple[0] or "Something went wrong" in response_tuple[0]
