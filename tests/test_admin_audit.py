import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app import app
from routes.admin import _parse_audit_safe_details


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


def _make_mock_audit_row(
    id=1,
    actor_user_id=1,
    action="update_user_role",
    target_type="user",
    target_id=2,
    safe_details=None,
    created_at=None,
    actor_name="HR Admin",
    actor_email="admin@company.com",
):
    return {
        "id": id,
        "actor_user_id": actor_user_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "safe_details": safe_details,
        "created_at": created_at or datetime(2026, 9, 6, 12, 0, 0),
        "actor_name": actor_name,
        "actor_email": actor_email,
    }


class TestAuditLogAuthorization:
    def test_unauthenticated_cannot_access_audit_logs(self, client):
        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_candidate_cannot_access_audit_logs(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="candidate", email="candidate@test.com")

        mock_conn = MagicMock()
        mock_core_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"email": "candidate@test.com", "is_active": True}

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 302
        assert resp.headers.get("Location", "") == "/"

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_recruiter_cannot_access_audit_logs(self, mock_core_db, mock_admin_db, client):
        _login_as(client, role="recruiter", email="recruiter@test.com")

        mock_conn = MagicMock()
        mock_core_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"email": "recruiter@test.com", "is_active": True}

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 302
        assert resp.headers.get("Location", "") == "/"

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_admin_allowed_access(self, mock_core_db, mock_admin_db, client):
        _login_as(client, user_id=1, role="recruiter", email="admin@company.com")

        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.side_effect = [{"total_unfiltered": 1}, {"total": 1}]
        mock_admin_cur.fetchall.return_value = [_make_mock_audit_row()]

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        assert b"Audit Logs" in resp.data


class TestAuditLogPaginationAndQueries:
    def _setup_admin(self, mock_core_db, mock_admin_db, client):
        _login_as(client, user_id=1, role="recruiter", email="admin@company.com")
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        return mock_admin_cur

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_default_pagination(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 50}, {"total": 50}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row(id=i) for i in range(1, 26)]

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        # verify LIMIT 25 OFFSET 0
        calls = [c for c in mock_cur.execute.call_args_list if "LIMIT %s OFFSET %s" in str(c)]
        assert len(calls) == 1
        args = calls[0][0][1]
        assert args[-2:] == [25, 0]

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_custom_page_and_per_page(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 150}, {"total": 150}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row(id=i) for i in range(1, 51)]

        resp = client.get("/admin/audit-logs?page=2&per_page=50")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "LIMIT %s OFFSET %s" in str(c)]
        assert len(calls) == 1
        args = calls[0][0][1]
        assert args[-2:] == [50, 50]

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_per_page_100(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 200}, {"total": 200}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row(id=i) for i in range(1, 101)]

        resp = client.get("/admin/audit-logs?page=1&per_page=100")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "LIMIT %s OFFSET %s" in str(c)]
        assert len(calls) == 1
        args = calls[0][0][1]
        assert args[-2:] == [100, 0]

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_pagination_params_normalized(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 30}, {"total": 30}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row()]

        resp = client.get("/admin/audit-logs?page=-5&per_page=999")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "LIMIT %s OFFSET %s" in str(c)]
        assert len(calls) == 1
        args = calls[0][0][1]
        # per_page normalized to 25, page clamped to 1 (offset 0)
        assert args[-2:] == [25, 0]

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_excessive_page_clamped_to_total_pages(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 20}, {"total": 20}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row()]

        resp = client.get("/admin/audit-logs?page=10&per_page=25")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "LIMIT %s OFFSET %s" in str(c)]
        assert len(calls) == 1
        args = calls[0][0][1]
        # 20 items / 25 per_page = 1 total page, so page 10 clamped to page 1 (offset 0)
        assert args[-2:] == [25, 0]

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_zero_total_records_case_a(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 0}, {"total": 0}]
        mock_cur.fetchall.return_value = []

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        assert b"No audit events have been recorded yet." in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_zero_filtered_records_case_b(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 10}, {"total": 0}]
        mock_cur.fetchall.return_value = []

        resp = client.get("/admin/audit-logs?action=create_company")
        assert resp.status_code == 200
        assert b"No audit events match these filters." in resp.data


class TestAuditLogFilters:
    def _setup_admin(self, mock_core_db, mock_admin_db, client):
        _login_as(client, user_id=1, role="recruiter", email="admin@company.com")
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        return mock_admin_cur

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_action_filter(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 10}, {"total": 2}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row(action="update_user_role")]

        resp = client.get("/admin/audit-logs?action=update_user_role")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "al.action = %s" in str(c)]
        assert len(calls) == 2  # count and records query
        assert "update_user_role" in calls[0][0][1]

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_target_type_filter(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 10}, {"total": 3}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row(target_type="company")]

        resp = client.get("/admin/audit-logs?target_type=company")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "al.target_type = %s" in str(c)]
        assert len(calls) == 2
        assert "company" in calls[0][0][1]

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_actor_search_escapes_wildcards(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 10}, {"total": 1}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row()]

        resp = client.get("/admin/audit-logs?actor=test%user_name")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "u.name LIKE %s" in str(c)]
        assert len(calls) == 2
        # % and _ escaped with =
        assert "%test=%user=_name%" in calls[0][0][1]

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_date_range_half_open(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 10}, {"total": 1}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row()]

        resp = client.get("/admin/audit-logs?date_from=2026-09-01&date_to=2026-09-05")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "al.created_at >= %s" in str(c)]
        assert len(calls) == 2
        params = calls[0][0][1]
        assert "2026-09-01 00:00:00" in params
        # date_to must be half-open: < 2026-09-06 00:00:00
        assert "2026-09-06 00:00:00" in params

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_dates_handled_gracefully(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 10}, {"total": 10}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row()]

        resp = client.get("/admin/audit-logs?date_from=invalid-date&date_to=2026-99-99")
        assert resp.status_code == 200

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_inverted_date_range_handled_gracefully(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 10}, {"total": 0}]
        mock_cur.fetchall.return_value = []

        resp = client.get("/admin/audit-logs?date_from=2026-09-10&date_to=2026-09-01")
        assert resp.status_code == 200
        assert b"Start date cannot be after end date. Please correct the date range." in resp.data
        assert b"Date filter was ignored" not in resp.data
        assert b"No audit events match these filters." in resp.data
        calls = [c for c in mock_cur.execute.call_args_list if "1 = 0" in str(c)]
        assert len(calls) == 2

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_invalid_action_and_target_type_ignored(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 10}, {"total": 10}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row()]

        resp = client.get("/admin/audit-logs?action=malicious_drop_table&target_type=hack_type")
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "al.action = %s" in str(c)]
        assert len(calls) == 0

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_combined_filters(self, mock_core_db, mock_admin_db, client):
        mock_cur = self._setup_admin(mock_core_db, mock_admin_db, client)
        mock_cur.fetchone.side_effect = [{"total_unfiltered": 50}, {"total": 5}]
        mock_cur.fetchall.return_value = [_make_mock_audit_row(action="update_user_role", target_type="user")]

        resp = client.get(
            "/admin/audit-logs?action=update_user_role&target_type=user&actor=admin&date_from=2026-09-01&date_to=2026-09-05"
        )
        assert resp.status_code == 200
        calls = [c for c in mock_cur.execute.call_args_list if "al.action = %s" in str(c)]
        assert len(calls) == 2
        # Verify all where clauses are present
        executed_sql = str(calls[0])
        assert "al.action = %s" in executed_sql
        assert "al.target_type = %s" in executed_sql
        assert "u.name LIKE %s" in executed_sql
        assert "al.created_at >= %s" in executed_sql
        assert "al.created_at < %s" in executed_sql


class TestSafeDetailsParser:
    def test_none_and_empty(self):
        assert _parse_audit_safe_details(None) == []
        assert _parse_audit_safe_details("") == []
        assert _parse_audit_safe_details("   ") == []

    def test_malformed_json(self):
        assert _parse_audit_safe_details("{broken-json") == []
        assert _parse_audit_safe_details("null") == []

    def test_non_dict_json(self):
        assert _parse_audit_safe_details('["item1", "item2"]') == []
        assert _parse_audit_safe_details('"just a string"') == []
        assert _parse_audit_safe_details("12345") == []

    def test_unknown_keys_filtered(self):
        raw = json.dumps({"unknown_secret_key": "hidden_val", "previous_role": "candidate"})
        parsed = _parse_audit_safe_details(raw)
        assert len(parsed) == 1
        assert parsed[0]["label"] == "Previous Role"
        assert parsed[0]["value"] == "candidate"

    def test_suppressed_fields_filtered(self):
        # ip_address and user_agent are in AUDIT_ALLOWLIST but MUST NOT be displayed in viewer
        raw = json.dumps({"ip_address": "127.0.0.1", "user_agent": "Mozilla/5.0", "company_name": "Acme Corp"})
        parsed = _parse_audit_safe_details(raw)
        assert len(parsed) == 1
        assert parsed[0]["label"] == "Company Name"
        assert parsed[0]["value"] == "Acme Corp"

    def test_boolean_active_inactive_conversion(self):
        raw = json.dumps({"is_active_before": True, "is_active_after": False})
        parsed = _parse_audit_safe_details(raw)
        assert len(parsed) == 2
        labels_vals = {item["label"]: item["value"] for item in parsed}
        assert labels_vals["Previous Status"] == "Active"
        assert labels_vals["New Status"] == "Inactive"

    def test_value_truncation(self):
        long_val = "x" * 150
        raw = json.dumps({"company_name": long_val})
        parsed = _parse_audit_safe_details(raw)
        assert len(parsed) == 1
        assert len(parsed[0]["value"]) == 103  # 100 chars + "..."
        assert parsed[0]["value"].endswith("...")


class TestSecurityAndEscaping:
    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_xss_content_escaped(self, mock_core_db, mock_admin_db, client):
        _login_as(client, user_id=1, role="recruiter", email="admin@company.com")
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.side_effect = [{"total_unfiltered": 1}, {"total": 1}]

        xss_payload = "<script>alert('xss')</script>"
        raw_details = json.dumps({"company_name": xss_payload})
        row = _make_mock_audit_row(
            actor_name="<script>evil_actor</script>",
            action="<script>evil_action</script>",
            target_type="<script>evil_target</script>",
            safe_details=raw_details,
        )
        mock_admin_cur.fetchall.return_value = [row]

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        # raw script tags must NOT appear unescaped
        assert b"<script>alert('xss')</script>" not in resp.data
        assert b"<script>evil_actor</script>" not in resp.data
        assert b"<script>evil_action</script>" not in resp.data
        assert b"<script>evil_target</script>" not in resp.data
        # escaped entities should appear
        assert b"&lt;script&gt;" in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_null_and_deleted_actor_fallback(self, mock_core_db, mock_admin_db, client):
        _login_as(client, user_id=1, role="recruiter", email="admin@company.com")
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.side_effect = [{"total_unfiltered": 1}, {"total": 1}]

        row = _make_mock_audit_row(actor_user_id=None, actor_name=None, actor_email=None)
        mock_admin_cur.fetchall.return_value = [row]

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        assert b"System / Deleted User" in resp.data

    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_unknown_and_missing_action_target_types(self, mock_core_db, mock_admin_db, client):
        _login_as(client, user_id=1, role="recruiter", email="admin@company.com")
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.side_effect = [{"total_unfiltered": 2}, {"total": 2}]

        row1 = _make_mock_audit_row(id=1, action="custom_event_fired", target_type="custom_entity")
        row2 = _make_mock_audit_row(id=2, action=None, target_type=None)
        mock_admin_cur.fetchall.return_value = [row1, row2]

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        # row1 should format custom underscores into Title Case
        assert b"Custom Event Fired" in resp.data
        assert b"Custom Entity" in resp.data
        # row2 None should fallback to Unknown
        assert b"Unknown" in resp.data

    @patch("routes.admin.log_audit_event")
    @patch("routes.admin.get_db_connection")
    @patch("core.get_db_connection")
    def test_audit_log_viewing_is_read_only_and_does_not_log_audit_event(
        self, mock_core_db, mock_admin_db, mock_log_audit, client
    ):
        _login_as(client, user_id=1, role="recruiter", email="admin@company.com")
        mock_core_conn = MagicMock()
        mock_core_db.return_value = mock_core_conn
        mock_core_cur = MagicMock()
        mock_core_conn.cursor.return_value = mock_core_cur
        mock_core_cur.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        mock_admin_conn = MagicMock()
        mock_admin_db.return_value = mock_admin_conn
        mock_admin_cur = MagicMock()
        mock_admin_conn.cursor.return_value = mock_admin_cur
        mock_admin_cur.fetchone.side_effect = [{"total_unfiltered": 1}, {"total": 1}]
        mock_admin_cur.fetchall.return_value = [_make_mock_audit_row()]

        resp = client.get("/admin/audit-logs")
        assert resp.status_code == 200
        # Critically verify no audit-of-view event was written
        mock_log_audit.assert_not_called()
