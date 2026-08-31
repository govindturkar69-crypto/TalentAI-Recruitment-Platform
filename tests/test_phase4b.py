import json
from contextlib import closing
from unittest.mock import patch

import pytest

from app import app
from core import get_db_connection
from services.interview_service import (
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
