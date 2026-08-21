from unittest.mock import MagicMock, patch

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["ADMIN_EMAIL"] = "admin@company.com"
    with app.test_client() as c:
        yield c


def _login_as(client, user_id=1, role="candidate", email="user@company.com"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["name"] = "Test User"
        sess["role"] = role
        sess["is_admin"] = email == app.config["ADMIN_EMAIL"]


class TestAdminPanel:
    def test_anonymous_cannot_access_admin(self, client):
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert b"/login" in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_candidate_cannot_access_admin(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="candidate", email="candidate@test.com")

        mock_conn = MagicMock()
        mock_core_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"email": "candidate@test.com"}

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_recruiter_cannot_access_admin(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="recruiter", email="recruiter@test.com")

        mock_conn = MagicMock()
        mock_core_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"email": "recruiter@test.com"}

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_admin_can_access_dashboard(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])

        # Mock core auth check
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"]}

        # Mock admin dashboard queries
        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur

        mock_admin_cur.fetchone.side_effect = [
            {"total": 10},  # total
            {"total": 8},  # candidates
            {"total": 2},  # recruiters
        ]
        mock_admin_cur.fetchall.return_value = [
            {"id": 1, "name": "Test", "email": "a@a.com", "role": "candidate", "created_at": None}
        ]

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200
        assert b"Admin Dashboard" in resp.data
        assert b"Total Users" in resp.data
        # Ensure password hashes are never accidentally mocked/shown
        assert b"pbkdf2:sha256" not in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_admin_change_role(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])

        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"]}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.return_value = {"id": 2}  # Target user exists

        resp = client.post("/admin/users/2/role", data={"role": "recruiter"})
        assert resp.status_code == 302
        mock_admin_cur.execute.assert_any_call("UPDATE users SET role = %s WHERE id = %s", ("recruiter", 2))

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_admin_cannot_change_own_role(self, mock_core_db, mock_admin_db, client):
        _login_as(client, user_id=1, role="recruiter", email=app.config["ADMIN_EMAIL"])

        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"]}

        resp = client.post("/admin/users/1/role", data={"role": "candidate"})
        assert resp.status_code == 302
        assert mock_admin_db.call_count == 0  # Should short-circuit before hitting DB

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_role_rejected(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])

        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"]}

        resp = client.post("/admin/users/2/role", data={"role": "superadmin"})
        assert resp.status_code == 302
        assert mock_admin_db.call_count == 0

    @patch("core.get_db_connection")
    def test_missing_admin_email_denies_access(self, mock_core_db, client):
        app.config["ADMIN_EMAIL"] = ""
        _login_as(client, role="recruiter", email="admin@company.com")

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302

    def test_public_registration_with_admin_email_rejected(self, client):
        resp = client.post(
            "/register",
            data={"name": "Attacker", "email": app.config["ADMIN_EMAIL"], "password": "password123"},
        )
        # Should return a generic message and NOT insert to DB
        assert b"could not be completed" in resp.data
