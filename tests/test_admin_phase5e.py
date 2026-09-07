import json

import pytest

from app import app
from routes.admin import (
    AUDIT_ACTION_LABELS,
    VIEWER_SAFE_DETAILS_ALLOWLIST,
    _parse_audit_safe_details,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["ADMIN_EMAIL"] = "admin@company.com"
    with app.test_client() as c:
        yield c


def _login_as(client, user_id=1, role="candidate", email="user@test.com"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role
        sess["email"] = email
        sess["name"] = "Test User"
        sess["is_admin"] = email == app.config.get("ADMIN_EMAIL")


# ==============================================================================
# 1. AUTH TESTS
# ==============================================================================
class TestAdminCompaniesAuth:
    def test_anonymous_cannot_access_companies_list(self, client):
        resp = client.get("/admin/companies", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_candidate_cannot_access_companies_list(self, client, mock_db):
        _login_as(client, role="candidate", email="cand@company.com")
        mock_db.fetchone.return_value = {"email": "cand@company.com", "is_active": True}
        resp = client.get("/admin/companies", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"

    def test_recruiter_cannot_access_companies_list(self, client, mock_db):
        _login_as(client, role="recruiter", email="rec@company.com")
        mock_db.fetchone.return_value = {"email": "rec@company.com", "is_active": True}
        resp = client.get("/admin/companies", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"

    def test_admin_can_access_companies_list(self, client, mock_db):
        _login_as(client, role="recruiter", email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},  # auth
            {"total": 1},  # count query
        ]
        mock_db.fetchall.return_value = [
            {
                "id": 1,
                "name": "Alpha Corp",
                "description": "Tech company",
                "website": "https://alpha.com",
                "is_active": True,
                "created_at": None,
                "updated_at": None,
                "recruiter_count": 2,
            }
        ]
        resp = client.get("/admin/companies", follow_redirects=False)
        assert resp.status_code == 200
        assert b"Alpha Corp" in resp.data

    def test_anonymous_cannot_toggle_company_status(self, client):
        resp = client.post("/admin/companies/1/status", data={"status": "inactive"}, follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_candidate_cannot_toggle_company_status(self, client, mock_db):
        _login_as(client, role="candidate", email="cand@company.com")
        mock_db.fetchone.return_value = {"email": "cand@company.com", "is_active": True}
        resp = client.post("/admin/companies/1/status", data={"status": "inactive"}, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"

    def test_recruiter_cannot_toggle_company_status(self, client, mock_db):
        _login_as(client, role="recruiter", email="rec@company.com")
        mock_db.fetchone.return_value = {"email": "rec@company.com", "is_active": True}
        resp = client.post("/admin/companies/1/status", data={"status": "inactive"}, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"


# ==============================================================================
# 2. LIST & PAGINATION TESTS
# ==============================================================================
class TestAdminCompaniesPagination:
    def test_default_pagination(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 35},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies")
        assert resp.status_code == 200

        # Check SQL queries
        calls = [c[0] for c in mock_db.execute.call_args_list]
        select_call = [c for c in calls if "SELECT c.id, c.name" in c[0]][0]
        sql, params = select_call
        assert "LIMIT %s OFFSET %s" in sql
        assert params == (20, 0)
        assert "ORDER BY c.name ASC, c.id ASC" in sql

    @pytest.mark.parametrize("per_page_val", [20, 50, 100])
    def test_allowed_per_page_values(self, client, mock_db, per_page_val):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 120},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get(f"/admin/companies?per_page={per_page_val}")
        assert resp.status_code == 200

        calls = [c[0] for c in mock_db.execute.call_args_list]
        select_call = [c for c in calls if "SELECT c.id, c.name" in c[0]][0]
        assert select_call[1] == (per_page_val, 0)

    def test_invalid_per_page_defaults_to_20(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 50},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?per_page=999")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        select_call = [c for c in calls if "SELECT c.id, c.name" in c[0]][0]
        assert select_call[1] == (20, 0)

    def test_invalid_page_normalizes_to_1(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 50},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?page=-5")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        select_call = [c for c in calls if "SELECT c.id, c.name" in c[0]][0]
        assert select_call[1] == (20, 0)

    def test_excessive_page_clamped_to_total_pages(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 35},  # total 35 with per_page 20 -> 2 total pages
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?page=999&per_page=20")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        select_call = [c for c in calls if "SELECT c.id, c.name" in c[0]][0]
        # page clamped to 2 -> offset = (2-1)*20 = 20
        assert select_call[1] == (20, 20)

    def test_zero_total_unfiltered_empty_state(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 0},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies")
        assert resp.status_code == 200
        assert b"No companies found" in resp.data
        assert b"Create your first company using the Add Company form." in resp.data

    def test_filtered_zero_empty_state(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 0},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?q=NonexistentCorp")
        assert resp.status_code == 200
        assert b"No companies match your filters" in resp.data
        assert b"Clear Filters" in resp.data


# ==============================================================================
# 3. SEARCH TESTS
# ==============================================================================
class TestAdminCompaniesSearch:
    def test_search_by_name(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 1},
        ]
        mock_db.fetchall.return_value = [
            {
                "id": 1,
                "name": "Google",
                "description": "",
                "website": "https://google.com",
                "is_active": True,
                "recruiter_count": 5,
            }
        ]

        resp = client.get("/admin/companies?q=Google")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
        sql, params = count_call
        assert "(c.name LIKE %s ESCAPE '=' OR c.website LIKE %s ESCAPE '=')" in sql
        assert params == ("%Google%", "%Google%")

    def test_search_by_website(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 1},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?q=example.org")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
        assert count_call[1] == ("%example.org%", "%example.org%")

    def test_search_wildcard_escaping(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 0},
        ]
        mock_db.fetchall.return_value = []

        # Literal %, _, and = in query
        resp = client.get("/admin/companies?q=100%_val=test")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
        # '=' escapes to '==', '%' to '=%', '_' to '=_'
        expected_pattern = "%100=%=_val==test%"
        assert count_call[1] == (expected_pattern, expected_pattern)

    def test_search_query_clamped_to_100_chars(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 0},
        ]
        mock_db.fetchall.return_value = []

        long_q = "a" * 150
        resp = client.get(f"/admin/companies?q={long_q}")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
        expected_pattern = f"%{'a' * 100}%"
        assert count_call[1] == (expected_pattern, expected_pattern)

    def test_search_does_not_search_description(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 0},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?q=something")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
        assert "c.description" not in count_call[0]


# ==============================================================================
# 4. STATUS FILTER TESTS
# ==============================================================================
class TestAdminCompaniesStatusFilter:
    def test_filter_active(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 2},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?status=active")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
        assert "c.is_active = TRUE" in count_call[0]

    def test_filter_inactive(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 1},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?status=inactive")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
        assert "c.is_active = FALSE" in count_call[0]

    def test_filter_all_or_invalid_normalizes(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        for status_val in ["all", "invalid_status", ""]:
            mock_db.execute.reset_mock()
            mock_db.fetchone.side_effect = [
                {"email": "admin@company.com", "is_active": True},
                {"total": 3},
            ]
            mock_db.fetchall.return_value = []

            resp = client.get(f"/admin/companies?status={status_val}")
            assert resp.status_code == 200
            calls = [c[0] for c in mock_db.execute.call_args_list]
            count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
            assert "c.is_active" not in count_call[0]

    def test_combined_search_and_status(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 1},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?q=tech&status=active")
        assert resp.status_code == 200
        calls = [c[0] for c in mock_db.execute.call_args_list]
        count_call = [c for c in calls if "COUNT(*)" in c[0]][0]
        sql = count_call[0]
        assert "(c.name LIKE %s ESCAPE '=' OR c.website LIKE %s ESCAPE '=')" in sql
        assert "c.is_active = TRUE" in sql
        assert " AND " in sql


# ==============================================================================
# 5. STATUS MUTATION TESTS & CONCURRENCY
# ==============================================================================
class TestAdminCompanyStatusMutation:
    def test_deactivate_active_company(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},  # auth
            {"id": 10, "name": "MegaCorp", "is_active": True},  # lookup
        ]
        mock_db.rowcount = 1

        resp = client.post("/admin/companies/10/status", data={"status": "inactive"}, follow_redirects=False)
        assert resp.status_code == 302
        assert "/admin/companies" in resp.headers["Location"]

        # Atomic update with current-state predicate
        update_calls = [c for c in mock_db.execute.call_args_list if "UPDATE companies SET is_active = %s" in c[0][0]]
        assert len(update_calls) == 1
        sql, params = update_calls[0][0]
        assert "WHERE id = %s AND is_active = %s" in sql
        assert params == (False, 10, True)

        # Audit log verification
        audit_calls = [c for c in mock_db.execute.call_args_list if "INSERT INTO audit_logs" in c[0][0]]
        assert len(audit_calls) == 1
        audit_params = audit_calls[0][0][1]
        assert audit_params[1] == "update_company_status"
        assert audit_params[2] == "company"
        assert audit_params[3] == 10
        details = json.loads(audit_params[4])
        assert details == {
            "is_active_before": True,
            "is_active_after": False,
            "company_name": "MegaCorp",
        }

    def test_activate_inactive_company(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"id": 10, "name": "MegaCorp", "is_active": False},
        ]
        mock_db.rowcount = 1

        resp = client.post("/admin/companies/10/status", data={"status": "active"}, follow_redirects=False)
        assert resp.status_code == 302

        update_calls = [c for c in mock_db.execute.call_args_list if "UPDATE companies SET is_active = %s" in c[0][0]]
        assert len(update_calls) == 1
        sql, params = update_calls[0][0]
        assert params == (True, 10, False)

        audit_calls = [c for c in mock_db.execute.call_args_list if "INSERT INTO audit_logs" in c[0][0]]
        assert len(audit_calls) == 1
        details = json.loads(audit_calls[0][0][1][4])
        assert details == {
            "is_active_before": False,
            "is_active_after": True,
            "company_name": "MegaCorp",
        }

    def test_same_state_idempotent_no_update_no_audit(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"id": 10, "name": "MegaCorp", "is_active": True},
        ]

        resp = client.post("/admin/companies/10/status", data={"status": "active"}, follow_redirects=False)
        assert resp.status_code == 302

        for call in mock_db.execute.call_args_list:
            assert "UPDATE companies" not in call[0][0]
            assert "INSERT INTO audit_logs" not in call[0][0]

    def test_nonexistent_company_returns_error(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            None,  # company not found
        ]

        resp = client.post("/admin/companies/999/status", data={"status": "inactive"}, follow_redirects=False)
        assert resp.status_code == 302
        for call in mock_db.execute.call_args_list:
            assert "UPDATE companies" not in call[0][0]
            assert "INSERT INTO audit_logs" not in call[0][0]

    def test_invalid_status_value_rejected(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        resp = client.post("/admin/companies/10/status", data={"status": "delete"}, follow_redirects=False)
        assert resp.status_code == 302
        for call in mock_db.execute.call_args_list:
            assert "UPDATE companies" not in call[0][0]
            assert "INSERT INTO audit_logs" not in call[0][0]

    def test_atomic_update_concurrency_zero_rowcount_handled(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"id": 10, "name": "MegaCorp", "is_active": True},
        ]
        # Simulate concurrent update that modified the row prior to this execution
        mock_db.rowcount = 0

        resp = client.post("/admin/companies/10/status", data={"status": "inactive"}, follow_redirects=False)
        assert resp.status_code == 302

        # No audit event should be logged when rowcount == 0
        for call in mock_db.execute.call_args_list:
            assert "INSERT INTO audit_logs" not in call[0][0]


# ==============================================================================
# 6. NO CASCADE TESTS
# ==============================================================================
class TestAdminCompanyNoCascade:
    def test_deactivate_does_not_mutate_other_tables(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"id": 10, "name": "MegaCorp", "is_active": True},
        ]
        mock_db.rowcount = 1

        resp = client.post("/admin/companies/10/status", data={"status": "inactive"}, follow_redirects=False)
        assert resp.status_code == 302

        # Assert no queries touching users, jobs, applications, interviews
        for call in mock_db.execute.call_args_list:
            sql = call[0][0].upper()
            if "UPDATE" in sql or "DELETE" in sql:
                assert "USERS" not in sql
                assert "JOBS" not in sql
                assert "APPLICATIONS" not in sql
                assert "INTERVIEWS" not in sql


# ==============================================================================
# 7. ASSIGNMENT REGRESSION TESTS
# ==============================================================================
class TestAdminAssignmentRegression:
    def test_inactive_company_cannot_receive_new_assignment(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"id": 2, "role": "recruiter", "company_id": None},
            {"id": 5, "is_active": False},  # inactive company
        ]

        resp = client.post("/admin/users/2/company", data={"company_id": "5"}, follow_redirects=False)
        assert resp.status_code == 302
        for call in mock_db.execute.call_args_list:
            assert "UPDATE users SET company_id" not in call[0][0]

    def test_unassign_recruiter_remains_supported(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"id": 2, "role": "recruiter", "company_id": 5},
        ]

        resp = client.post("/admin/users/2/company", data={"company_id": ""}, follow_redirects=False)
        assert resp.status_code == 302
        update_calls = [c for c in mock_db.execute.call_args_list if "UPDATE users SET company_id = %s" in c[0][0]]
        assert len(update_calls) == 1
        assert update_calls[0][0][1] == (None, 2)

    def test_reassign_to_active_company_remains_supported(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"id": 2, "role": "recruiter", "company_id": 5},
            {"id": 8, "is_active": True},
        ]

        resp = client.post("/admin/users/2/company", data={"company_id": "8"}, follow_redirects=False)
        assert resp.status_code == 302
        update_calls = [c for c in mock_db.execute.call_args_list if "UPDATE users SET company_id = %s" in c[0][0]]
        assert len(update_calls) == 1
        assert update_calls[0][0][1] == (8, 2)


# ==============================================================================
# 8. AUDIT SERVICE & VIEWER TESTS
# ==============================================================================
class TestAdminCompanyAuditIntegration:
    def test_audit_action_label_mapped(self):
        assert "update_company_status" in AUDIT_ACTION_LABELS
        assert AUDIT_ACTION_LABELS["update_company_status"] == "Company Status Updated"
        assert "is_active_before" in VIEWER_SAFE_DETAILS_ALLOWLIST
        assert "is_active_after" in VIEWER_SAFE_DETAILS_ALLOWLIST
        assert "company_name" in VIEWER_SAFE_DETAILS_ALLOWLIST

    def test_viewer_safe_details_parsing(self):
        raw_details = json.dumps(
            {
                "is_active_before": True,
                "is_active_after": False,
                "company_name": "Acme Global",
                "unwanted_secret": "drop_me",
            }
        )
        parsed = _parse_audit_safe_details(raw_details)
        labels = [p["label"] for p in parsed]
        values = [p["value"] for p in parsed]

        assert "Previous Status" in labels
        assert "New Status" in labels
        assert "Company Name" in labels
        assert "Active" in values
        assert "Inactive" in values
        assert "Acme Global" in values
        assert "unwanted_secret" not in [p.get("key") for p in parsed]


# ==============================================================================
# 9. VALIDATION TESTS
# ==============================================================================
class TestAdminCompanyValidation:
    def test_create_company_website_length_limit(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        # Website exceeding 255 chars
        long_website = "https://example.com/" + "a" * 250
        assert len(long_website) > 255

        resp = client.post(
            "/admin/companies/create",
            data={"name": "Valid Name", "website": long_website},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        for call in mock_db.execute.call_args_list:
            assert "INSERT INTO companies" not in call[0][0]

    def test_edit_company_website_length_limit(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

        long_website = "https://example.com/" + "b" * 250
        assert len(long_website) > 255

        resp = client.post(
            "/admin/companies/1/edit",
            data={"name": "Valid Name", "website": long_website},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        for call in mock_db.execute.call_args_list:
            assert "UPDATE companies SET name = %s" not in call[0][0]

    def test_duplicate_company_name_allowed(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.return_value = {"email": "admin@company.com", "is_active": True}
        mock_db.lastrowid = 12

        resp = client.post(
            "/admin/companies/create",
            data={"name": "Duplicate Co", "website": "https://dup.com"},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        insert_calls = [c for c in mock_db.execute.call_args_list if "INSERT INTO companies" in c[0][0]]
        assert len(insert_calls) == 1


# ==============================================================================
# 10. REUSABLE MODAL & XSS TEMPLATE SAFETY TESTS
# ==============================================================================
class TestAdminCompanyTemplateAndModal:
    def test_single_reusable_modal_and_data_attributes(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 2},
        ]
        mock_db.fetchall.return_value = [
            {
                "id": 1,
                "name": "First Corp",
                "description": "Desc 1",
                "website": "https://first.com",
                "is_active": True,
                "created_at": None,
                "updated_at": None,
                "recruiter_count": 1,
            },
            {
                "id": 2,
                "name": "Second Corp",
                "description": "Desc 2",
                "website": "https://second.com",
                "is_active": False,
                "created_at": None,
                "updated_at": None,
                "recruiter_count": 0,
            },
        ]

        resp = client.get("/admin/companies")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")

        # Exactly ONE modal with id="companyEditModal"
        assert html.count('id="companyEditModal"') == 1

        # Buttons carry data-edit-url from url_for
        assert 'data-edit-url="/admin/companies/1/edit' in html
        assert 'data-edit-url="/admin/companies/2/edit' in html

        # No hardcoded JavaScript route string
        assert "/admin/companies/${id}/edit" not in html
        assert "innerHTML" not in html

    def test_xss_escaping_in_template(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 1},
        ]
        mock_db.fetchall.return_value = [
            {
                "id": 99,
                "name": "<script>alert('xss_name')</script>",
                "description": "<img src=x onerror=alert('xss_desc')>",
                "website": "https://xss-test.com",
                "is_active": True,
                "created_at": None,
                "updated_at": None,
                "recruiter_count": 0,
            }
        ]

        resp = client.get("/admin/companies")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")

        # Must be escaped, raw script must NOT execute unescaped
        assert "<script>alert('xss_name')</script>" not in html
        assert "&lt;script&gt;alert(&#39;xss_name&#39;)&lt;/script&gt;" in html or "&lt;script&gt;" in html
        assert "<img src=x" not in html


# ==============================================================================
# 11. FILTER PRESERVATION TESTS
# ==============================================================================
class TestAdminCompanyFilterPreservation:
    def test_pagination_links_preserve_filters(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"total": 60},
        ]
        mock_db.fetchall.return_value = []

        resp = client.get("/admin/companies?q=tech&status=active&per_page=20&page=1")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")

        # Page 2 link should preserve q and status
        assert "q=tech" in html
        assert "status=active" in html
        assert "per_page=20" in html

    def test_status_redirect_preserves_normalized_filters(self, client, mock_db):
        _login_as(client, email="admin@company.com")
        mock_db.fetchone.side_effect = [
            {"email": "admin@company.com", "is_active": True},
            {"id": 5, "name": "PreserveCo", "is_active": True},
        ]
        mock_db.rowcount = 1

        resp = client.post(
            "/admin/companies/5/status",
            data={
                "status": "inactive",
                "q": "tech",
                "filter_status": "active",
                "page": "2",
                "per_page": "50",
                "injected_arbitrary_key": "drop_this",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        location = resp.headers["Location"]
        assert "q=tech" in location
        assert "status=active" in location
        assert "page=2" in location
        assert "per_page=50" in location
        assert "injected_arbitrary_key" not in location
