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
        mock_cur.fetchone.return_value = {"email": "candidate@test.com", "is_active": True}

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
        mock_cur.fetchone.return_value = {"email": "recruiter@test.com", "is_active": True}

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
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        # Mock admin dashboard queries
        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur

        mock_admin_cur.fetchone.side_effect = [
            {
                "total_users": 10,
                "candidates": 8,
                "recruiters": 2,
                "active_users": 9,
                "inactive_users": 1,
                "unassigned_recruiters": 0,
            },
            {
                "total_jobs": 5,
                "active_jobs": 4,
                "inactive_jobs": 1,
            },
            {
                "total_applications": 15,
                "applied": 5,
                "shortlisted": 4,
                "hired": 2,
                "rejected": 3,
                "withdrawn": 1,
            },
            {
                "total_interviews": 6,
                "scheduled": 3,
                "completed": 2,
                "cancelled": 1,
                "upcoming": 2,
            },
            {
                "total_companies": 3,
                "active_companies": 2,
                "inactive_companies": 1,
            },
            {"total": 1},  # filtered_total
        ]
        test_user = {
            "id": 1,
            "name": "Test",
            "email": "a@a.com",
            "role": "candidate",
            "is_active": True,
            "created_at": None,
            "company_id": None,
            "company_name": None,
        }
        mock_admin_cur.fetchall.side_effect = [
            [test_user],  # users
            [],  # active companies
            [test_user],  # recent_users
        ]

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200
        assert b"Admin Console" in resp.data
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
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.return_value = {"id": 2, "role": "candidate", "is_active": True}  # Target user exists

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
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

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
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

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


def _setup_admin_dashboard_mock(
    mock_core_db, mock_admin_db, client, filtered_total=1, users=None, companies=None, recent_users=None
):
    _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])

    mock_core_conn = MagicMock()
    mock_core_db.return_value = mock_core_conn
    mock_core_cur = MagicMock()
    mock_core_conn.cursor.return_value = mock_core_cur
    mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

    mock_admin_conn = MagicMock()
    mock_admin_db.return_value = mock_admin_conn
    mock_admin_cur = MagicMock()
    mock_admin_conn.cursor.return_value = mock_admin_cur

    if users is None:
        users = [
            {
                "id": 1,
                "name": "Test User",
                "email": "user@test.com",
                "role": "candidate",
                "is_active": True,
                "created_at": None,
                "company_id": None,
                "company_name": None,
            }
        ]
    if companies is None:
        companies = [{"id": 1, "name": "Acme Corp", "is_active": True}]
    if recent_users is None:
        recent_users = []

    mock_admin_cur.fetchone.side_effect = [
        {
            "total_users": 10,
            "candidates": 8,
            "recruiters": 2,
            "active_users": 9,
            "inactive_users": 1,
            "unassigned_recruiters": 0,
        },
        {
            "total_jobs": 5,
            "active_jobs": 4,
            "inactive_jobs": 1,
        },
        {
            "total_applications": 15,
            "applied": 5,
            "shortlisted": 4,
            "hired": 2,
            "rejected": 3,
            "withdrawn": 1,
        },
        {
            "total_interviews": 6,
            "scheduled": 3,
            "completed": 2,
            "cancelled": 1,
            "upcoming": 2,
        },
        {
            "total_companies": 3,
            "active_companies": 2,
            "inactive_companies": 1,
        },
        {"total": filtered_total},  # filtered_total
    ]

    mock_admin_cur.fetchall.side_effect = [
        users if filtered_total > 0 else [],
        companies,
        recent_users,
    ]
    return mock_admin_cur


def _find_execute_call(mock_cur, sql_snippet):
    for call in mock_cur.execute.call_args_list:
        query = call[0][0]
        params = call[0][1] if len(call[0]) > 1 else ()
        if sql_snippet in query:
            return query, params
    return None, None


class TestAdminScalingPhase5B:
    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_default_pagination(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=50)
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "LIMIT %s OFFSET %s")
        assert query is not None
        assert params[-2:] == (20, 0)
        assert b"Showing 1-20 of 50 users" in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_per_page_clamp(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=250)
        resp = client.get("/admin/dashboard?per_page=1000")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "LIMIT %s OFFSET %s")
        assert query is not None
        assert params[-2:] == (100, 0)

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_per_page(self, mock_core_db, mock_admin_db, client):
        for invalid_val in ["invalid", "-5", "0"]:
            cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=50)
            resp = client.get(f"/admin/dashboard?per_page={invalid_val}")
            assert resp.status_code == 200
            query, params = _find_execute_call(cur, "LIMIT %s OFFSET %s")
            assert query is not None
            assert params[-2:] == (20, 0)

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_page(self, mock_core_db, mock_admin_db, client):
        for invalid_val in ["0", "-5", "abc"]:
            cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=50)
            resp = client.get(f"/admin/dashboard?page={invalid_val}")
            assert resp.status_code == 200
            query, params = _find_execute_call(cur, "LIMIT %s OFFSET %s")
            assert query is not None
            assert params[-2:] == (20, 0)

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_page_above_max_clamped(self, mock_core_db, mock_admin_db, client):
        # 45 total with 20 per_page => 3 pages (offset for page 3 is 40)
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=45)
        resp = client.get("/admin/dashboard?page=999")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "LIMIT %s OFFSET %s")
        assert query is not None
        assert params[-2:] == (20, 40)
        assert b"Showing 41-45 of 45 users" in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_role_filter(self, mock_core_db, mock_admin_db, client):
        for role in ["candidate", "recruiter"]:
            cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
            resp = client.get(f"/admin/dashboard?role={role}")
            assert resp.status_code == 200
            query, params = _find_execute_call(cur, "u.role = %s")
            assert query is not None
            assert role in params

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_role_ignored(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard?role=superadmin")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "u.role = %s")
        assert query is None

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_status_filter(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard?status=active")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "u.is_active = %s")
        assert query is not None
        assert True in params

        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard?status=inactive")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "u.is_active = %s")
        assert query is not None
        assert False in params

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_status_ignored(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard?status=banned")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "u.is_active = %s")
        assert query is None

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_company_id_filter(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard?company_id=5")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "u.company_id = %s")
        assert query is not None
        assert 5 in params

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_company_id_ignored(self, mock_core_db, mock_admin_db, client):
        for invalid_val in ["-1", "0", "abc"]:
            cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
            resp = client.get(f"/admin/dashboard?company_id={invalid_val}")
            assert resp.status_code == 200
            query, params = _find_execute_call(cur, "u.company_id = %s")
            assert query is None

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_q_search(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard?q=alice")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "LIKE %s ESCAPE '='")
        assert query is not None
        assert "%alice%" in params

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_literal_wildcard_handling(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard?q=100%_deal=win")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "LIKE %s ESCAPE '='")
        assert query is not None
        expected_escaped = "%100=%=_deal==win%"
        assert expected_escaped in params

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_combined_filters_order(self, mock_core_db, mock_admin_db, client):
        cur = _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=100)
        resp = client.get("/admin/dashboard?q=bob&role=recruiter&status=active&company_id=3&page=2&per_page=50")
        assert resp.status_code == 200
        query, params = _find_execute_call(cur, "LIMIT %s OFFSET %s")
        assert query is not None
        assert params == ("%bob%", "%bob%", "recruiter", True, 3, 50, 50)

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_xss_prevention_in_search(self, mock_core_db, mock_admin_db, client):
        _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=1)
        resp = client.get('/admin/dashboard?q=<script>alert("xss")</script>')
        assert resp.status_code == 200
        assert b'<script>alert("xss")</script>' not in resp.data
        assert b"alert(&#34;xss&#34;)" in resp.data or b"alert(&quot;xss&quot;)" in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_pagination_links_preserve_filters(self, mock_core_db, mock_admin_db, client):
        _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=60)
        resp = client.get("/admin/dashboard?q=alice&role=recruiter&per_page=20")
        assert resp.status_code == 200
        assert b"page=2" in resp.data
        assert b"q=alice" in resp.data
        assert b"role=recruiter" in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_clear_filters_link(self, mock_core_db, mock_admin_db, client):
        _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard?q=alice&role=recruiter")
        assert resp.status_code == 200
        assert b'href="/admin/dashboard"' in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_only_paginated_users_rendered_and_no_client_filtering(self, mock_core_db, mock_admin_db, client):
        _setup_admin_dashboard_mock(mock_core_db, mock_admin_db, client, filtered_total=10)
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200
        assert b"userSearch" not in resp.data
        assert b"roleFilter" not in resp.data
        assert b"filterUsers" not in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_mutation_redirect_preserves_dashboard_state(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])

        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.return_value = {"id": 2, "role": "candidate", "is_active": True}

        resp = client.post(
            "/admin/users/2/role?page=2&per_page=50&q=dev&role=candidate",
            data={"role": "recruiter"},
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "/admin/dashboard?" in location
        assert "page=2" in location
        assert "per_page=50" in location
        assert "q=dev" in location
        assert "role=candidate" in location

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_open_redirect_defense(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])

        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.return_value = {"id": 2, "role": "candidate", "is_active": True}

        resp = client.post(
            "/admin/users/2/role?next=https://evil.example&q=dev",
            data={"role": "recruiter"},
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "evil.example" not in location
        assert location.startswith("/admin/dashboard")


class TestAdminPlatformAnalyticsPhase5C:
    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_dashboard_aggregate_metrics_render(self, mock_core_db, mock_admin_db, client):
        """Verify mocked rows correctly populate users, jobs, applications, interviews, companies."""
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur

        mock_admin_cur.fetchone.side_effect = [
            {
                "total_users": 150,
                "candidates": 100,
                "recruiters": 50,
                "active_users": 140,
                "inactive_users": 10,
                "unassigned_recruiters": 7,
            },
            {
                "total_jobs": 42,
                "active_jobs": 35,
                "inactive_jobs": 7,
            },
            {
                "total_applications": 200,
                "applied": 80,
                "shortlisted": 50,
                "hired": 20,
                "rejected": 40,
                "withdrawn": 10,
            },
            {
                "total_interviews": 55,
                "scheduled": 25,
                "completed": 20,
                "cancelled": 10,
                "upcoming": 12,
            },
            {
                "total_companies": 18,
                "active_companies": 15,
                "inactive_companies": 3,
            },
            {"total": 150},  # filtered_total
        ]
        mock_admin_cur.fetchall.side_effect = [
            [],  # users
            [],  # companies
            [],  # recent_users
        ]

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200
        html = resp.data.decode()

        # Platform Overview cards
        assert "Total Users" in html
        assert "150" in html
        assert "Total Jobs" in html
        assert "42" in html
        assert "Total Applications" in html
        assert "200" in html
        assert "Total Interviews" in html
        assert "55" in html
        assert "Active Companies" in html
        assert "15" in html

        # Application Pipeline section
        assert "Application Pipeline" in html
        assert "40.0%" in html  # 80/200
        assert "25.0%" in html  # 50/200
        assert "10.0%" in html  # 20/200
        assert "20.0%" in html  # 40/200
        assert "5.0%" in html  # 10/200

        # Interview Overview section
        assert "Interview Overview" in html
        assert "Scheduled" in html
        assert "25" in html
        assert "Upcoming" in html
        assert "12" in html
        assert "Completed" in html
        assert "20" in html
        assert "Cancelled" in html
        assert "10" in html

        # Operational Health section
        assert "Operational Health" in html
        assert "Active: 140" in html
        assert "Inactive: 10" in html
        assert "Unassigned Recruiters" in html
        assert "7" in html
        assert "Active: 35" in html
        assert "Inactive: 7" in html
        assert "Active: 15" in html
        assert "Inactive: 3" in html

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_empty_database_behavior(self, mock_core_db, mock_admin_db, client):
        """All aggregate values render as zero without divide-by-zero or template errors."""
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur

        mock_admin_cur.fetchone.side_effect = [
            None,  # users
            None,  # jobs
            None,  # applications
            None,  # interviews
            None,  # companies
            {"total": 0},  # filtered_total
        ]
        mock_admin_cur.fetchall.side_effect = [
            [],  # users
            [],  # companies
            [],  # recent_users
        ]

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Application Pipeline" in html
        assert "Interview Overview" in html
        assert "Operational Health" in html
        assert "0.0%" in html
        assert "Active: 0" in html
        assert "Inactive: 0" in html

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_upcoming_interview_query_contract(self, mock_core_db, mock_admin_db, client):
        """Verify interview query uses DB NOW() for upcoming without Python system time or extra params."""
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur

        mock_admin_cur.fetchone.side_effect = [{}, {}, {}, {}, {}, {"total": 0}]
        mock_admin_cur.fetchall.side_effect = [[], [], []]

        client.get("/admin/dashboard")

        interview_query = None
        for call in mock_admin_cur.execute.call_args_list:
            q = call[0][0]
            if "FROM interviews" in q:
                interview_query = q
                break

        assert interview_query is not None
        assert "status = 'scheduled'" in interview_query
        assert "scheduled_at > NOW()" in interview_query
        # Ensure no sensitive fields exposed
        assert "notes" not in interview_query.lower()
        assert "location_or_link" not in interview_query.lower()

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_application_pipeline_values_and_zero_division(self, mock_core_db, mock_admin_db, client):
        """Verify pipeline computes percentages accurately and handles zero total cleanly."""
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur

        mock_admin_cur.fetchone.side_effect = [
            {"total_users": 10},
            {"total_jobs": 5},
            {
                "total_applications": 20,
                "applied": 10,
                "shortlisted": 5,
                "hired": 2,
                "rejected": 2,
                "withdrawn": 1,
            },
            {"total_interviews": 0},
            {"total_companies": 0},
            {"total": 10},
        ]
        mock_admin_cur.fetchall.side_effect = [[], [], []]

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "50.0%" in html  # 10/20
        assert "25.0%" in html  # 5/20
        assert "10.0%" in html  # 2/20
        assert "5.0%" in html  # 1/20

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_operational_metrics_contract(self, mock_core_db, mock_admin_db, client):
        """Verify active/inactive users/jobs/companies and unassigned recruiters display."""
        _login_as(client, role="recruiter", email=app.config["ADMIN_EMAIL"])
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": app.config["ADMIN_EMAIL"], "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur

        mock_admin_cur.fetchone.side_effect = [
            {
                "total_users": 50,
                "candidates": 30,
                "recruiters": 20,
                "active_users": 45,
                "inactive_users": 5,
                "unassigned_recruiters": 3,
            },
            {"total_jobs": 10, "active_jobs": 8, "inactive_jobs": 2},
            {"total_applications": 0, "applied": 0, "shortlisted": 0, "hired": 0, "rejected": 0, "withdrawn": 0},
            {"total_interviews": 0, "scheduled": 0, "completed": 0, "cancelled": 0, "upcoming": 0},
            {"total_companies": 5, "active_companies": 4, "inactive_companies": 1},
            {"total": 50},
        ]
        mock_admin_cur.fetchall.side_effect = [[], [], []]

        resp = client.get("/admin/dashboard")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "Active: 45" in html
        assert "Inactive: 5" in html
        assert "Active: 8" in html
        assert "Inactive: 2" in html
        assert "Active: 4" in html
        assert "Inactive: 1" in html
        assert "Unassigned Recruiters" in html

    def test_non_admin_cannot_access_analytics(self, client):
        """Unauthorized users cannot access the dashboard or see analytics."""
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
