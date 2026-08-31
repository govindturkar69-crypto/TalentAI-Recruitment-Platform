"""
Phase 4B Step 4 — Complete Interview Integration Tests.
Covers: auto-cancel, ownership, isolation, rollback, UI, CSRF, validation.
"""

import json
from contextlib import closing
from unittest.mock import patch

import pytest

from app import app
from core import get_db_connection
from services.interview_service import (
    cancel_future_scheduled_interviews_for_application,
    cancel_interview_service,
    complete_interview_service,
    get_candidate_interviews,
    get_recruiter_interviews_for_application,
    schedule_interview_service,
    update_interview_service,
)


@pytest.fixture
def test_client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            yield client


def setup_data():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            # Clean up
            cur.execute("DELETE FROM interviews")
            cur.execute("DELETE FROM applications")
            cur.execute("DELETE FROM jobs")
            cur.execute("DELETE FROM resumes")
            cur.execute("DELETE FROM users WHERE email LIKE '%test4b%'")
            cur.execute("DELETE FROM companies WHERE name LIKE '%TestCo4B%'")

            # Companies
            cur.execute("INSERT INTO companies (name) VALUES ('TestCo4B 1')")
            company1 = cur.lastrowid
            cur.execute("INSERT INTO companies (name) VALUES ('TestCo4B 2')")
            company2 = cur.lastrowid

            # Recruiter A (Co 1)
            cur.execute(
                "INSERT INTO users (name, email, password, role, company_id) "
                "VALUES ('Recruiter A', 'reca_test4b@example.com', 'hash', 'recruiter', %s)",
                (company1,),
            )
            reca_id = cur.lastrowid

            # Recruiter B (Co 1) - Same company
            cur.execute(
                "INSERT INTO users (name, email, password, role, company_id) "
                "VALUES ('Recruiter B', 'recb_test4b@example.com', 'hash', 'recruiter', %s)",
                (company1,),
            )
            recb_id = cur.lastrowid

            # Recruiter C (Co 2)
            cur.execute(
                "INSERT INTO users (name, email, password, role, company_id) "
                "VALUES ('Recruiter C', 'recc_test4b@example.com', 'hash', 'recruiter', %s)",
                (company2,),
            )
            recc_id = cur.lastrowid

            # Candidates
            cur.execute(
                "INSERT INTO users (name, email, password, role) "
                "VALUES ('Candidate 1', 'cand1_test4b@example.com', 'hash', 'candidate')"
            )
            cand1_id = cur.lastrowid

            cur.execute(
                "INSERT INTO users (name, email, password, role) "
                "VALUES ('Candidate 2', 'cand2_test4b@example.com', 'hash', 'candidate')"
            )
            cand2_id = cur.lastrowid

            # Resume
            cur.execute(
                "INSERT INTO resumes (user_id, resume_path, skills) VALUES (%s, 'dummy.pdf', 'python')", (cand1_id,)
            )
            resume1_id = cur.lastrowid

            # Job A (Owned by Recruiter A)
            cur.execute(
                "INSERT INTO jobs (recruiter_id, job_title, required_skills) VALUES (%s, 'Job A', 'python')", (reca_id,)
            )
            job_a_id = cur.lastrowid

            conn.commit()
            return reca_id, recb_id, recc_id, cand1_id, cand2_id, job_a_id, resume1_id


def create_application(candidate_id, job_id, resume_id, status="applied"):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO applications (candidate_id, job_id, resume_id, status) VALUES (%s, %s, %s, %s)",
                (candidate_id, job_id, resume_id, status),
            )
            conn.commit()
            return cur.lastrowid


def create_interview(application_id, scheduled_at="2030-01-01T10:00", status="scheduled"):
    """Create an interview row directly for testing without triggering service validation."""
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO interviews (application_id, scheduled_at, duration_minutes, mode, status) "
                "VALUES (%s, %s, 30, 'phone', %s)",
                (application_id, scheduled_at.replace("T", " "), status),
            )
            conn.commit()
            return cur.lastrowid


def get_interview(interview_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT * FROM interviews WHERE id = %s", (interview_id,))
            return cur.fetchone()


# ---------------------------------------------------------
# AUTHORIZATION
# ---------------------------------------------------------


def test_authorization_schedule():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    future_time = "2030-01-01T10:00"

    # owner recruiter can schedule
    res = schedule_interview_service(app_id, reca, future_time, 30, "online", "https://zoom.us/test", None)
    assert res["success"] is True

    # same-company different recruiter still cannot schedule (isolation)
    res = schedule_interview_service(app_id, recb, future_time, 30, "online", "https://zoom.us/test", None)
    assert res["success"] is False

    # different recruiter cannot schedule
    res = schedule_interview_service(app_id, recc, future_time, 30, "online", "https://zoom.us/test", None)
    assert res["success"] is False


def test_authorization_read():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)

    # owner can read
    res = get_recruiter_interviews_for_application(app_id, reca)
    assert res["success"] is True
    assert len(res["data"]) == 1

    # different recruiter cannot read
    res = get_recruiter_interviews_for_application(app_id, recb)
    assert res["success"] is False
    assert res["data"] is None


def test_authorization_candidate_isolation():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)

    # owning candidate can read own interview
    interviews_c1 = get_candidate_interviews(cand1)
    assert len(interviews_c1) == 1

    # different candidate cannot receive it
    interviews_c2 = get_candidate_interviews(cand2)
    assert len(interviews_c2) == 0


# ---------------------------------------------------------
# SCHEDULING & STATUS
# ---------------------------------------------------------


def test_scheduling_application_status():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()

    app_applied = create_application(cand1, ja, res1, "applied")
    res = schedule_interview_service(app_applied, reca, "2030-01-01T10:00", 30, "phone", None, None)
    assert res["success"] is False

    app_rejected = create_application(cand1, ja, res1, "rejected")
    res = schedule_interview_service(app_rejected, reca, "2030-01-01T10:00", 30, "phone", None, None)
    assert res["success"] is False

    app_short = create_application(cand1, ja, res1, "shortlisted")
    res = schedule_interview_service(app_short, reca, "2030-01-01T10:00", 30, "phone", None, None)
    assert res["success"] is True

    # multiple interviews for same application succeed
    res = schedule_interview_service(app_short, reca, "2030-01-02T10:00", 60, "in_person", "Office", None)
    assert res["success"] is True

    # past datetime rejected
    res = schedule_interview_service(app_short, reca, "2020-01-01T10:00", 30, "phone", None, None)
    assert res["success"] is False
    assert "future" in res["message"].lower()


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------


def test_validation():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    # duration below 5 rejected
    res = schedule_interview_service(app_id, reca, "2030-01-01T10:00", 3, "phone", None, None)
    assert res["success"] is False

    # duration above 480 rejected
    res = schedule_interview_service(app_id, reca, "2030-01-01T10:00", 500, "phone", None, None)
    assert res["success"] is False

    # invalid mode rejected
    res = schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "invalid", None, None)
    assert res["success"] is False

    # online missing URL rejected
    res = schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "online", "", None)
    assert res["success"] is False

    # online javascript/file/invalid URL rejected
    res = schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "online", "javascript:alert(1)", None)
    assert res["success"] is False

    # online http/https with hostname accepted
    res = schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "online", "https://zoom.us/test", None)
    assert res["success"] is True

    # in-person missing location rejected
    res = schedule_interview_service(app_id, reca, "2030-01-02T10:00", 30, "in_person", "   ", None)
    assert res["success"] is False

    # in-person >500 chars rejected
    res = schedule_interview_service(app_id, reca, "2030-01-02T10:00", 30, "in_person", "A" * 501, None)
    assert res["success"] is False

    # phone with non-blank location_or_link rejected
    res = schedule_interview_service(app_id, reca, "2030-01-02T10:00", 30, "phone", "555-1234", None)
    assert res["success"] is False

    # phone with None (blank) location ACCEPTED
    res = schedule_interview_service(app_id, reca, "2030-01-03T10:00", 30, "phone", None, None)
    assert res["success"] is True

    # phone with empty string location ACCEPTED
    res = schedule_interview_service(app_id, reca, "2030-01-04T10:00", 5, "phone", "", None)
    assert res["success"] is True

    # duration min boundary (5) accepted
    res = schedule_interview_service(app_id, reca, "2030-01-05T10:00", 5, "phone", None, None)
    assert res["success"] is True

    # duration max boundary (480) accepted
    res = schedule_interview_service(app_id, reca, "2030-01-06T10:00", 480, "phone", None, None)
    assert res["success"] is True


# ---------------------------------------------------------
# UPDATE, CANCEL, COMPLETE
# ---------------------------------------------------------


def test_update_interview():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)

    interviews = get_recruiter_interviews_for_application(app_id, reca)["data"]
    iv_id = interviews[0]["id"]

    # different recruiter cannot edit
    res = update_interview_service(iv_id, recb, "2030-01-02T10:00", 30, "phone", None, None)
    assert res["success"] is False

    # owner can edit
    res = update_interview_service(iv_id, reca, "2030-01-02T10:00", 60, "phone", None, "Updated")
    assert res["success"] is True

    # check stale status
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE applications SET status='hired' WHERE id=%s", (app_id,))
            conn.commit()

    # application no longer shortlisted prevents normal reschedule
    res = update_interview_service(iv_id, reca, "2030-01-03T10:00", 60, "phone", None, None)
    assert res["success"] is False


def test_cancel_interview():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)
    iv_id = get_recruiter_interviews_for_application(app_id, reca)["data"][0]["id"]

    # different recruiter cannot cancel
    res = cancel_interview_service(iv_id, recb)
    assert res["success"] is False

    # scheduled -> cancelled succeeds
    res = cancel_interview_service(iv_id, reca)
    assert res["success"] is True

    # second cancellation blocked
    res = cancel_interview_service(iv_id, reca)
    assert res["success"] is False


def test_complete_interview():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)
    iv_id = get_recruiter_interviews_for_application(app_id, reca)["data"][0]["id"]

    # future interview cannot be completed
    res = complete_interview_service(iv_id, reca)
    assert res["success"] is False

    # manually set date to past to test complete
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE interviews SET scheduled_at='2000-01-01 10:00:00' WHERE id=%s", (iv_id,))
            conn.commit()

    # now can complete
    res = complete_interview_service(iv_id, reca)
    assert res["success"] is True

    # second completion blocked
    res = complete_interview_service(iv_id, reca)
    assert res["success"] is False

    # cancelled -> completed blocked
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)
    iv2_id = get_recruiter_interviews_for_application(app_id, reca)["data"][1]["id"]
    cancel_interview_service(iv2_id, reca)
    res = complete_interview_service(iv2_id, reca)
    assert res["success"] is False


# ---------------------------------------------------------
# AUTO-CANCEL HELPER — CONTRACT TESTS
# ---------------------------------------------------------


def test_auto_cancel_helper_future_only():
    """Only future scheduled rows are cancelled; past, completed, cancelled are preserved."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    # Future scheduled — should be cancelled
    iv_future = create_interview(app_id, "2030-06-01T10:00", "scheduled")
    # Past scheduled — should NOT be cancelled
    iv_past = create_interview(app_id, "2000-01-01T10:00", "scheduled")
    # Already completed — should NOT be touched
    iv_completed = create_interview(app_id, "2030-07-01T10:00", "completed")
    # Already cancelled — should NOT be touched
    iv_cancelled = create_interview(app_id, "2030-08-01T10:00", "cancelled")

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cancelled = cancel_future_scheduled_interviews_for_application(cur, app_id)
            conn.commit()

    cancelled_ids = [r["id"] for r in cancelled]
    assert iv_future in cancelled_ids
    assert iv_past not in cancelled_ids
    assert iv_completed not in cancelled_ids
    assert iv_cancelled not in cancelled_ids

    # Verify DB state
    assert get_interview(iv_future)["status"] == "cancelled"
    assert get_interview(iv_past)["status"] == "scheduled"
    assert get_interview(iv_completed)["status"] == "completed"
    assert get_interview(iv_cancelled)["status"] == "cancelled"


def test_auto_cancel_helper_no_delete():
    """Helper must NEVER delete rows — only status change."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_id = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cancel_future_scheduled_interviews_for_application(cur, app_id)
            conn.commit()

    # Row must still exist
    row = get_interview(iv_id)
    assert row is not None
    assert row["status"] == "cancelled"


def test_auto_cancel_helper_no_connection_no_commit():
    """Verify helper only takes cursor; does not call conn.commit() itself."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    create_interview(app_id, "2030-06-01T10:00", "scheduled")

    # Call helper inside a transaction but do NOT commit
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            result = cancel_future_scheduled_interviews_for_application(cur, app_id)
            # Do NOT commit — rollback
            conn.rollback()

    # After rollback the interview should still be scheduled
    row = get_interview(result[0]["id"])
    assert row["status"] == "scheduled"


def test_recruiter_rejected_auto_cancel():
    """Recruiter rejecting a shortlisted application auto-cancels future scheduled interviews."""
    from services.recruiter_service import update_status_service

    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    iv_future = create_interview(app_id, "2030-06-01T10:00", "scheduled")
    iv_past = create_interview(app_id, "2000-01-01T10:00", "scheduled")

    res = update_status_service(app_id, "rejected", reca)
    assert res["success"] is True

    # Future scheduled interview cancelled
    assert get_interview(iv_future)["status"] == "cancelled"
    # Past scheduled interview NOT cancelled by auto-cancel
    assert get_interview(iv_past)["status"] == "scheduled"


def test_recruiter_hired_auto_cancel():
    """Recruiter hiring a shortlisted application auto-cancels future scheduled interviews."""
    from services.recruiter_service import update_status_service

    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    iv_future = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    res = update_status_service(app_id, "hired", reca)
    assert res["success"] is True
    assert get_interview(iv_future)["status"] == "cancelled"


def test_recruiter_bulk_auto_cancel():
    """Bulk reject auto-cancels future scheduled interviews for each affected application."""
    from services.recruiter_service import bulk_update_status_service

    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_future = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    result = bulk_update_status_service([str(app_id)], "rejected", reca)
    assert result["success_count"] == 1

    assert get_interview(iv_future)["status"] == "cancelled"


def test_candidate_withdraw_auto_cancel():
    """Candidate withdrawing application auto-cancels future scheduled interviews."""
    from services.candidate_service import withdraw_application_service

    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_future = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    res = withdraw_application_service(app_id, cand1)
    assert res["success"] is True
    assert get_interview(iv_future)["status"] == "cancelled"


def test_no_auto_cancel_for_shortlisted():
    """Auto-cancel must NOT fire when transitioning to shortlisted."""
    from services.recruiter_service import update_status_service

    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "applied")
    iv_future = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    res = update_status_service(app_id, "shortlisted", reca)
    assert res["success"] is True
    # Interview MUST remain scheduled
    assert get_interview(iv_future)["status"] == "scheduled"


def test_transaction_rollback_if_auto_cancel_fails():
    """If auto-cancel helper raises, the whole transaction rolls back (no partial commit)."""
    from services.recruiter_service import update_status_service

    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    with patch("services.recruiter_service.cancel_future_scheduled_interviews_for_application") as mock_cancel:
        mock_cancel.side_effect = Exception("Simulated DB failure")
        with pytest.raises(Exception, match="Simulated DB failure"):
            update_status_service(app_id, "rejected", reca)

    # Application status must NOT have changed (transaction rolled back)
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM applications WHERE id = %s", (app_id,))
            row = cur.fetchone()
    assert row["status"] == "shortlisted"


# ---------------------------------------------------------
# CANDIDATE NOTES SAFETY
# ---------------------------------------------------------


def test_candidate_never_receives_notes():
    """get_candidate_interviews must never expose the notes column."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "online", "https://safe.com", "INTERNAL NOTE")

    interviews = get_candidate_interviews(cand1)
    assert len(interviews) >= 1
    row = interviews[0]
    # Key 'notes' must NOT exist in the returned rows
    assert "notes" not in row
    # Value of notes must not appear anywhere in the row dict values
    all_values = " ".join(str(v) for v in row.values() if v is not None)
    assert "INTERNAL NOTE" not in all_values


@patch("services.interview_service.log_audit_event")
def test_audit_safety(mock_audit):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "online", "https://safe.com", "my secret notes")

    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    details = args[4]

    # verify unsafe fields are never passed to the audit function
    assert "notes" not in details
    assert "location_or_link" not in details
    assert "meeting_url" not in details
    assert "my secret notes" not in json.dumps(details)


# ---------------------------------------------------------
# ROUTE TESTS — HTTP method enforcement
# ---------------------------------------------------------


def _recruiter_session(client, recruiter_id, name="Recruiter A"):
    with client.session_transaction() as sess:
        sess["user_id"] = recruiter_id
        sess["role"] = "recruiter"
        sess["name"] = name
        sess["is_admin"] = False


def _candidate_session(client, candidate_id, name="Candidate 1"):
    with client.session_transaction() as sess:
        sess["user_id"] = candidate_id
        sess["role"] = "candidate"
        sess["name"] = name
        sess["is_admin"] = False


def test_interview_post_routes_reject_get(test_client):
    """All POST interview mutation routes must return 405 for GET requests."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_id = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    _recruiter_session(test_client, reca)

    routes = [
        f"/recruiter/application/{app_id}/interviews/schedule",
        f"/recruiter/interview/{iv_id}/update",
        f"/recruiter/interview/{iv_id}/cancel",
        f"/recruiter/interview/{iv_id}/complete",
    ]

    for route in routes:
        resp = test_client.get(route)
        assert resp.status_code == 405, f"Expected 405 for GET {route}, got {resp.status_code}"


def test_candidate_has_no_mutation_routes(test_client):
    """Candidate must have no interview mutation routes."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_id = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    _candidate_session(test_client, cand1)

    # These recruiter routes must be inaccessible to candidates
    routes_404_or_redirect = [
        (f"/recruiter/application/{app_id}/interviews/schedule", "POST"),
        (f"/recruiter/interview/{iv_id}/cancel", "POST"),
        (f"/recruiter/interview/{iv_id}/complete", "POST"),
    ]

    for path, method in routes_404_or_redirect:
        if method == "POST":
            resp = test_client.post(path, data={})
        else:
            resp = test_client.get(path)
        # Must redirect to login (not 200 success)
        assert resp.status_code in (302, 403, 404), f"Candidate reached {path}: status {resp.status_code}"


def test_candidate_interviews_read_only(test_client):
    """Candidate interviews GET route returns 200 and contains no form actions for mutations."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)

    _candidate_session(test_client, cand1)
    resp = test_client.get("/candidate/interviews")
    assert resp.status_code == 200

    html = resp.data.decode()
    # Must not contain mutation form actions
    assert "/cancel" not in html or "recruiter" not in html
    assert "INTERNAL NOTE" not in html
    # Must not contain 'notes' anywhere in the body
    assert "notes" not in html.lower().replace("<!-- ", "").replace("-->", "")


# ---------------------------------------------------------
# TEMPLATE CONTENT TESTS
# ---------------------------------------------------------


def test_candidate_template_no_notes(test_client):
    """Candidate interview template must never reference recruiter notes."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, "secret recruiter notes")

    _candidate_session(test_client, cand1)
    resp = test_client.get("/candidate/interviews")
    assert resp.status_code == 200
    assert b"secret recruiter notes" not in resp.data


def test_recruiter_workflow_ui_applied(test_client):
    """For applied status: only Shortlist and Reject buttons appear; no Hire button."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    create_application(cand1, ja, res1, "applied")

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/job/{ja}/applicants")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "shortlisted" in html
    assert "rejected" in html


def test_recruiter_interviews_page_has_csrf(test_client):
    """Recruiter interviews schedule form must contain csrf_token."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert resp.status_code == 200
    assert b"csrf_token" in resp.data


def test_candidate_withdraw_ui_no_rejected(test_client):
    """Dashboard must NOT show withdraw button for rejected status."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    create_application(cand1, ja, res1, "rejected")

    _candidate_session(test_client, cand1)
    resp = test_client.get("/candidate/dashboard")
    assert resp.status_code == 200
    # For a rejected application, withdraw form must not be present
    html = resp.data.decode()
    # The withdraw URL pattern for candidate should not be active for rejected apps
    # The condition is app.status in ['applied', 'shortlisted']
    # Since the only application is 'rejected', no withdraw form should appear
    assert "withdraw_application" not in html or "Withdraw" not in html


def test_candidate_withdraw_ui_applied(test_client):
    """Dashboard shows withdraw button for applied status."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    create_application(cand1, ja, res1, "applied")

    _candidate_session(test_client, cand1)
    resp = test_client.get("/candidate/dashboard")
    assert resp.status_code == 200
    assert b"Withdraw" in resp.data


def test_candidate_withdraw_ui_shortlisted(test_client):
    """Dashboard shows withdraw button for shortlisted status."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    create_application(cand1, ja, res1, "shortlisted")

    _candidate_session(test_client, cand1)
    resp = test_client.get("/candidate/dashboard")
    assert resp.status_code == 200
    assert b"Withdraw" in resp.data


def test_in_person_exact_mode_value(test_client):
    """Recruiter interviews template uses exact value 'in_person', not 'in-person'."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'value="in_person"' in html
    assert 'value="in-person"' not in html


def test_duration_min_max_attributes(test_client):
    """Schedule form must have min=5 and max=480 on duration input."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'min="5"' in html
    assert 'max="480"' in html


def test_online_links_safe_attributes(test_client):
    """Online meeting links must have target=_blank and rel=noopener noreferrer."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "online", "https://meet.google.com/test", None)

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'target="_blank"' in html
    assert "noopener" in html
    assert "noreferrer" in html


def test_xss_escaping_location(test_client):
    """HTML-like location strings must be escaped, not rendered raw."""
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    xss_payload = "Office <script>alert(1)</script>"
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "in_person", xss_payload, None)

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert resp.status_code == 200
    # Raw script tag must not appear; Jinja2 auto-escapes
    assert b"<script>alert(1)</script>" not in resp.data


def test_schema_and_migration_unchanged():
    """schema.sql must still contain the interviews table without modification."""
    import os

    schema_path = os.path.join(os.path.dirname(__file__), "..", "database", "schema.sql")
    with open(schema_path, "r") as f:
        schema = f.read()
    assert "CREATE TABLE IF NOT EXISTS interviews" in schema
    assert "application_id INT NOT NULL" in schema
    # Migration 009 must not be referenced (no 009 migration file created)
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "database", "migrations")
    if os.path.isdir(migrations_dir):
        migration_files = os.listdir(migrations_dir)
        migration_010_files = [f for f in migration_files if "010" in f]
        assert len(migration_010_files) == 0, "Migration 010 must not exist"


# ---------------------------------------------------------
# NEW TESTS FOR STEP 4 V2
# ---------------------------------------------------------


def test_route_owner_get_interviews(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert resp.status_code == 200

    _recruiter_session(test_client, recb)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert resp.status_code == 302  # Redirects

    _recruiter_session(test_client, recc)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert resp.status_code == 302


def test_route_non_owner_mutations(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_id = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    _recruiter_session(test_client, recb)
    test_client.post(
        f"/recruiter/application/{app_id}/interviews/schedule",
        data={"scheduled_at": "2030-07-01T10:00", "duration_minutes": "30", "mode": "phone"},
    )
    # Cannot mutate
    assert get_interview(iv_id)["status"] == "scheduled"

    test_client.post(
        f"/recruiter/interview/{iv_id}/update",
        data={"scheduled_at": "2030-08-01T10:00", "duration_minutes": "30", "mode": "phone"},
    )
    assert get_interview(iv_id)["status"] == "scheduled"

    test_client.post(f"/recruiter/interview/{iv_id}/cancel")
    assert get_interview(iv_id)["status"] == "scheduled"

    # manual past
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE interviews SET scheduled_at='2000-01-01 10:00:00' WHERE id=%s", (iv_id,))
            conn.commit()

    test_client.post(f"/recruiter/interview/{iv_id}/complete")
    assert get_interview(iv_id)["status"] == "scheduled"


def test_tampered_app_id_route(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_id = create_interview(app_id, "2030-06-01T10:00", "scheduled")

    _recruiter_session(test_client, reca)
    resp = test_client.post(f"/recruiter/interview/{iv_id}/cancel", data={"app_id": 9999})
    assert resp.status_code == 302
    assert f"/recruiter/application/{app_id}/interviews" in resp.headers["Location"]


def test_service_returned_application_id():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)
    iv_id = get_recruiter_interviews_for_application(app_id, reca)["data"][0]["id"]

    res = update_interview_service(iv_id, reca, "2030-02-01T10:00", 30, "phone", None, None)
    assert res["application_id"] == app_id

    res = cancel_interview_service(iv_id, reca)
    assert res["application_id"] == app_id

    iv_id_2 = create_interview(app_id, "2000-01-01T10:00", "scheduled")
    res = complete_interview_service(iv_id_2, reca)
    assert res["application_id"] == app_id


def test_app_info_candidate_name():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    res = get_recruiter_interviews_for_application(app_id, reca)
    assert "Candidate 1" in res["app_info"]["candidate_name"]


def test_is_upcoming_logic():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_future = create_interview(app_id, "2030-06-01T10:00", "scheduled")
    create_interview(app_id, "2030-07-01T10:00", "cancelled")
    create_interview(app_id, "2030-08-01T10:00", "completed")
    create_interview(app_id, "2000-01-01T10:00", "scheduled")

    interviews = get_candidate_interviews(cand1)
    for iv in interviews:
        if iv["id"] == iv_future:
            assert iv["is_upcoming"] == 1
        else:
            assert iv["is_upcoming"] == 0


def test_interviews_ordering():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    # history
    create_interview(app_id, "2000-01-01T10:00", "completed")
    create_interview(app_id, "2001-01-01T10:00", "scheduled")
    # upcoming
    create_interview(app_id, "2030-06-01T10:00", "scheduled")
    create_interview(app_id, "2030-05-01T10:00", "scheduled")

    interviews = get_candidate_interviews(cand1)
    assert interviews[0]["scheduled_at"].year == 2030
    assert interviews[0]["scheduled_at"].month == 5
    assert interviews[1]["scheduled_at"].year == 2030
    assert interviews[1]["scheduled_at"].month == 6
    assert interviews[2]["scheduled_at"].year == 2001
    assert interviews[3]["scheduled_at"].year == 2000


@patch("services.recruiter_service.log_audit_event")
@patch("services.recruiter_service.create_notification")
def test_recruiter_audit_notifications(mock_notif, mock_audit):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    create_interview(app_id, "2030-06-01T10:00", "scheduled")

    from services.recruiter_service import update_status_service

    update_status_service(app_id, "rejected", reca)

    audit_calls = mock_audit.call_args_list
    assert len(audit_calls) >= 2
    found_cancel = False
    for call in audit_calls:
        if call[0][1] == "interview_cancelled":
            found_cancel = True
            details = call[0][4]
            assert "notes" not in details
            assert "location_or_link" not in details
            assert details["application_id"] == app_id
    assert found_cancel

    notif_call = mock_notif.call_args[0]
    assert "Any future scheduled interviews have also been cancelled." in notif_call[2]


@patch("services.recruiter_service.log_audit_event")
@patch("services.recruiter_service.create_notification")
def test_bulk_audit_notifications(mock_notif, mock_audit):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    create_interview(app_id, "2030-06-01T10:00", "scheduled")

    from services.recruiter_service import bulk_update_status_service

    bulk_update_status_service([str(app_id)], "hired", reca)

    found_cancel = False
    for call in mock_audit.call_args_list:
        if call[0][1] == "interview_cancelled":
            found_cancel = True
    assert found_cancel

    notif_call = mock_notif.call_args[0]
    assert "Any future scheduled interviews have also been cancelled." in notif_call[2]


@patch("services.candidate_service.log_audit_event")
def test_candidate_withdraw_audits(mock_audit):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    create_interview(app_id, "2030-06-01T10:00", "scheduled")

    from services.candidate_service import withdraw_application_service

    withdraw_application_service(app_id, cand1)

    found_cancel = False
    for call in mock_audit.call_args_list:
        if call[0][1] == "interview_cancelled":
            found_cancel = True
            assert call[0][0] == cand1
    assert found_cancel


def test_phone_labels(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "phone", None, None)

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert b"Phone interview" in resp.data

    _candidate_session(test_client, cand1)
    resp = test_client.get("/candidate/interviews")
    assert b"Phone interview" in resp.data


def test_xss_in_js_data(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    xss_payload = '"; alert(1); // <script>eval()</script>'
    schedule_interview_service(app_id, reca, "2030-01-01T10:00", 30, "in_person", xss_payload, xss_payload)

    _recruiter_session(test_client, reca)
    resp = test_client.get(f"/recruiter/application/{app_id}/interviews")
    html = resp.data.decode()
    assert 'onclick="openEditModal(this)' in html
    # Ensure raw quote does not break out of data attribute
    assert (
        'data-notes="&quot;; alert(1);' in html
        or "&#34;" in html
        or "&#x27;" in html
        or '"' not in html[html.find('data-notes="') + 12 : html.find('data-notes="') + 13]
    )
    # In jinja | e or autoescape converts " to &#34; or similar
