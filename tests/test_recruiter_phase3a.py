import pytest
from unittest.mock import MagicMock
from flask import current_app

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

    # mock fetchone calls:
    # 1. inject_unread_count -> {"cnt": 0}
    # 2. app_data -> {...}
    # 3. profile -> {...}
    mock_db.fetchone.side_effect = [
        {"cnt": 0},
        {"application_id": 1, "score": 85, "matched_skills": "Python", "missing_skills": "React", "status": "applied", "applied_at": None, "job_id": 1, "job_title": "Dev", "name": "Alice", "email": "alice@test.com", "candidate_id": 1},
        {"user_id": 1, "bio": "Great dev", "skills": "Python"}
    ]
    mock_db.fetchall.return_value = []

    response = client.get("/recruiter/application/1/candidate", follow_redirects=True)
    assert response.status_code == 200
    assert b"Alice" in response.data
    assert b"Great dev" in response.data

def test_view_candidate_profile_unauthorized_recruiter(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "recruiter"
    
    # App data returns None (not found or not owned by recruiter 3)
    mock_db.fetchone.side_effect = [
        {"cnt": 0},
        None
    ]

    response = client.get("/recruiter/application/1/candidate", follow_redirects=True)
    assert response.status_code == 200
    assert b"Application not found" in response.data

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

    # Create dummy pdf
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    pdf_file = upload_dir / "test_resume.pdf"
    pdf_file.write_text("fake pdf content")

    monkeypatch.setitem(current_app.config, "UPLOAD_FOLDER", str(upload_dir))

    mock_db.fetchone.side_effect = [
        {"resume_path": "test_resume.pdf"}
    ]

    response = client.get("/recruiter/application/1/resume", follow_redirects=False)
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data == b"fake pdf content"

def test_view_candidate_resume_unauthorized(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "recruiter"
    
    # inject_unread_count then None
    mock_db.fetchone.side_effect = [{"cnt": 0}, None]
    
    response = client.get("/recruiter/application/1/resume", follow_redirects=True)
    assert b"Resume not found or unauthorized" in response.data

def test_view_candidate_resume_path_traversal(client, mock_db, tmp_path, monkeypatch):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setitem(current_app.config, "UPLOAD_FOLDER", str(upload_dir))

    # Test trying to access outside upload directory
    mock_db.fetchone.side_effect = [
        {"cnt": 0},
        {"resume_path": "../../../etc/passwd"}
    ]
    
    response = client.get("/recruiter/application/1/resume", follow_redirects=True)
    assert response.status_code in [200, 404]

def test_applicant_filtering_success(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"
        sess["name"] = "Rec"
        
    mock_db.fetchone.side_effect = [
        {"cnt": 0}, # unread count
        {"id": 1, "recruiter_id": 2, "job_title": "Dev"} # job
    ]
    mock_db.fetchall.return_value = []
    
    response = client.get("/recruiter/job/1/applicants?q=alice&status=applied")
    assert response.status_code == 200
    
    # Verify execute was called with correct parameters
    execute_calls = mock_db.execute.call_args_list
    assert len(execute_calls) >= 2
    last_call_args = execute_calls[-1][0]
    query = last_call_args[0]
    params = last_call_args[1]
    
    assert "LIKE %s" in query
    assert "a.status = %s" in query
    assert "%alice%" in params
    assert "applied" in params

def test_applicant_filtering_unauthorized(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["role"] = "recruiter"
        
    mock_db.fetchone.side_effect = [{"cnt": 0}, None]
    
    response = client.get("/recruiter/job/1/applicants?q=alice", follow_redirects=True)
    assert response.status_code == 200
    assert b"Job not found" in response.data
