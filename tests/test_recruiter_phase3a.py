import os

import pytest

# -----------------------------------
# PROFILE ACCESS TESTS
# -----------------------------------


def test_view_candidate_profile_unauthenticated(client):
    response = client.get("/recruiter/application/1/candidate", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_view_candidate_profile_candidate_role(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "candidate"

    response = client.get("/recruiter/application/1/candidate", follow_redirects=False)
    assert response.status_code == 302


def test_view_candidate_profile_success(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"
        sess["name"] = "Recruiter Bob"

    # 1. is_active -> 1
    # 2. app_data
    # 3. profile
    mock_db.fetchone.side_effect = [
        {"is_active": 1},
        {
            "application_id": 1,
            "score": 85,
            "matched_skills": "Python",
            "missing_skills": "React",
            "status": "applied",
            "applied_at": None,
            "job_id": 1,
            "job_title": "Dev",
            "name": "Alice",
            "email": "alice@test.com",
            "candidate_id": 1,
        },
        {"user_id": 1, "bio": "Great dev", "skills": "Python"},
    ]
    mock_db.fetchall.side_effect = [
        [{"institution": "MIT", "degree": "BS"}],  # education
        [{"company": "Google", "title": "SWE"}],  # experience
        [{"title": "Open Source"}],  # projects
        [{"name": "AWS Certified"}],  # certifications
        [{"title": "Employee of the Month"}],  # achievements
    ]

    response = client.get("/recruiter/application/1/candidate", follow_redirects=True)
    assert response.status_code == 200
    assert b"Alice" in response.data
    assert b"alice@test.com" in response.data
    assert b"Dev" in response.data
    assert b"MIT" in response.data
    assert b"Google" in response.data
    assert b"Open Source" in response.data
    assert b"AWS Certified" in response.data
    assert b"Employee of the Month" in response.data

    # Ownership SQL verification
    execute_calls = mock_db.execute.call_args_list
    app_query_found = False
    for call in execute_calls:
        query, params = call[0]
        if "FROM applications a" in query and "JOIN jobs j" in query:
            app_query_found = True
            assert params == (1, 2)  # app_id, recruiter_id
            break
    assert app_query_found


def test_view_candidate_profile_unauthorized_recruiter(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"is_active": 1}, None]
    response = client.get("/recruiter/application/1/candidate", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


def test_view_candidate_profile_nonexistent(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"is_active": 1}, None]
    response = client.get("/recruiter/application/999/candidate", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


# -----------------------------------
# RESUME ACCESS TESTS
# -----------------------------------


def test_view_candidate_resume_unauthenticated(client):
    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302


def test_view_candidate_resume_candidate_role(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "candidate"

    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302


def test_view_candidate_resume_success(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    pdf_file = upload_dir / "test_resume.pdf"
    pdf_file.write_text("fake pdf content")
    monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"is_active": 1}, {"resume_path": "test_resume.pdf"}]

    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"

    execute_calls = mock_db.execute.call_args_list
    resume_query_found = False
    for call in execute_calls:
        query, params = call[0]
        if "JOIN resumes r ON a.resume_id = r.id" in query:
            resume_query_found = True
            assert "r.user_id = a.candidate_id" in query
            assert "WHERE a.id = %s AND j.recruiter_id = %s" in query
            break
    assert resume_query_found


def test_view_candidate_resume_unauthorized(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"is_active": 1}, None]
    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


def test_view_candidate_resume_missing_db_record(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"is_active": 1}, None]
    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


def test_view_candidate_resume_missing_physical_file(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"is_active": 1}, {"resume_path": "valid_but_missing.pdf"}]
    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


def test_view_candidate_resume_path_traversal(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"is_active": 1}, {"resume_path": "../../../etc/passwd"}]
    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


def test_view_candidate_resume_non_pdf(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"is_active": 1}, {"resume_path": "malicious_script.exe"}]
    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


def test_view_candidate_resume_symlink_escape(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_pdf = outside_dir / "secret.pdf"
    outside_pdf.write_text("secret")

    symlink_path = upload_dir / "escape.pdf"
    try:
        os.symlink(outside_pdf, symlink_path)
    except OSError:
        pytest.skip("Symlinks not supported on this platform/configuration")

    monkeypatch.setitem(client.application.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"is_active": 1}, {"resume_path": "escape.pdf"}]
    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


# -----------------------------------
# FILTERING TESTS
# -----------------------------------


def test_applicant_filtering_success(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [
        {"is_active": 1},
        {
            "id": 1,
            "recruiter_id": 2,
            "job_title": "Developer",
            "location": "Remote",
            "experience": "0-2 years",
            "required_skills": "python,sql",
        },
    ]
    mock_db.fetchall.return_value = []

    response = client.get("/recruiter/job/1/applicants?q=alice&status=applied")
    assert response.status_code == 200

    execute_calls = mock_db.execute.call_args_list
    app_query_found = False
    for call in execute_calls:
        query = call[0][0]
        params = call[0][1]
        if "FROM applications a" in query and "JOIN users u" in query and "WHERE a.job_id = %s" in query:
            app_query_found = True
            assert "LIKE %s" in query
            assert "a.status = %s" in query
            assert "ORDER BY a.score DESC" in query
            assert "%alice%" in params
            assert "applied" in params
            assert "alice" not in query
            break

    assert app_query_found


def test_applicant_filtering_invalid_status(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [
        {"is_active": 1},
        {
            "id": 1,
            "recruiter_id": 2,
            "job_title": "Developer",
            "location": "Remote",
            "experience": "0-2 years",
            "required_skills": "python,sql",
        },
    ]
    mock_db.fetchall.return_value = []

    response = client.get("/recruiter/job/1/applicants?status=DROP TABLE")
    assert response.status_code == 200

    execute_calls = mock_db.execute.call_args_list
    app_query_found = False
    for call in execute_calls:
        query = call[0][0]
        params = call[0][1] if len(call[0]) > 1 else ()
        if "FROM applications a" in query and "JOIN users u" in query and "WHERE a.job_id = %s" in query:
            app_query_found = True
            assert "a.status = %s" not in query
            assert "DROP TABLE" not in query
            assert "ORDER BY a.score DESC" in query
            assert "DROP TABLE" not in params
            break

    assert app_query_found


def test_applicant_filtering_unauthorized(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"is_active": 1}, None]
    response = client.get("/recruiter/job/1/applicants?q=alice", follow_redirects=False)
    assert response.status_code == 302
    assert "/recruiter/dashboard" in response.headers["Location"]


# -----------------------------------
# TEMPLATE LINKS TESTS
# -----------------------------------


def test_template_links_use_application_id(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [
        {"is_active": 1},
        {
            "id": 1,
            "recruiter_id": 2,
            "job_title": "Developer",
            "location": "Remote",
            "experience": "0-2 years",
            "required_skills": "python,sql",
        },
    ]
    mock_db.fetchall.return_value = [
        {
            "id": 999,
            "candidate_id": 888,
            "candidate_name": "Test",
            "email": "test@t.c",
            "score": 50,
            "matched_skills": "",
            "missing_skills": "",
            "status": "applied",
            "applied_at": None,
        }
    ]

    response = client.get("/recruiter/job/1/applicants")
    html = response.data.decode("utf-8")

    assert "/recruiter/application/999/candidate" in html
    assert "/recruiter/application/999/resume" in html
    assert "/recruiter/application/888/" not in html
