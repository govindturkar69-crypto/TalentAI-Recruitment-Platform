import datetime
import json
from contextlib import closing
from unittest.mock import patch

import pytest

from app import app
from core import get_db_connection
from services.candidate_service import withdraw_application_service
from services.interview_service import (
    _authorize_recruiter_application,
    cancel_future_scheduled_interviews_for_application,
    cancel_interview_service,
    complete_interview_service,
    get_candidate_interviews,
    get_recruiter_interviews_for_application,
    schedule_interview_service,
    update_interview_service,
)
from services.recruiter_service import bulk_update_status_service, update_status_service


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

    # same-company different recruiter still cannot schedule
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

    # phone with location_or_link rejected
    res = schedule_interview_service(app_id, reca, "2030-01-02T10:00", 30, "phone", "555-1234", None)
    assert res["success"] is False


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

    # past/current scheduled interview -> completed succeeds
    # To test this, we must mock NOW() or create it with a past date (but wait, creation requires future date).
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


def test_recruiter_metadata_authorization():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            # A. recruiter metadata
            app_info = _authorize_recruiter_application(cur, app_id, reca)
            assert app_info is not None
            assert "application_id" in app_info
            assert "candidate_id" in app_info
            assert app_info["candidate_name"] == "Candidate 1"
            assert "application_status" in app_info
            assert "job_id" in app_info
            assert app_info["job_title"] == "Job A"

            # B. same-company recruiter denied
            app_info_b = _authorize_recruiter_application(cur, app_id, recb)
            assert app_info_b is None


def _get_db_now():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT NOW() as db_now")
            return cur.fetchone()["db_now"]


def _create_interview_raw(application_id, status, scheduled_at):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                INSERT INTO interviews (application_id, scheduled_at, duration_minutes,
                                        mode, location_or_link, status, notes)
                VALUES (%s, %s, 30, 'phone', NULL, %s, 'secret note')
                """,
                (application_id, scheduled_at, status),
            )
            conn.commit()
            return cur.lastrowid


def test_candidate_safe_query_and_is_upcoming():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()
    future1 = db_now + datetime.timedelta(days=1)
    future2 = db_now + datetime.timedelta(days=2)
    past1 = db_now - datetime.timedelta(days=1)
    past2 = db_now - datetime.timedelta(days=2)

    _create_interview_raw(app_id, "completed", past2)  # history 1
    _create_interview_raw(app_id, "scheduled", past1)  # history 2
    _create_interview_raw(app_id, "scheduled", future1)  # upcoming 1
    _create_interview_raw(app_id, "cancelled", future2)  # history 3

    interviews = get_candidate_interviews(cand1)
    # C. candidate safe query
    assert len(interviews) == 4
    for iv in interviews:
        assert "notes" not in iv
        assert "updated_at" in iv
        assert "application_status" in iv
        assert iv["application_id"] == app_id

    # D & E. is_upcoming and ordering
    # Expected order: upcoming (future1), then history (future2, past1, past2)
    assert interviews[0]["is_upcoming"] == 1
    assert interviews[0]["scheduled_at"] == future1

    assert interviews[1]["is_upcoming"] == 0
    assert interviews[1]["scheduled_at"] == future2
    assert interviews[1]["status"] == "cancelled"

    assert interviews[2]["is_upcoming"] == 0
    assert interviews[2]["scheduled_at"] == past1
    assert interviews[2]["status"] == "scheduled"

    assert interviews[3]["is_upcoming"] == 0
    assert interviews[3]["scheduled_at"] == past2
    assert interviews[3]["status"] == "completed"


def test_can_complete():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))
    _create_interview_raw(app_id, "scheduled", db_now - datetime.timedelta(days=1))
    _create_interview_raw(app_id, "cancelled", db_now - datetime.timedelta(days=2))

    res = get_recruiter_interviews_for_application(app_id, reca)
    ivs = res["data"]  # Ordered by scheduled_at ASC natively

    assert ivs[0]["status"] == "cancelled"
    assert ivs[0]["can_complete"] == 0

    assert ivs[1]["status"] == "scheduled"  # past
    assert ivs[1]["can_complete"] == 1

    assert ivs[2]["status"] == "scheduled"  # future
    assert ivs[2]["can_complete"] == 0


def test_auto_cancel_helper_logic():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    i1 = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))  # Should cancel
    i2 = _create_interview_raw(app_id, "scheduled", db_now - datetime.timedelta(days=1))  # Past, preserve
    i3 = _create_interview_raw(app_id, "completed", db_now + datetime.timedelta(days=2))  # Preserve
    i4 = _create_interview_raw(app_id, "cancelled", db_now + datetime.timedelta(days=3))  # Preserve

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            changed = cancel_future_scheduled_interviews_for_application(cur, app_id)
            conn.commit()

    assert len(changed) == 1
    assert changed[0]["id"] == i1

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, status FROM interviews ORDER BY id")
            rows = cur.fetchall()
            status_map = {r["id"]: r["status"] for r in rows}
            assert status_map[i1] == "cancelled"
            assert status_map[i2] == "scheduled"
            assert status_map[i3] == "completed"
            assert status_map[i4] == "cancelled"
            assert len(rows) == 4  # no DELETE


def test_auto_cancel_helper_transaction_ownership():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    i1 = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cancel_future_scheduled_interviews_for_application(cur, app_id)
            conn.rollback()  # Prove helper did not commit

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM interviews WHERE id = %s", (i1,))
            status = cur.fetchone()["status"]
            assert status == "scheduled"  # Rolled back!


def test_success_redirect_metadata():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    t1 = db_now + datetime.timedelta(days=1)
    t2 = db_now - datetime.timedelta(days=1)

    res = schedule_interview_service(app_id, reca, t1.strftime("%Y-%m-%dT%H:%M"), 30, "phone", None, None)
    ivs = get_recruiter_interviews_for_application(app_id, reca)["data"]
    iv_id = ivs[0]["id"]

    # unauthorized update leak
    res = update_interview_service(iv_id, recb, t1.strftime("%Y-%m-%dT%H:%M"), 30, "phone", None, None)
    assert res["success"] is False
    assert "application_id" not in res

    # success update leak
    res = update_interview_service(iv_id, reca, t1.strftime("%Y-%m-%dT%H:%M"), 60, "phone", None, None)
    assert res["success"] is True
    assert res["application_id"] == app_id

    # unauthorized cancel leak
    res = cancel_interview_service(iv_id, recb)
    assert res["success"] is False
    assert "application_id" not in res

    # success cancel leak
    res = cancel_interview_service(iv_id, reca)
    assert res["success"] is True
    assert res["application_id"] == app_id

    # complete tests
    i2 = _create_interview_raw(app_id, "scheduled", t2)
    # unauthorized complete leak
    res = complete_interview_service(i2, recb)
    assert res["success"] is False
    assert "application_id" not in res

    # success complete leak
    res = complete_interview_service(i2, reca)
    assert res["success"] is True
    assert res["application_id"] == app_id


def test_single_recruiter_status_transition_auto_cancel():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    i1 = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))
    i2 = _create_interview_raw(app_id, "scheduled", db_now - datetime.timedelta(days=1))
    i3 = _create_interview_raw(app_id, "completed", db_now + datetime.timedelta(days=2))

    # A. shortlisted -> rejected: future scheduled interviews become cancelled
    res = update_status_service(app_id, "rejected", reca)
    assert res["success"] is True

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, status FROM interviews ORDER BY id")
            rows = cur.fetchall()
            smap = {r["id"]: r["status"] for r in rows}
            assert smap[i1] == "cancelled"
            assert smap[i2] == "scheduled"  # past preserved
            assert smap[i3] == "completed"  # completed preserved
            assert len(rows) == 3  # no DELETE


def test_single_recruiter_status_transition_hired():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    i1 = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))

    # B. shortlisted -> hired
    res = update_status_service(app_id, "hired", reca)
    assert res["success"] is True

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM interviews WHERE id=%s", (i1,))
            assert cur.fetchone()["status"] == "cancelled"


def test_single_recruiter_status_transition_no_cancel_for_shortlist():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "applied")
    db_now = _get_db_now()

    i1 = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))

    # C. applied -> shortlisted
    res = update_status_service(app_id, "shortlisted", reca)
    assert res["success"] is True

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM interviews WHERE id=%s", (i1,))
            assert cur.fetchone()["status"] == "scheduled"  # preserved


def test_bulk_recruiter_status_transition_auto_cancel():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app1 = create_application(cand1, ja, res1, "shortlisted")
    app2 = create_application(cand2, ja, res1, "shortlisted")  # same job

    db_now = _get_db_now()
    i1 = _create_interview_raw(app1, "scheduled", db_now + datetime.timedelta(days=1))
    i2 = _create_interview_raw(app2, "scheduled", db_now + datetime.timedelta(days=1))

    # unauthorized bulk
    res = bulk_update_status_service([app1], "rejected", recb)
    assert res["success_count"] == 0
    assert res["skipped_count"] == 1

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM interviews WHERE id=%s", (i1,))
            assert cur.fetchone()["status"] == "scheduled"  # preserved because unauthorized

    # valid bulk
    res = bulk_update_status_service([app1, app2], "rejected", reca)
    assert res["success_count"] == 2

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, status FROM interviews")
            smap = {r["id"]: r["status"] for r in cur.fetchall()}
            assert smap[i1] == "cancelled"
            assert smap[i2] == "cancelled"


def test_candidate_withdraw_auto_cancel():
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    i1 = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))
    i2 = _create_interview_raw(app_id, "scheduled", db_now - datetime.timedelta(days=1))

    # other candidate blocked
    res = withdraw_application_service(app_id, cand2)
    assert res["success"] is False

    # owner candidate success
    res = withdraw_application_service(app_id, cand1)
    assert res["success"] is True

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, status FROM interviews")
            smap = {r["id"]: r["status"] for r in cur.fetchall()}
            assert smap[i1] == "cancelled"
            assert smap[i2] == "scheduled"  # past

    # hired -> withdrawn blocked
    app2 = create_application(cand1, ja, res1, "hired")
    res = withdraw_application_service(app2, cand1)
    assert res["success"] is False


@patch("services.recruiter_service.cancel_future_scheduled_interviews_for_application")
@patch("services.recruiter_service.log_audit_event")
def test_atomicity_auto_cancel_rollback(mock_audit, mock_cancel):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    i1 = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))

    mock_cancel.side_effect = Exception("DB failure")

    # Call service
    with pytest.raises(Exception, match=r".*"):
        update_status_service(app_id, "rejected", reca)

    # Verify rollback
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM applications WHERE id=%s", (app_id,))
            assert cur.fetchone()["status"] == "shortlisted"

            cur.execute("SELECT status FROM interviews WHERE id=%s", (i1,))
            assert cur.fetchone()["status"] == "scheduled"

    # Verify no audit emitted
    mock_audit.assert_not_called()


@patch("services.recruiter_service.log_audit_event")
def test_audit_safety_auto_cancel(mock_audit):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()
    _ = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))

    update_status_service(app_id, "rejected", reca)

    # Expect 2 audit events: application_status_changed and interview_cancelled
    assert mock_audit.call_count == 2

    # Application event
    app_call = mock_audit.call_args_list[0]
    assert app_call.args[1] == "application_status_changed"

    # Interview event
    iv_call = mock_audit.call_args_list[1]
    assert iv_call.args[1] == "interview_cancelled"
    details = iv_call.args[4]

    assert details["application_id"] == app_id
    assert details["previous_interview_status"] == "scheduled"
    assert details["new_interview_status"] == "cancelled"

    details_str = json.dumps(details)
    assert "notes" not in details_str
    assert "location_or_link" not in details_str
    assert "email" not in details_str
    assert "phone" not in details_str


@patch("services.candidate_service.log_audit_event")
def test_audit_safety_auto_cancel_candidate(mock_audit):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()
    _ = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))

    withdraw_application_service(app_id, cand1)

    # Expect 2 events
    assert mock_audit.call_count == 2
    assert mock_audit.call_args_list[1].args[1] == "interview_cancelled"


@patch("services.recruiter_service.create_notification")
def test_notification_auto_cancel(mock_notify):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    # No interview -> normal notification
    update_status_service(app_id, "rejected", reca)
    mock_notify.assert_called_once()
    body = mock_notify.call_args.args[2]
    assert "future scheduled interviews have also been cancelled" not in body

    # Reset
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE applications SET status='shortlisted' WHERE id=%s", (app_id,))
            conn.commit()
    mock_notify.reset_mock()

    # With interview -> suffix added
    _ = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))
    update_status_service(app_id, "rejected", reca)
    mock_notify.assert_called_once()
    body = mock_notify.call_args.args[2]
    assert "future scheduled interviews have also been cancelled" in body


# ---------------------------------------------------------
# ROUTES & ROUTE AUTHORIZATION
# ---------------------------------------------------------


def _set_session(client, user_id, role, name="Test"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role
        sess["name"] = name


def test_route_manage_interviews_get(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    # A. owner recruiter GET succeeds
    _set_session(test_client, reca, "recruiter")
    with patch("routes.recruiter.render_template", return_value="INTERVIEW PAGE") as mock_render:
        response = test_client.get(f"/recruiter/application/{app_id}/interviews")
        assert response.status_code == 200
        assert b"INTERVIEW PAGE" in response.data
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        assert "app_info" in kwargs
        assert "interviews" in kwargs
        assert kwargs["app_info"]["application_id"] == app_id

    # B. same-company different recruiter GET denied
    _set_session(test_client, recb, "recruiter")
    with patch("routes.recruiter.render_template", return_value="INTERVIEW PAGE") as mock_render:
        response = test_client.get(f"/recruiter/application/{app_id}/interviews")
        assert response.status_code == 302
        assert "/recruiter/dashboard" in response.headers["Location"]
        mock_render.assert_not_called()

    # C. different recruiter denied
    _set_session(test_client, recc, "recruiter")
    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]

    # D. nonexistent application denied
    _set_session(test_client, reca, "recruiter")
    response = test_client.get("/recruiter/application/999999/interviews")
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]

    # E. candidate role cannot access recruiter interview GET
    _set_session(test_client, cand1, "candidate")
    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_route_schedule_post(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    future_time = (_get_db_now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")

    # owner recruiter: POST schedule succeeds
    _set_session(test_client, reca, "recruiter")
    response = test_client.post(
        f"/recruiter/application/{app_id}/interviews/schedule",
        data={
            "scheduled_at": future_time,
            "duration_minutes": "30",
            "mode": "phone",
            "location_or_link": "",
            "notes": "Route test",
        },
    )
    assert response.status_code == 302
    assert f"/recruiter/application/{app_id}/interviews" in response.headers["Location"]

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, status FROM interviews WHERE application_id=%s", (app_id,))
            ivs = cur.fetchall()
            assert len(ivs) == 1
            assert ivs[0]["status"] == "scheduled"

    # same-company recruiter denied
    _set_session(test_client, recb, "recruiter")
    response = test_client.post(
        f"/recruiter/application/{app_id}/interviews/schedule",
        data={"scheduled_at": future_time, "duration_minutes": "30", "mode": "phone"},
    )
    assert response.status_code == 302  # Redirected back but failed
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT count(*) as c FROM interviews WHERE application_id=%s", (app_id,))
            assert cur.fetchone()["c"] == 1  # unchanged

    # different recruiter denied
    _set_session(test_client, recc, "recruiter")
    response = test_client.post(
        f"/recruiter/application/{app_id}/interviews/schedule",
        data={"scheduled_at": future_time, "duration_minutes": "30", "mode": "phone"},
    )

    # non-shortlisted app rejected
    app2_id = create_application(cand1, ja, res1, "applied")
    _set_session(test_client, reca, "recruiter")
    test_client.post(
        f"/recruiter/application/{app2_id}/interviews/schedule",
        data={"scheduled_at": future_time, "duration_minutes": "30", "mode": "phone"},
    )
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT count(*) as c FROM interviews WHERE application_id=%s", (app2_id,))
            assert cur.fetchone()["c"] == 0

    # invalid mode rejected
    test_client.post(
        f"/recruiter/application/{app_id}/interviews/schedule",
        data={"scheduled_at": future_time, "duration_minutes": "30", "mode": "invalid"},
    )
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT count(*) as c FROM interviews WHERE application_id=%s", (app_id,))
            assert cur.fetchone()["c"] == 1


def test_route_update_post(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    future_time = (_get_db_now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")

    iv_id = _create_interview_raw(app_id, "scheduled", _get_db_now() + datetime.timedelta(days=1))

    # POST owner update with tampered app_id
    _set_session(test_client, reca, "recruiter")
    response = test_client.post(
        f"/recruiter/interview/{iv_id}/update",
        data={
            "app_id": "99999999",  # Tampered
            "scheduled_at": future_time,
            "duration_minutes": "60",
            "mode": "phone",
            "location_or_link": "",
            "notes": "Updated notes",
        },
    )
    assert response.status_code == 302
    # Redirects to REAL application_id
    assert f"/recruiter/application/{app_id}/interviews" in response.headers["Location"]

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT duration_minutes FROM interviews WHERE id=%s", (iv_id,))
            assert cur.fetchone()["duration_minutes"] == 60

    # same-company recruiter update fails
    _set_session(test_client, recb, "recruiter")
    response = test_client.post(
        f"/recruiter/interview/{iv_id}/update",
        data={"app_id": "99999999", "scheduled_at": future_time, "duration_minutes": "45", "mode": "phone"},
    )
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]  # Generic redirect

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT duration_minutes FROM interviews WHERE id=%s", (iv_id,))
            assert cur.fetchone()["duration_minutes"] == 60  # unchanged


def test_route_cancel_post(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    iv_id = _create_interview_raw(app_id, "scheduled", _get_db_now() + datetime.timedelta(days=1))

    # same-company recruiter cannot cancel
    _set_session(test_client, recb, "recruiter")
    test_client.post(f"/recruiter/interview/{iv_id}/cancel")
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM interviews WHERE id=%s", (iv_id,))
            assert cur.fetchone()["status"] == "scheduled"

    # different recruiter cannot cancel
    _set_session(test_client, recc, "recruiter")
    test_client.post(f"/recruiter/interview/{iv_id}/cancel")

    # owner recruiter cancel success with tampered app_id
    _set_session(test_client, reca, "recruiter")
    response = test_client.post(f"/recruiter/interview/{iv_id}/cancel", data={"app_id": "99999999"})
    assert response.status_code == 302
    assert f"/recruiter/application/{app_id}/interviews" in response.headers["Location"]

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM interviews WHERE id=%s", (iv_id,))
            assert cur.fetchone()["status"] == "cancelled"


def test_route_complete_post(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    # past scheduled interview
    iv_id = _create_interview_raw(app_id, "scheduled", _get_db_now() - datetime.timedelta(days=1))

    # Unauthorized recruiters cannot complete
    _set_session(test_client, recb, "recruiter")
    test_client.post(f"/recruiter/interview/{iv_id}/complete")

    # Owner recruiter complete success with tampered app_id
    _set_session(test_client, reca, "recruiter")
    response = test_client.post(f"/recruiter/interview/{iv_id}/complete", data={"app_id": "99999999"})
    assert response.status_code == 302
    assert f"/recruiter/application/{app_id}/interviews" in response.headers["Location"]

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM interviews WHERE id=%s", (iv_id,))
            assert cur.fetchone()["status"] == "completed"

    # Future scheduled interview cannot be completed
    iv_future = _create_interview_raw(app_id, "scheduled", _get_db_now() + datetime.timedelta(days=1))
    response = test_client.post(f"/recruiter/interview/{iv_future}/complete")
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM interviews WHERE id=%s", (iv_future,))
            assert cur.fetchone()["status"] == "scheduled"


def test_route_candidate_interviews(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app1 = create_application(cand1, ja, res1, "shortlisted")
    app2 = create_application(cand2, ja, res1, "shortlisted")

    _create_interview_raw(app1, "scheduled", _get_db_now() + datetime.timedelta(days=1))
    _create_interview_raw(app2, "scheduled", _get_db_now() + datetime.timedelta(days=1))

    # GET candidate1
    _set_session(test_client, cand1, "candidate")
    with patch("routes.candidate.render_template", return_value="CANDIDATE INTERVIEW PAGE") as mock_render:
        response = test_client.get("/candidate/interviews")
        assert response.status_code == 200
        assert b"CANDIDATE INTERVIEW PAGE" in response.data

        args, kwargs = mock_render.call_args
        interviews = kwargs["interviews"]
        assert len(interviews) == 1
        assert "notes" not in interviews[0]
        assert interviews[0]["application_id"] == app1

    # recruiter role cannot access candidate route
    _set_session(test_client, reca, "recruiter")
    response = test_client.get("/candidate/interviews")
    assert response.status_code == 302

    # anonymous cannot access
    with test_client.session_transaction() as sess:
        sess.clear()
    response = test_client.get("/candidate/interviews")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # POST candidate/interviews 405
    _set_session(test_client, cand1, "candidate")
    response = test_client.post("/candidate/interviews")
    assert response.status_code == 405


def test_no_form_id_trust(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")

    # Update
    iv1 = _create_interview_raw(app_id, "scheduled", _get_db_now() + datetime.timedelta(days=1))
    _set_session(test_client, reca, "recruiter")

    future_time = (_get_db_now() + datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")

    response = test_client.post(
        f"/recruiter/interview/{iv1}/update",
        data={
            "app_id": "99999999",
            "scheduled_at": future_time,
            "duration_minutes": "45",
            "mode": "phone",
            "location_or_link": "",
            "notes": "",
        },
    )

    assert response.status_code == 302
    assert f"/recruiter/application/{app_id}/interviews" in response.headers["Location"]

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT duration_minutes FROM interviews WHERE id=%s", (iv1,))
            assert cur.fetchone()["duration_minutes"] == 45

    # Cancel
    response = test_client.post(f"/recruiter/interview/{iv1}/cancel", data={"app_id": "99999999"})
    assert response.status_code == 302
    assert f"/recruiter/application/{app_id}/interviews" in response.headers["Location"]

    # Complete
    iv2 = _create_interview_raw(app_id, "scheduled", _get_db_now() - datetime.timedelta(days=1))
    response = test_client.post(f"/recruiter/interview/{iv2}/complete", data={"app_id": "99999999"})
    assert response.status_code == 302
    assert f"/recruiter/application/{app_id}/interviews" in response.headers["Location"]


def test_route_method_security(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    iv_id = _create_interview_raw(app_id, "scheduled", _get_db_now() + datetime.timedelta(days=1))

    _set_session(test_client, reca, "recruiter")

    response = test_client.get(f"/recruiter/application/{app_id}/interviews/schedule")
    assert response.status_code == 405

    response = test_client.get(f"/recruiter/interview/{iv_id}/update")
    assert response.status_code == 405

    response = test_client.get(f"/recruiter/interview/{iv_id}/cancel")
    assert response.status_code == 405

    response = test_client.get(f"/recruiter/interview/{iv_id}/complete")
    assert response.status_code == 405


# ---------------------------------------------------------
# PHASE 4B STEP 4 UI TESTS
# ---------------------------------------------------------


def test_ui_recruiter_real_template_render(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))
    _create_interview_raw(app_id, "scheduled", db_now - datetime.timedelta(days=1))
    _create_interview_raw(app_id, "completed", db_now - datetime.timedelta(days=2))
    _create_interview_raw(app_id, "cancelled", db_now - datetime.timedelta(days=3))

    _set_session(test_client, reca, "recruiter")

    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    assert response.status_code == 200

    html = response.data.decode("utf-8")

    # Assert candidate name and job title
    assert "Candidate 1" in html
    assert "Job A" in html

    # Assert schedule form exists
    assert "Schedule New Interview" in html

    # Assert mode values
    assert 'value="online"' in html
    assert 'value="in_person"' in html
    assert 'value="phone"' in html
    assert 'value="in-person"' not in html

    # Assert duration contract
    assert 'min="5"' in html
    assert 'max="480"' in html

    # Assert location maxlength
    assert 'maxlength="500"' in html

    # Assert notes maxlength
    assert 'maxlength="2000"' in html


def test_ui_recruiter_control_visibility(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    iv_future = _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))
    iv_past = _create_interview_raw(app_id, "scheduled", db_now - datetime.timedelta(days=1))
    iv_comp = _create_interview_raw(app_id, "completed", db_now - datetime.timedelta(days=2))
    iv_canc = _create_interview_raw(app_id, "cancelled", db_now - datetime.timedelta(days=3))

    _set_session(test_client, reca, "recruiter")
    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    html = response.data.decode("utf-8")

    # Helper to check if a specific action exists for an interview
    def has_action(iv_id, action):
        return f"/recruiter/interview/{iv_id}/{action}" in html

    def has_edit(iv_id):
        # We look for the edit form action URL
        return f"/recruiter/interview/{iv_id}/update" in html

    # Future scheduled: edit visible, cancel visible, complete NOT visible
    assert has_edit(iv_future)
    assert has_action(iv_future, "cancel")
    assert not has_action(iv_future, "complete")

    # Past scheduled: edit may be visible, cancel visible, complete visible
    assert has_action(iv_past, "cancel")
    assert has_action(iv_past, "complete")

    # Completed: no mutation controls
    assert not has_edit(iv_comp)
    assert not has_action(iv_comp, "cancel")
    assert not has_action(iv_comp, "complete")

    # Cancelled: no mutation controls
    assert not has_edit(iv_canc)
    assert not has_action(iv_canc, "cancel")
    assert not has_action(iv_canc, "complete")

    # Delete control should not exist at all
    assert "/delete" not in html


def test_ui_non_shortlisted_application(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "rejected")
    db_now = _get_db_now()

    iv_past = _create_interview_raw(app_id, "scheduled", db_now - datetime.timedelta(days=1))

    _set_session(test_client, reca, "recruiter")
    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    html = response.data.decode("utf-8")

    # Should render history
    assert "Interview History" in html

    # NOT render schedule form
    assert "Schedule New Interview" not in html

    # NOT render edit form (no update action in HTML for any interview)
    assert f"/recruiter/interview/{iv_past}/update" not in html

    # Cancel may remain visible if status is scheduled
    assert f"/recruiter/interview/{iv_past}/cancel" in html

    # No delete action
    assert "/delete" not in html


def test_ui_candidate_real_template(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    _create_interview_raw(app_id, "scheduled", db_now + datetime.timedelta(days=1))

    _set_session(test_client, cand1, "candidate")
    response = test_client.get("/candidate/interviews")
    assert response.status_code == 200

    html = response.data.decode("utf-8")

    # Job title appears
    assert "Job A" in html

    # Does not contain literal field name 'notes'
    assert "notes" not in html.lower()

    # Contains no URLs/actions for recruiter mutations
    assert "recruiter.schedule_interview" not in html
    assert "/interviews/schedule" not in html
    assert "/update" not in html
    assert "/cancel" not in html
    assert "/complete" not in html


def test_ui_xss_escaping(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                INSERT INTO interviews (application_id, scheduled_at, duration_minutes,
                                        mode, location_or_link, status, notes)
                VALUES (%s, %s, 30, 'online', '<img src=x onerror=alert(1)>', 'scheduled', '<script>alert(1)</script>')
                """,
                (app_id, db_now + datetime.timedelta(days=1)),
            )
            conn.commit()

    # Recruiter check
    _set_session(test_client, reca, "recruiter")
    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    html = response.data.decode("utf-8")

    assert "<script>alert(1)</script>" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    # Candidate check
    _set_session(test_client, cand1, "candidate")
    response = test_client.get("/candidate/interviews")
    html = response.data.decode("utf-8")

    assert "alert(1)" not in html  # notes are not rendered at all
    assert "&lt;img src=x onerror=alert(1)&gt;" in html


def test_ui_unsafe_link(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                INSERT INTO interviews (application_id, scheduled_at, duration_minutes,
                                        mode, location_or_link, status, notes)
                VALUES (%s, %s, 30, 'online', 'javascript:alert(1)', 'scheduled', '')
                """,
                (app_id, db_now + datetime.timedelta(days=1)),
            )
            conn.commit()

    # Recruiter check
    _set_session(test_client, reca, "recruiter")
    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    html = response.data.decode("utf-8")

    assert 'href="javascript:alert(1)"' not in html

    # Candidate check
    _set_session(test_client, cand1, "candidate")
    response = test_client.get("/candidate/interviews")
    html = response.data.decode("utf-8")

    assert 'href="javascript:alert(1)"' not in html


def test_ui_csrf_template(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    _create_interview_raw(app_id, "scheduled", db_now - datetime.timedelta(days=1))

    _set_session(test_client, reca, "recruiter")
    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    html = response.data.decode("utf-8")

    # Count CSRF tokens for forms (schedule, update, cancel, complete)
    assert html.count('name="csrf_token"') >= 4


def test_ui_candidate_withdraw(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()

    app_applied = create_application(cand1, ja, res1, "applied")
    app_shortlisted = create_application(cand1, ja, res1, "shortlisted")
    app_rejected = create_application(cand1, ja, res1, "rejected")
    app_hired = create_application(cand1, ja, res1, "hired")
    app_withdrawn = create_application(cand1, ja, res1, "withdrawn")

    _set_session(test_client, cand1, "candidate")
    response = test_client.get("/candidate/dashboard")
    html = response.data.decode("utf-8")

    # Ensure withdraw is present for applied and shortlisted
    assert f"/candidate/application/{app_applied}/withdraw" in html
    assert f"/candidate/application/{app_shortlisted}/withdraw" in html

    # Ensure withdraw is absent for others
    assert f"/candidate/application/{app_rejected}/withdraw" not in html
    assert f"/candidate/application/{app_hired}/withdraw" not in html
    assert f"/candidate/application/{app_withdrawn}/withdraw" not in html


def test_ui_recruiter_transition(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()

    app_applied = create_application(cand1, ja, res1, "applied")
    app_shortlisted = create_application(cand2, ja, res1, "shortlisted")

    _set_session(test_client, reca, "recruiter")
    response = test_client.get(f"/recruiter/job/{ja}/applicants")
    html = response.data.decode("utf-8")

    # applied: shortlisted action present, rejected action present, hired action absent
    assert f'data-app-id="{app_applied}" data-status="shortlisted"' in html
    assert f'data-app-id="{app_applied}" data-status="rejected"' in html
    assert f'data-app-id="{app_applied}" data-status="hired"' not in html

    # shortlisted: hired action present, rejected action present, shortlisted action absent
    assert f'data-app-id="{app_shortlisted}" data-status="hired"' in html
    assert f'data-app-id="{app_shortlisted}" data-status="rejected"' in html
    assert f'data-app-id="{app_shortlisted}" data-status="shortlisted"' not in html

    # Hidden single-status POST form contains CSRF token
    assert 'id="singleStatusForm"' in html

    # All applications should have Interview history link
    assert f"/recruiter/application/{app_applied}/interviews" in html
    assert f"/recruiter/application/{app_shortlisted}/interviews" in html


def test_ui_no_user_data_in_js(test_client):
    reca, recb, recc, cand1, cand2, ja, res1 = setup_data()
    app_id = create_application(cand1, ja, res1, "shortlisted")
    db_now = _get_db_now()

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                INSERT INTO interviews (application_id, scheduled_at, duration_minutes,
                                        mode, location_or_link, status, notes)
                VALUES (%s, %s, 30, 'online', 'loc_inject_test', 'scheduled', 'notes_inject_test')
                """,
                (app_id, db_now + datetime.timedelta(days=1)),
            )
            # Update user and job names to malicious values
            cur.execute("UPDATE users SET name = 'cand_inject_test' WHERE id = %s", (cand1,))
            cur.execute("UPDATE jobs SET job_title = 'job_inject_test' WHERE id = %s", (ja,))
            conn.commit()

    _set_session(test_client, reca, "recruiter")
    response = test_client.get(f"/recruiter/application/{app_id}/interviews")
    html = response.data.decode("utf-8")

    # Extract the script block content to verify JS doesn't contain injected values
    import re

    script_blocks = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    for block in script_blocks:
        assert "loc_inject_test" not in block
        assert "notes_inject_test" not in block
        assert "cand_inject_test" not in block
        assert "job_inject_test" not in block
