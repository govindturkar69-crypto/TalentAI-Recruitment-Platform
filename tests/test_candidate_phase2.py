import datetime


def test_candidate_jobs_unauthenticated(client):
    response = client.get("/candidate/jobs")
    assert response.status_code == 302
    assert b"/login" in response.data


def test_candidate_jobs_recruiter_blocked(client, mock_db):
    mock_db.fetchone.return_value = {"id": 2, "role": "recruiter", "is_active": True, "email": "recruiter@test.com"}
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"
        sess["is_active"] = True
    response = client.get("/candidate/jobs")
    assert response.status_code == 302


def test_candidate_jobs_active_displayed(client, mock_db):
    mock_db.fetchone.side_effect = [
        {"is_active": True},  # for login_required
    ]
    mock_db.fetchall.side_effect = [
        [
            {
                "id": 1,
                "job_title": "Active Job",
                "location": "Remote",
                "experience": "2 years",
                "required_skills": "Python",
                "is_active": True,
            }
        ],
        [],  # saved_jobs
        [],  # applications
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/jobs")
    assert response.status_code == 200
    assert b"Active Job" in response.data

    calls = mock_db.execute.call_args_list
    assert "is_active = TRUE" in calls[1][0][0]


def test_candidate_jobs_keyword_search(client, mock_db):
    mock_db.fetchone.side_effect = [{"is_active": True}]
    mock_db.fetchall.side_effect = [[], [], []]

    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/jobs?keyword=Dev")
    assert response.status_code == 200

    calls = mock_db.execute.call_args_list
    sql = calls[1][0][0]
    args = calls[1][0][1]
    assert "job_title LIKE %s" in sql
    assert "%Dev%" in args


def test_candidate_job_details_active(client, mock_db):
    mock_db.fetchone.side_effect = [
        {"is_active": True},
        None,  # not applied
        {
            "id": 1,
            "job_title": "Test Job",
            "company_name": "Test Co",
            "is_active": True,
            "location": "Remote",
            "experience": "Any",
            "required_skills": "Python",
            "created_at": datetime.datetime.now(),
            "description": "desc",
        },
        None,  # not saved
        None,  # candidate_skills profile
        None,  # candidate_skills resume
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/job/1")
    assert response.status_code == 200
    assert b"Test Job" in response.data
    assert b"Apply Now" in response.data


def test_candidate_job_details_inactive_not_applied(client, mock_db):
    mock_db.fetchone.side_effect = [
        {"is_active": True},
        None,  # not applied
        {"id": 1, "job_title": "Closed Job", "is_active": False, "recruiter_id": 1},
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/job/1")
    assert response.status_code == 302


def test_candidate_job_details_inactive_applied(client, mock_db):
    mock_db.fetchone.side_effect = [
        {"is_active": True},
        {"id": 10, "status": "rejected", "applied_at": datetime.datetime.now()},  # applied
        {
            "id": 1,
            "job_title": "Closed Job",
            "company_name": "Test Co",
            "is_active": False,
            "location": "Remote",
            "experience": "Any",
            "required_skills": "Python",
            "created_at": datetime.datetime.now(),
            "description": "desc",
        },
        None,  # not saved
        None,  # profile skills
        None,  # resume skills
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/job/1")
    assert response.status_code == 200
    assert b"Closed Job" in response.data
    assert b"Job Closed" in response.data


def test_candidate_applications(client, mock_db):
    mock_db.fetchone.side_effect = [{"is_active": True}]
    mock_db.fetchall.side_effect = [
        [
            {
                "id": 1,
                "job_id": 1,
                "job_title": "Active App",
                "company_name": "Co",
                "applied_at": datetime.datetime.now(),
                "score": 80,
                "status": "shortlisted",
                "is_active": True,
            },
            {
                "id": 2,
                "job_id": 2,
                "job_title": "Closed App",
                "company_name": "Co",
                "applied_at": datetime.datetime.now(),
                "score": 75,
                "status": "applied",
                "is_active": False,
            },
        ]
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/applications")
    assert response.status_code == 200
    assert b"Active App" in response.data
    assert b"Closed App" in response.data
    assert b"Closed" in response.data


def test_apply_job_inactive_rejected(client, mock_db):
    mock_db.fetchone.side_effect = [
        {"is_active": True},  # login check
        {"id": 1, "raw_text": "text", "skills": "Python"},  # resume
        None,  # duplicate check
        {"id": 1, "is_active": False},  # job check
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"
        sess["name"] = "Candidate"

    response = client.post("/candidate/apply/1")
    assert response.status_code == 302

    with client.session_transaction() as session:
        flashes = dict(session["_flashes"])
        assert b"This job is no longer active" in str(flashes).encode()


def test_candidate_jobs_location_search_and_empty(client, mock_db):
    mock_db.fetchone.side_effect = [{"is_active": True}]
    # Simulate empty results
    mock_db.fetchall.side_effect = [[], [], []]

    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/jobs?location=Remote")
    assert response.status_code == 200
    assert b"No jobs found" in response.data

    calls = mock_db.execute.call_args_list
    sql = calls[1][0][0]
    args = calls[1][0][1]
    assert "location LIKE %s" in sql
    assert "%Remote%" in args


def test_candidate_job_details_invalid_id(client, mock_db):
    mock_db.fetchone.side_effect = [
        {"is_active": True},
        None,  # not applied
        None,  # Job not found
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/job/999")
    assert response.status_code == 302


def test_candidate_job_details_active_applied_and_saved(client, mock_db):
    import datetime

    mock_db.fetchone.side_effect = [
        {"is_active": True},
        {"id": 10, "status": "applied", "applied_at": datetime.datetime.now()},  # applied
        {
            "id": 1,
            "job_title": "Test Job",
            "company_name": "Test Co",
            "is_active": True,
            "location": "Remote",
            "experience": "Any",
            "required_skills": "Python",
            "created_at": datetime.datetime.now(),
            "description": "desc",
        },
        {"saved": 1},  # is_saved
        None,  # profile skills
        None,  # resume skills
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.get("/candidate/job/1")
    assert response.status_code == 200
    assert b"You applied for this job on" in response.data
    assert b"Unsave" in response.data


def test_apply_job_success(client, mock_db):
    mock_db.fetchone.side_effect = [
        {"is_active": True},  # login check
        {"id": 1, "raw_text": "text", "skills": "Python"},  # resume
        None,  # duplicate check
        {
            "id": 1,
            "is_active": True,
            "required_skills": "Python",
            "description": "desc",
            "job_title": "Test Job",
            "recruiter_id": 2,
        },  # job check
        {"id": 1, "skills": "Python"},  # resolved candidate skills
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"
        sess["name"] = "Candidate"

    response = client.post("/candidate/apply/1")
    assert response.status_code == 302

    with client.session_transaction() as session:
        flashes = dict(session["_flashes"])
        assert b"Application submitted!" in str(flashes).encode()


def test_apply_job_duplicate(client, mock_db):
    mock_db.fetchone.side_effect = [
        {"is_active": True},  # login check
        {"id": 1, "raw_text": "text", "skills": "Python"},  # resume
        {"id": 10},  # duplicate check (already applied)
    ]
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"
        sess["name"] = "Candidate"

    response = client.post("/candidate/apply/1")
    assert response.status_code == 302

    with client.session_transaction() as session:
        flashes = dict(session["_flashes"])
        assert b"You have already applied for this job" in str(flashes).encode()


def test_save_job(client, mock_db):
    mock_db.fetchone.return_value = {"is_active": True}
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.post("/candidate/save_job/1")
    assert response.status_code == 302

    calls = mock_db.execute.call_args_list

    job_check_calls = [call for call in calls if "SELECT id FROM jobs WHERE id = %s" in call.args[0]]

    assert len(job_check_calls) == 1
    assert job_check_calls[0].args[1] == (1,)

    insert_calls = [call for call in calls if "INSERT INTO saved_jobs" in call.args[0]]

    assert len(insert_calls) == 1
    assert insert_calls[0].args[1] == (3, 1)


def test_unsave_job(client, mock_db):
    mock_db.fetchone.return_value = {"is_active": True}
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "candidate"

    response = client.post("/candidate/unsave_job/1")
    assert response.status_code == 302

    calls = mock_db.execute.call_args_list
    assert "DELETE FROM saved_jobs" in calls[1][0][0]
    assert calls[1][0][1] == (3, 1)


def test_candidate_applications_other_candidate_excluded(client, mock_db):
    # This just verifies that the session["user_id"] is used in the query
    mock_db.fetchone.return_value = {"is_active": True}
    mock_db.fetchall.return_value = []

    with client.session_transaction() as sess:
        sess["user_id"] = 99
        sess["role"] = "candidate"

    response = client.get("/candidate/applications")
    assert response.status_code == 200

    calls = mock_db.execute.call_args_list
    # First is auth check, second is the applications query
    assert calls[1][0][1] == (99,)
