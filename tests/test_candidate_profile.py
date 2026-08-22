from unittest.mock import MagicMock, patch
import pytest
from app import app

@pytest.fixture
def auth_client(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 100
        sess["name"] = "Test Candidate"
        sess["role"] = "candidate"
        sess["is_admin"] = False
    return client

@pytest.fixture
def recruiter_client(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 200
        sess["role"] = "recruiter"
        sess["is_admin"] = False
    return client

def setup_mock_db(mock_db, db_state=None):
    if db_state is None:
        db_state = {}
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cur
    
    last_query = {}
    def exe_se(q, p=None): last_query["q"] = q
    mock_cur.execute.side_effect = exe_se
    
    def fetchone_se():
        q = last_query.get("q", "")
        if "users" in q: return {"role": "candidate", "is_active": True}
        if "candidate_profiles" in q: return db_state.get("candidate_profiles")
        if "candidate_education" in q: return db_state.get("candidate_education")
        if "candidate_experience" in q: return db_state.get("candidate_experience")
        if "candidate_projects" in q: return db_state.get("candidate_projects")
        if "candidate_certifications" in q: return db_state.get("candidate_certifications")
        if "candidate_achievements" in q: return db_state.get("candidate_achievements")
        if "applications" in q: return db_state.get("applications", {"cnt": 0})
        if "resumes" in q: return db_state.get("resumes")
        return None
        
    mock_cur.fetchone.side_effect = fetchone_se
    return mock_cur

# --- SKILLS ---
@patch("routes.candidate.get_db_connection")
def test_skills_crud_normalization(mock_db, auth_client):
    mock_cur = setup_mock_db(mock_db, {"candidate_profiles": {"id": 1}})
    res = auth_client.post("/candidate/skills/edit", data={"skills": "Python, python,  Flask "})
    assert res.status_code == 302
    
    called_args = mock_cur.execute.call_args_list[-1][0]
    assert "UPDATE candidate_profiles" in called_args[0]
    assert called_args[1][0] == "Python,Flask"

def test_skills_profile_precedence_and_resume_fallback():
    from services.candidate_service import get_resolved_candidate_skills
    mock_cur = MagicMock()
    
    mock_cur.fetchone.side_effect = [{"skills": "python, django"}, {"skills": "react"}]
    assert get_resolved_candidate_skills(1, mock_cur) == ["python", "django"]
    
    mock_cur.fetchone.side_effect = [None, {"skills": "react"}]
    assert get_resolved_candidate_skills(1, mock_cur) == ["react"]
    
    mock_cur.fetchone.side_effect = [None, None]
    assert get_resolved_candidate_skills(1, mock_cur) == []

# --- EDUCATION ---
@patch("routes.candidate.get_db_connection")
def test_education_crud(mock_db, auth_client):
    mock_cur = setup_mock_db(mock_db)
    res = auth_client.post("/candidate/education/add", data={
        "institution": "MIT", "degree": "BS", "field_of_study": "CS",
        "start_date": "2018-09-01", "end_date": "2022-05-01"
    })
    assert res.status_code == 302
    
    mock_cur = setup_mock_db(mock_db)
    res = auth_client.post("/candidate/education/add", data={
        "institution": "MIT", "start_date": "2022-09-01", "end_date": "2018-05-01"
    })
    assert res.status_code == 302
    
    mock_cur = setup_mock_db(mock_db, {"candidate_education": None}) # Simulate IDOR failure
    res = auth_client.post("/candidate/education/1/delete")
    assert res.status_code == 403

# --- EXPERIENCE ---
@patch("routes.candidate.get_db_connection")
def test_experience_crud(mock_db, auth_client):
    mock_cur = setup_mock_db(mock_db)
    res = auth_client.post("/candidate/experience/add", data={
        "company": "Tech", "title": "Dev", "start_date": "2020-01-01", 
        "end_date": "2023-01-01", "is_current": "on"
    })
    assert res.status_code == 302
    params = mock_cur.execute.call_args_list[-1][0][1]
    assert params[5] is None
    
    mock_cur = setup_mock_db(mock_db)
    res = auth_client.post("/candidate/experience/add", data={
        "company": "Tech", "title": "Dev", "start_date": "2023-01-01", "end_date": "2020-01-01"
    })
    assert res.status_code == 302
    
    mock_cur = setup_mock_db(mock_db, {"candidate_experience": None})
    res = auth_client.post("/candidate/experience/1/delete")
    assert res.status_code == 403

# --- PROJECTS ---
@patch("routes.candidate.get_db_connection")
def test_projects_crud(mock_db, auth_client):
    mock_cur = setup_mock_db(mock_db)
    res = auth_client.post("/candidate/projects/add", data={
        "title": "My App", "url": "https://myapp.com"
    })
    assert res.status_code == 302
    
    mock_cur = setup_mock_db(mock_db)
    res = auth_client.post("/candidate/projects/add", data={
        "title": "My App", "url": "javascript:alert(1)"
    })
    assert res.status_code == 302
    
    mock_cur = setup_mock_db(mock_db, {"candidate_projects": None})
    res = auth_client.post("/candidate/projects/1/edit", data={"title": "Test"})
    assert res.status_code == 403

# --- CERTIFICATIONS ---
@patch("routes.candidate.get_db_connection")
def test_certifications_crud(mock_db, auth_client):
    mock_cur = setup_mock_db(mock_db)
    res = auth_client.post("/candidate/certifications/add", data={
        "name": "AWS", "issuer": "Amazon", "credential_url": "https://aws.com"
    })
    assert res.status_code == 302
    
    mock_cur = setup_mock_db(mock_db, {"candidate_certifications": None})
    res = auth_client.post("/candidate/certifications/1/delete")
    assert res.status_code == 403

# --- ACHIEVEMENTS ---
@patch("routes.candidate.get_db_connection")
def test_achievements_crud(mock_db, auth_client):
    mock_cur = setup_mock_db(mock_db)
    res = auth_client.post("/candidate/achievements/add", data={"title": "Hero"})
    assert res.status_code == 302
    
    mock_cur = setup_mock_db(mock_db, {"candidate_achievements": None})
    res = auth_client.post("/candidate/achievements/1/delete")
    assert res.status_code == 403

# --- AUTHORIZATION ---
def test_auth_blocks_unauthenticated_and_recruiters(client, recruiter_client):
    res = client.post("/candidate/education/add", data={"institution": "Test"})
    assert res.status_code == 302
    
    res = recruiter_client.post("/candidate/education/add", data={"institution": "Test"})
    assert res.status_code == 302

# --- PROFILE COMPLETION ---
@patch("routes.candidate.get_db_connection")
def test_profile_completion_formulas(mock_db, auth_client):
    mock_cur = setup_mock_db(mock_db)
    mock_cur.fetchall.return_value = []
    res = auth_client.get("/candidate/profile")
    assert b'0%' in res.data
    
    def fresher_list_se():
        q = last_query.get("q", "")
        if "education" in q: return [{"id": 1}]
        if "projects" in q: return [{"id": 1}]
        if "certifications" in q: return [{"id": 1}]
        return []
        
    mock_cur = setup_mock_db(mock_db, {
        "candidate_profiles": {"bio": "a", "phone": "b", "location": "c", "linkedin_url": "d", "github_url": "e", "portfolio_url": "f"},
        "resumes": {"skills": "python"}
    })
    # Extract last_query reference from the new mock_cur
    last_query = mock_cur.execute.side_effect.__closure__[0].cell_contents
    mock_cur.fetchall.side_effect = fresher_list_se
    res = auth_client.get("/candidate/profile")
    assert b'95%' in res.data
    
    def experienced_list_se():
        q = last_query.get("q", "")
        if "education" in q: return [{"id": 1}]
        if "experience" in q: return [{"id": 1}, {"id": 2}]
        if "projects" in q: return [{"id": 1}]
        if "certifications" in q: return [{"id": 1}]
        if "achievements" in q: return [{"id": 1}]
        return []

    mock_cur = setup_mock_db(mock_db, {
        "candidate_profiles": {"bio": "a", "phone": "b", "location": "c", "linkedin_url": "d", "github_url": "e", "portfolio_url": "f"},
        "resumes": {"skills": "python"}
    })
    last_query = mock_cur.execute.side_effect.__closure__[0].cell_contents
    mock_cur.fetchall.side_effect = experienced_list_se
    res = auth_client.get("/candidate/profile")
    assert b'100%' in res.data
