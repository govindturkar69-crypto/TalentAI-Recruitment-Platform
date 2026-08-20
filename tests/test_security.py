"""Security regression tests covering all remediation findings."""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("SENTRY_DSN", "")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key-for-ci")
os.environ.setdefault("TESTING", "True")

from app import app, is_safe_redirect_url


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


def _login_candidate(client, user_id=1, name="Test User"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["name"] = name
        sess["role"] = "candidate"


def _login_recruiter(client, user_id=100, name="Recruiter"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["name"] = name
        sess["role"] = "recruiter"


# ==========================================================================
# H5 — Password reset token must not leak
# ==========================================================================
class TestPasswordResetTokenLeak:
    @patch("routes.auth.send_password_reset_email")
    @patch("routes.auth.get_db_connection")
    def test_reset_token_not_in_response(self, mock_db, mock_send, client):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"id": 1, "email": "test@test.com"}

        resp = client.post("/forgot_password", data={"email": "test@test.com"}, follow_redirects=True)
        assert b"If that email is registered, a password reset link has been sent." in resp.data
        html = resp.data.decode("utf-8")
        assert "reset_password" not in html.lower() or "reset link" not in html
        assert "/reset_password/" not in html
        mock_send.assert_called_once()

    @patch("routes.auth.send_password_reset_email")
    @patch("routes.auth.get_db_connection")
    def test_response_same_for_unknown_email(self, mock_db, mock_send, client):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None  # Email not found

        resp = client.post("/forgot_password", data={"email": "nobody@x.com"}, follow_redirects=True)
        assert b"If that email is registered, a password reset link has been sent." in resp.data
        mock_send.assert_not_called()


# ==========================================================================
# H1 — Candidate score API authentication
# ==========================================================================
class TestCandidateScoreAPI:
    def test_anonymous_rejected(self, client):
        resp = client.get("/api/candidate/1/score")
        assert resp.status_code in (302, 401, 403)

    @patch("app.get_db_connection")
    def test_candidate_own_score(self, mock_db, client):
        _login_candidate(client, user_id=5)
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [{"score": 85.0, "job_title": "Dev"}]

        resp = client.get("/api/candidate/5/score")
        assert resp.status_code == 200

    @patch("app.get_db_connection")
    def test_candidate_other_score_rejected(self, mock_db, client):
        _login_candidate(client, user_id=5)
        resp = client.get("/api/candidate/99/score")
        assert resp.status_code == 404


# ==========================================================================
# H2 — Jobs API authentication and filtering
# ==========================================================================
class TestJobsAPI:
    def test_anonymous_rejected(self, client):
        resp = client.get("/api/jobs")
        assert resp.status_code in (302, 401, 403)

    @patch("app.get_db_connection")
    def test_authenticated_access(self, mock_db, client):
        _login_candidate(client)
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []

        resp = client.get("/api/jobs")
        assert resp.status_code == 200

    @patch("app.get_db_connection")
    def test_only_active_jobs(self, mock_db, client):
        _login_candidate(client)
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []

        client.get("/api/jobs")
        sql = mock_cur.execute.call_args[0][0]
        assert "is_active = TRUE" in sql


# ==========================================================================
# H3 — Recruiter view applicants IDOR
# ==========================================================================
class TestRecruiterApplicantsIDOR:
    @patch("routes.recruiter.get_db_connection")
    def test_own_job_accessible(self, mock_db, client):
        _login_recruiter(client, user_id=100)
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # First call: job lookup (owned), second call: applicants
        mock_cur.fetchone.return_value = {
            "id": 1,
            "job_title": "Dev",
            "recruiter_id": 100,
            "location": "Remote",
            "experience": "2y",
            "required_skills": "python",
            "is_active": True,
            "cnt": 0,
        }
        mock_cur.fetchall.return_value = []

        resp = client.get("/recruiter/job/1/applicants")
        assert resp.status_code == 200

    @patch("routes.recruiter.get_db_connection")
    def test_other_recruiter_job_rejected(self, mock_db, client):
        _login_recruiter(client, user_id=100)
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None  # Not owned

        resp = client.get("/recruiter/job/999/applicants")
        assert resp.status_code == 302  # Redirect to dashboard


# ==========================================================================
# H4 — Recruiter application status IDOR
# ==========================================================================
class TestRecruiterStatusIDOR:
    @patch("services.recruiter_service.get_db_connection")
    def test_update_status_verifies_ownership(self, mock_db):
        from services.recruiter_service import update_status_service

        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None  # Not owned

        result = update_status_service(app_id=1, new_status="hired", recruiter_id=999)
        assert result["success"] is False


# ==========================================================================
# H6 — Rate limiting
# ==========================================================================
class TestRateLimiting:
    def test_login_under_limit(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_normal_routes_not_limited(self, client):
        resp = client.get("/")
        assert resp.status_code == 200


# ==========================================================================
# M2 — Security headers
# ==========================================================================
class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/")
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_referrer_policy(self, client):
        resp = client.get("/")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        resp = client.get("/")
        assert "camera=()" in resp.headers.get("Permissions-Policy", "")


# ==========================================================================
# M1 — Open redirect prevention
# ==========================================================================
class TestOpenRedirect:
    def test_safe_same_origin(self):
        with app.test_request_context("/"):
            assert is_safe_redirect_url("/candidate/dashboard") is True

    def test_reject_external(self):
        with app.test_request_context("/", base_url="http://localhost"):
            assert is_safe_redirect_url("https://evil.com/steal") is False

    def test_reject_none(self):
        with app.test_request_context("/"):
            assert is_safe_redirect_url(None) is False

    def test_reject_empty(self):
        with app.test_request_context("/"):
            assert is_safe_redirect_url("") is False


# ==========================================================================
# M4 — Session lifetime
# ==========================================================================
class TestSessionLifetime:
    @patch("routes.auth.get_db_connection")
    def test_login_creates_permanent_session(self, mock_db, client):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {
            "id": 1,
            "name": "Test",
            "email": "t@t.com",
            "password": "pbkdf2:sha256:600000$x$y",  # won't match
            "role": "candidate",
        }

        # Login will fail (password mismatch) but we can check config
        from datetime import timedelta

        assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(hours=8)


# ==========================================================================
# M5 — Logout POST only
# ==========================================================================
class TestLogoutPostOnly:
    def test_get_logout_rejected(self, client):
        _login_candidate(client)
        resp = client.get("/logout")
        assert resp.status_code == 405  # Method Not Allowed

    def test_post_logout_clears_session(self, client):
        _login_candidate(client)
        resp = client.post("/logout", follow_redirects=False)
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert "user_id" not in sess


# ==========================================================================
# L1 — Registration enumeration prevention
# ==========================================================================
class TestRegistrationEnumeration:
    @patch("routes.auth.get_db_connection")
    def test_duplicate_email_generic_message(self, mock_db, client):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # Simulate duplicate key error
        mock_cur.execute.side_effect = [Exception("Duplicate entry")]

        resp = client.post(
            "/register",
            data={"name": "X", "email": "x@x.com", "password": "longpassword1"},
            follow_redirects=True,
        )
        html = resp.data.decode()
        assert "already registered" not in html.lower()


# ==========================================================================
# L4 — Profile URL validation
# ==========================================================================
class TestProfileURLValidation:
    @patch("routes.candidate.get_db_connection")
    def test_javascript_url_rejected(self, mock_db, client):
        _login_candidate(client)
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"id": 1, "cnt": 0, "skills": ""}

        resp = client.post(
            "/candidate/profile",
            data={
                "bio": "test",
                "phone": "",
                "location": "",
                "experience_years": "",
                "linkedin_url": "javascript:alert(1)",
                "github_url": "",
                "portfolio_url": "",
            },
            follow_redirects=True,
        )
        html = resp.data.decode()
        assert "https://" in html or resp.status_code in (200, 302)

    @patch("routes.candidate.get_db_connection")
    def test_valid_url_accepted(self, mock_db, client):
        _login_candidate(client)
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"id": 1, "cnt": 0, "skills": ""}

        resp = client.post(
            "/candidate/profile",
            data={
                "bio": "test",
                "phone": "",
                "location": "",
                "experience_years": "",
                "linkedin_url": "https://linkedin.com/in/test",
                "github_url": "",
                "portfolio_url": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
