from contextlib import closing
from unittest.mock import patch

import pytest

from app import app
from core import get_db_connection


@pytest.fixture
def test_client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            yield client


def _set_session(client, user_id, role, name="Test"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role
        sess["name"] = name


def setup_data():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            # Clean up
            cur.execute("DELETE FROM applications")
            cur.execute("DELETE FROM jobs")
            cur.execute("DELETE FROM resumes")
            cur.execute("DELETE FROM users WHERE email LIKE '%test4a%'")

            # Recruiter A
            cur.execute(
                "INSERT INTO users (name, email, password, role) "
                "VALUES ('Recruiter A', 'reca_test4a@example.com', 'hash', 'recruiter')"
            )
            reca_id = cur.lastrowid

            # Recruiter B
            cur.execute(
                "INSERT INTO users (name, email, password, role) "
                "VALUES ('Recruiter B', 'recb_test4a@example.com', 'hash', 'recruiter')"
            )
            recb_id = cur.lastrowid

            # Candidate
            cur.execute(
                "INSERT INTO users (name, email, password, role) "
                "VALUES ('Candidate', 'cand_test4a@example.com', 'hash', 'candidate')"
            )
            cand_id = cur.lastrowid

            # Resume
            cur.execute(
                "INSERT INTO resumes (user_id, resume_path, skills) VALUES (%s, 'dummy.pdf', 'python')", (cand_id,)
            )
            resume_id = cur.lastrowid

            # Job A
            cur.execute(
                "INSERT INTO jobs (recruiter_id, job_title, required_skills) VALUES (%s, 'Job A', 'python')", (reca_id,)
            )
            job_a_id = cur.lastrowid

            # Job B
            cur.execute(
                "INSERT INTO jobs (recruiter_id, job_title, required_skills) VALUES (%s, 'Job B', 'python')", (recb_id,)
            )
            job_b_id = cur.lastrowid

            conn.commit()
            return reca_id, recb_id, cand_id, job_a_id, job_b_id, resume_id


def create_application(candidate_id, job_id, resume_id, status="applied"):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO applications (candidate_id, job_id, resume_id, status) VALUES (%s, %s, %s, %s)",
                (candidate_id, job_id, resume_id, status),
            )
            conn.commit()
            return cur.lastrowid


def get_app_status(app_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT status FROM applications WHERE id=%s", (app_id,))
            return cur.fetchone()["status"]


def test_single_status_valid(test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    app_id = create_application(cand, ja, res, "applied")
    _set_session(test_client, reca, "recruiter")

    # applied -> shortlisted
    test_client.post(f"/recruiter/application/{app_id}/status", data={"status": "shortlisted"}, follow_redirects=True)
    assert get_app_status(app_id) == "shortlisted"

    # shortlisted -> hired
    test_client.post(f"/recruiter/application/{app_id}/status", data={"status": "hired"}, follow_redirects=True)
    assert get_app_status(app_id) == "hired"


def test_single_status_invalid_transitions(test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    app_id = create_application(cand, ja, res, "applied")
    _set_session(test_client, reca, "recruiter")

    # applied -> hired (BLOCKED)
    test_client.post(f"/recruiter/application/{app_id}/status", data={"status": "hired"}, follow_redirects=True)
    assert get_app_status(app_id) == "applied"

    # set to rejected
    create_application(cand, ja, res, "rejected")
    app_rej = create_application(cand, ja, res, "rejected")

    # rejected -> shortlisted (BLOCKED)
    test_client.post(f"/recruiter/application/{app_rej}/status", data={"status": "shortlisted"}, follow_redirects=True)
    assert get_app_status(app_rej) == "rejected"

    # arbitrary status string
    test_client.post(f"/recruiter/application/{app_id}/status", data={"status": "super_hired"}, follow_redirects=True)
    assert get_app_status(app_id) == "applied"


def test_ownership_security(test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    create_application(cand, ja, res, "applied")
    app_b = create_application(cand, jb, res, "applied")

    _set_session(test_client, reca, "recruiter")

    # Recruiter A tries to update Recruiter B's app
    test_client.post(f"/recruiter/application/{app_b}/status", data={"status": "shortlisted"}, follow_redirects=True)
    assert get_app_status(app_b) == "applied"


def test_candidate_withdrawal(test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    app_1 = create_application(cand, ja, res, "applied")
    app_2 = create_application(cand, ja, res, "shortlisted")
    app_3 = create_application(cand, ja, res, "hired")
    app_4 = create_application(cand, ja, res, "rejected")

    _set_session(test_client, cand, "candidate")

    # Valid
    test_client.post(f"/candidate/withdraw/{app_1}", follow_redirects=True)
    assert get_app_status(app_1) == "withdrawn"

    test_client.post(f"/candidate/withdraw/{app_2}", follow_redirects=True)
    assert get_app_status(app_2) == "withdrawn"

    # Invalid
    test_client.post(f"/candidate/withdraw/{app_3}", follow_redirects=True)
    assert get_app_status(app_3) == "hired"

    test_client.post(f"/candidate/withdraw/{app_4}", follow_redirects=True)
    assert get_app_status(app_4) == "rejected"


def test_bulk_update(test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    app_1 = create_application(cand, ja, res, "applied")
    app_2 = create_application(cand, ja, res, "shortlisted")
    app_3 = create_application(cand, jb, res, "applied")

    _set_session(test_client, reca, "recruiter")

    resp = test_client.post(
        "/recruiter/applications/bulk_update",
        data={"selected_apps": [str(app_1), str(app_2), str(app_3), "99999"], "bulk_status": "rejected", "job_id": ja},
        follow_redirects=True,
    )

    assert get_app_status(app_1) == "rejected"
    assert get_app_status(app_2) == "rejected"
    assert get_app_status(app_3) == "applied"

    assert b"Updated 2 application(s)" in resp.data


@patch("services.recruiter_service.log_audit_event")
def test_audit_single_update(mock_audit, test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    app_id = create_application(cand, ja, res, "applied")
    _set_session(test_client, reca, "recruiter")

    # successful single update => audit emitted
    test_client.post(f"/recruiter/application/{app_id}/status", data={"status": "shortlisted"}, follow_redirects=True)
    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert args[0] == reca
    assert args[1] == "application_status_changed"
    assert args[3] == app_id
    assert args[4] == {"previous_status": "applied", "new_status": "shortlisted"}


@patch("services.recruiter_service.log_audit_event")
def test_audit_single_update_invalid(mock_audit, test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    app_id = create_application(cand, ja, res, "applied")
    _set_session(test_client, reca, "recruiter")

    # invalid transition => no audit
    test_client.post(f"/recruiter/application/{app_id}/status", data={"status": "hired"}, follow_redirects=True)
    mock_audit.assert_not_called()

    # failed/not-owned application => no audit
    app_b = create_application(cand, jb, res, "applied")
    test_client.post(f"/recruiter/application/{app_b}/status", data={"status": "shortlisted"}, follow_redirects=True)
    mock_audit.assert_not_called()


@patch("services.candidate_service.log_audit_event")
def test_audit_candidate_withdrawal(mock_audit, test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    app_1 = create_application(cand, ja, res, "applied")
    _set_session(test_client, cand, "candidate")

    # successful candidate withdrawal => audit emitted
    test_client.post(f"/candidate/withdraw/{app_1}", follow_redirects=True)
    mock_audit.assert_called_once()
    args, kwargs = mock_audit.call_args
    assert args[0] == cand
    assert args[1] == "application_withdrawn"
    assert args[3] == app_1
    assert args[4] == {"previous_status": "applied", "new_status": "withdrawn"}


@patch("services.recruiter_service.log_audit_event")
def test_audit_bulk_update(mock_audit, test_client):
    reca, recb, cand, ja, jb, res = setup_data()
    app_1 = create_application(cand, ja, res, "applied")
    app_2 = create_application(cand, ja, res, "shortlisted")
    app_3 = create_application(cand, jb, res, "applied")

    _set_session(test_client, reca, "recruiter")

    # bulk audits only successful transitions
    test_client.post(
        "/recruiter/applications/bulk_update",
        data={"selected_apps": [str(app_1), str(app_2), str(app_3), "99999"], "bulk_status": "rejected", "job_id": ja},
        follow_redirects=True,
    )

    # 1 and 2 should be audited, 3 and 99999 should not be
    assert mock_audit.call_count == 2
