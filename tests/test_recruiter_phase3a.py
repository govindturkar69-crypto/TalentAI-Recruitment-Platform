from flask import current_app

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

    # app_data, profile, education, experience, projects, certifications, achievements
    mock_db.fetchone.side_effect = [
        {"cnt": 0},  # unread
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

    mock_db.fetchone.side_effect = [{"cnt": 0}, None]
    response = client.get("/recruiter/application/1/candidate", follow_redirects=True)
    assert response.status_code == 200
    assert b"Application not found" in response.data


def test_view_candidate_profile_nonexistent(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"cnt": 0}, None]
    response = client.get("/recruiter/application/999/candidate", follow_redirects=True)
    assert response.status_code == 200
    assert b"Application not found" in response.data


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
    monkeypatch.setitem(current_app.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"cnt": 0}, {"resume_path": "test_resume.pdf"}]

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

    mock_db.fetchone.side_effect = [{"cnt": 0}, None]
    response = client.get("/recruiter/application/1/resume", follow_redirects=True)
    assert b"Resume not found" in response.data


def test_view_candidate_resume_missing_db_record(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"cnt": 0}, None]
    response = client.get("/recruiter/application/1/resume", follow_redirects=True)
    assert b"Resume not found" in response.data


def test_view_candidate_resume_missing_physical_file(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setitem(current_app.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"cnt": 0}, {"resume_path": "valid_but_missing.pdf"}]
    response = client.get("/recruiter/application/1/resume", follow_redirects=True)
    assert b"Resume file not found on server" in response.data


def test_view_candidate_resume_path_traversal(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setitem(current_app.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"cnt": 0}, {"resume_path": "../../../etc/passwd"}]
    response = client.get("/recruiter/application/1/resume", follow_redirects=True)
    assert b"Invalid resume file path" in response.data


def test_view_candidate_resume_non_pdf(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setitem(current_app.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"cnt": 0}, {"resume_path": "malicious_script.exe"}]
    response = client.get("/recruiter/application/1/resume", follow_redirects=True)
    assert b"Invalid resume file format" in response.data


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

    # Try to create symlink if os supports it, or just use absolute path to simulate
    monkeypatch.setitem(current_app.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [{"cnt": 0}, {"resume_path": str(outside_pdf.resolve())}]
    response = client.get("/recruiter/application/1/resume", follow_redirects=True)
    assert b"Invalid resume file path" in response.data


# -----------------------------------
# FILTERING TESTS
# -----------------------------------


def test_applicant_filtering_success(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"cnt": 0}, {"id": 1, "recruiter_id": 2}]
    mock_db.fetchall.return_value = []

    response = client.get("/recruiter/job/1/applicants?q=alice&status=applied")
    assert response.status_code == 200

    execute_calls = mock_db.execute.call_args_list
    query = execute_calls[-1][0][0]
    params = execute_calls[-1][0][1]

    assert "LIKE %s" in query
    assert "a.status = %s" in query
    assert "%alice%" in params
    assert "applied" in params


def test_applicant_filtering_invalid_status(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"cnt": 0}, {"id": 1, "recruiter_id": 2}]
    mock_db.fetchall.return_value = []

    response = client.get("/recruiter/job/1/applicants?status=DROP TABLE")
    assert response.status_code == 200

    execute_calls = mock_db.execute.call_args_list
    query = execute_calls[-1][0][0]

    assert "a.status = %s" not in query
    assert "DROP TABLE" not in query
    assert "ORDER BY a.score DESC" in query


def test_applicant_filtering_unauthorized(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"cnt": 0}, None]
    response = client.get("/recruiter/job/1/applicants?q=alice", follow_redirects=True)
    assert response.status_code == 200
    assert b"Job not found" in response.data


# -----------------------------------
# TEMPLATE LINKS TESTS
# -----------------------------------


def test_template_links_use_application_id(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    mock_db.fetchone.side_effect = [{"cnt": 0}, {"id": 1, "recruiter_id": 2}]
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
        }
    ]

    response = client.get("/recruiter/job/1/applicants")
    html = response.data.decode("utf-8")

    assert "/recruiter/application/999/candidate" in html
    assert "/recruiter/application/999/resume" in html
    assert "/recruiter/application/888/" not in html
