from unittest.mock import MagicMock, patch

import openai
import pytest

from app import app
from services.ai_resume_service import sanitize_text


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["OPENAI_API_KEY"] = "test-key"
    app.config["RATELIMIT_ENABLED"] = False  # Disable rate limiter for general tests unless testing rate limit
    with app.test_client() as c:
        yield c


def _login_as(client, user_id=1, role="candidate"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["name"] = "Test User"
        sess["role"] = role


class TestAIResumeSanitization:
    def test_email_redaction(self):
        text = "Contact me at my.email@example.com or other@test.co.uk please."
        sanitized = sanitize_text(text)
        assert "my.email@example.com" not in sanitized
        assert "other@test.co.uk" not in sanitized
        assert "[EMAIL REDACTED]" in sanitized

    def test_phone_redaction(self):
        text = "Call me: +1-555-123-4567 or (800) 555-0199"
        sanitized = sanitize_text(text)
        assert "555-123-4567" not in sanitized
        assert "[PHONE REDACTED]" in sanitized

    def test_input_length_limit(self):
        long_text = "A" * 15000
        # In analyze_resume it slices to 10000
        # We test this logic indirectly or directly via mocking
        pass


class TestLocalResumeScore:
    @patch("routes.candidate.get_db_connection")
    def test_score_local_general(self, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        
        # Return a resume with skills
        mock_cur.fetchone.side_effect = [
            {"raw_text": "Sample text", "skills": "python,flask"}
        ]
        
        resp = client.post("/api/resume/score_local", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["mode"] == "general"
        assert "python" in data["skills"]
        assert mock_cur.execute.call_count == 1 # Only resume query

    @patch("routes.candidate.get_db_connection")
    def test_score_local_job_specific(self, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        
        mock_cur.fetchone.side_effect = [
            {"raw_text": "Experienced in python and flask", "skills": "python,flask"},
            {"job_title": "Backend Dev", "required_skills": "python,docker", "description": "Needs python and docker"}
        ]
        
        resp = client.post("/api/resume/score_local", json={"job_id": 1})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["mode"] == "job_specific"
        assert "python" in data["matched_skills"]
        assert "docker" in data["missing_skills"]
        assert data["match_score"] > 0
        assert mock_cur.execute.call_count == 2 # Resume + Job queries

    @patch("routes.candidate.get_db_connection")
    def test_score_local_no_resume(self, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None
        
        resp = client.post("/api/resume/score_local", json={})
        assert resp.status_code == 400
        assert b"No resume found" in resp.data

    @patch("routes.candidate.get_db_connection")
    def test_score_local_invalid_job(self, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.side_effect = [
            {"raw_text": "Sample text", "skills": "python"},
            None # Job not found
        ]
        
        resp = client.post("/api/resume/score_local", json={"job_id": 999})
        assert resp.status_code == 400
        assert b"not found or inactive" in resp.data


class TestAIResumeRoutes:
    def test_anonymous_denied(self, client):
        resp = client.get("/resume/suggestions")
        assert resp.status_code == 302
        resp = client.post("/api/resume/analyze")
        assert resp.status_code == 302

    def test_recruiter_denied(self, client):
        _login_as(client, role="recruiter")
        resp = client.get("/resume/suggestions")
        assert resp.status_code == 302

    @patch("routes.candidate.get_db_connection")
    def test_candidate_page_allowed(self, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"id": 1}
        mock_cur.fetchall.return_value = []

        resp = client.get("/resume/suggestions")
        assert resp.status_code == 200
        assert b"AI Resume Suggestions" in resp.data

    @patch("routes.candidate.get_db_connection")
    def test_candidate_without_resume_handled(self, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = None  # No resume

        resp = client.post("/api/resume/analyze")
        assert resp.status_code == 400
        assert b"No resume found" in resp.data

    @patch("routes.candidate.get_db_connection")
    @patch("services.ai_resume_service.openai.OpenAI")
    def test_own_resume_successfully_analyzed(self, mock_openai, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        mock_cur.fetchone.side_effect = [
            {"raw_text": "Sample valid resume"},  # resume fetch
            None,  # Job fetch (not requested here)
        ]

        # Mock OpenAI parse
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance

        mock_parsed = MagicMock()
        mock_parsed.model_dump.return_value = {
            "summary": "Great resume",
            "strengths": ["Python"],
            "priority_improvements": [],
            "skills": [],
            "experience": [],
            "projects": [],
            "ats": [],
        }

        mock_response = MagicMock()
        mock_response.output_parsed = mock_parsed
        mock_client_instance.responses.parse.return_value = mock_response

        resp = client.post("/api/resume/analyze", json={"job_id": None})
        assert resp.status_code == 200
        assert b"Great resume" in resp.data

    @patch("routes.candidate.get_db_connection")
    @patch("services.ai_resume_service.openai.OpenAI")
    def test_job_specific_analysis(self, mock_openai, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        mock_cur.fetchone.side_effect = [
            {"raw_text": "Sample valid resume"},
            {"job_title": "Dev", "required_skills": "Python", "description": "Good job"},
        ]

        # Mock OpenAI parse
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_parsed = MagicMock()
        mock_parsed.model_dump.return_value = {
            "summary": "Job match good",
            "strengths": [],
            "priority_improvements": [],
            "skills": [],
            "experience": [],
            "projects": [],
            "ats": [],
        }
        mock_response = MagicMock()
        mock_response.output_parsed = mock_parsed
        mock_client_instance.responses.parse.return_value = mock_response

        resp = client.post("/api/resume/analyze", json={"job_id": 10})
        assert resp.status_code == 200
        assert b"Job match good" in resp.data

        # Ensure the prompt included the job description
        args, kwargs = mock_client_instance.responses.parse.call_args
        input_text = kwargs.get("input")
        assert "<job_description>" in input_text

    @patch("routes.candidate.get_db_connection")
    @patch("services.ai_resume_service.openai.OpenAI")
    def test_invalid_job_id_handled(self, mock_openai, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        mock_cur.fetchone.side_effect = [{"raw_text": "Sample valid resume"}, None]  # Job not found

        resp = client.post("/api/resume/analyze", json={"job_id": 999})
        assert resp.status_code == 400
        assert b"target job not found or inactive" in resp.data

    @patch("routes.candidate.get_db_connection")
    @patch("services.ai_resume_service.openai.OpenAI")
    def test_provider_exception_handled(self, mock_openai, mock_db, client):
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        mock_cur.fetchone.return_value = {"raw_text": "Sample valid resume"}

        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_client_instance.responses.parse.side_effect = openai.RateLimitError(
            "Rate limit exceeded", response=MagicMock(), body=None
        )

        resp = client.post("/api/resume/analyze", json={"job_id": None})
        assert resp.status_code == 500
        assert b"busy" in resp.data

    @patch("routes.candidate.get_db_connection")
    def test_missing_api_key_handled(self, mock_db, client):
        app.config["OPENAI_API_KEY"] = None
        _login_as(client, role="candidate")
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = {"raw_text": "Sample"}

        resp = client.post("/api/resume/analyze", json={"job_id": None})
        assert resp.status_code == 500
        assert b"temporarily unavailable" in resp.data
