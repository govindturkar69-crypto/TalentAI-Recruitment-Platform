def _login_as(client, user_id=1, role="recruiter", email="recruiter@test.com"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role
        sess["email"] = email


def test_recruiter_settings_unauthenticated(client):
    response = client.get("/recruiter/settings", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_recruiter_settings_candidate(client, mock_db):
    _login_as(client, role="candidate")
    mock_db.fetchone.return_value = {"is_active": 1}
    response = client.get("/recruiter/settings", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_recruiter_settings_view_company(client, mock_db):
    _login_as(client)
    mock_db.fetchone.side_effect = [
        {"is_active": 1},
        {
            "name": "Recruiter A",
            "email": "a@test.com",
            "company_id": 1,
            "company_name": "Test Co",
            "description": "Desc",
            "website": "https://test.com",
            "is_active": 1,
        },
    ]
    response = client.get("/recruiter/settings")
    assert response.status_code == 200
    assert b"Test Co" in response.data
    assert b"https://test.com" in response.data
    assert b"company_id" not in response.data  # No form exposed
    assert b'<select name="company_id"' not in response.data


def test_recruiter_settings_null_company(client, mock_db):
    _login_as(client)
    mock_db.fetchone.side_effect = [
        {"is_active": 1},
        {
            "name": "Recruiter A",
            "email": "a@test.com",
            "company_id": None,
            "company_name": None,
            "description": None,
            "website": None,
            "is_active": None,
        },
    ]
    response = client.get("/recruiter/settings")
    assert response.status_code == 200
    assert b"No company has been assigned" in response.data


def test_recruiter_cannot_post_settings(client):
    _login_as(client)
    response = client.post("/recruiter/settings", data={"company_id": 2}, follow_redirects=False)
    assert response.status_code == 405  # Method Not Allowed


def test_same_company_isolation_job_applicants(client, mock_db):
    # Recruiter A (id=2, company_id=5) trying to access Recruiter B's (id=3, company_id=5) job (Job 1)
    # The application verifies ownership using recruiter_id, so same company does not grant access.
    _login_as(client, user_id=2)
    mock_db.fetchone.side_effect = [
        {"is_active": 1},
        None,  # job not found because WHERE id=1 AND recruiter_id=2 fails, ignoring company_id
    ]
    response = client.get("/recruiter/job/1/applicants", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


def test_same_company_isolation_candidate_profile(client, mock_db):
    # Recruiter A (id=2, company_id=5) trying to view candidate profile for Recruiter B's job.
    _login_as(client, user_id=2)
    mock_db.fetchone.side_effect = [{"is_active": 1}, None]  # app not found because join on jobs.recruiter_id=2 fails
    response = client.get("/recruiter/application/1/candidate", follow_redirects=False)
    assert response.status_code == 302


def test_same_company_isolation_candidate_resume(client, mock_db):
    # Recruiter A (id=2, company_id=5) trying to view resume for Recruiter B's job.
    _login_as(client, user_id=2)
    mock_db.fetchone.side_effect = [{"is_active": 1}, None]  # app not found because join on jobs.recruiter_id=2 fails
    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302
