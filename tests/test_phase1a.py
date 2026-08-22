from unittest.mock import MagicMock

import pytest
from werkzeug.security import generate_password_hash


def test_inactive_login_denied(client, mock_db):
    mock_db.fetchone.return_value = {
        "id": 1,
        "email": "test@test.com",
        "password": generate_password_hash("password123"),
        "role": "candidate",
        "name": "Test User",
        "is_active": False,
    }

    response = client.post("/login", data={"email": "test@test.com", "password": "password123"}, follow_redirects=True)
    assert b"Your account has been deactivated" in response.data


def test_inactive_session_denied(client, mock_db):
    # First query during login_required is to check is_active
    mock_db.fetchone.return_value = {"is_active": False}
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "candidate"

    response = client.get("/candidate/dashboard", follow_redirects=True)
    assert b"Your account has been deactivated" in response.data


def test_settings_access_and_password_update(client, mock_db):
    # Mock for login_required check
    mock_db.fetchone.side_effect = [
        {"is_active": True},  # for login_required GET
        {"cnt": 0},  # for inject_unread_count GET
        {"is_active": True},  # for login_required POST
        {"password": generate_password_hash("oldpass")},  # for settings POST
    ]

    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "candidate"
        sess["name"] = "Candidate"

    # Get settings page
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Change Password" in response.data

    # Post to update password
    response = client.post(
        "/settings",
        data={"current_password": "oldpass", "new_password": "newpassword123", "confirm_password": "newpassword123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
        assert any(b"Password updated successfully" in str(msg).encode() for cat, msg in flashes)


def test_admin_deactivate_user(client, mock_db, monkeypatch):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")

    with client.session_transaction() as sess:
        sess["user_id"] = 99
        sess["role"] = "admin"

    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},  # admin_required
        {"id": 2, "email": "user@test.com", "is_active": True},  # user lookup
    ]

    response = client.post("/admin/users/2/status", data={"status": "inactive"}, follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
        assert any(b"User account deactivated successfully" in str(msg).encode() for cat, msg in flashes)


def test_admin_self_deactivation_blocked(client, mock_db, monkeypatch):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")

    with client.session_transaction() as sess:
        sess["user_id"] = 99
        sess["role"] = "admin"

    mock_db.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

    # user_id == session user_id
    response = client.post("/admin/users/99/status", data={"status": "inactive"}, follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
        assert any(b"cannot deactivate your own account" in str(msg).encode() for cat, msg in flashes)


def test_audit_log_allowlist():
    import json

    from services.audit_service import log_audit_event

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with pytest.MonkeyPatch().context() as m:
        m.setattr("services.audit_service.get_db_connection", lambda: mock_conn)

        # details with some safe, some unsafe keys
        details = {
            "previous_role": "candidate",
            "new_role": "recruiter",
            "password": "supersecretpassword",
            "api_key": "12345",
        }

        log_audit_event(1, "test_action", "user", 2, details)

        # Check that safe_details JSON contains only previous_role/new_role
        called_args = mock_cursor.execute.call_args[0]
        params = called_args[1]

        safe_json = json.loads(params[4])
        assert "previous_role" in safe_json
        assert "new_role" in safe_json
        assert "password" not in safe_json
        assert "api_key" not in safe_json
