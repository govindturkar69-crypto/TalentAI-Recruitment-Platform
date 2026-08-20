"""Tests for the public Flask routes.

These use the `client` fixture from conftest.py — a fake browser that sends
requests to the app in memory. No real server, no real database.

We only test routes that don't need a database here: pages that render a
template, and the access-control checks that redirect before any query runs.
"""


def test_homepage_loads(client):
    response = client.get("/")
    assert response.status_code == 200


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"login" in response.data.lower()


def test_register_page_loads(client):
    response = client.get("/register")
    assert response.status_code == 200


def test_healthz_returns_ok(client):
    # The health-check endpoint may report the DB as down in tests, but the
    # route itself must always respond rather than crash.
    response = client.get("/healthz")
    assert response.status_code in (200, 503)


def test_unknown_page_returns_404(client):
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Access control: protected pages must redirect a logged-out visitor to login
# ---------------------------------------------------------------------------


def test_candidate_dashboard_requires_login(client):
    response = client.get("/candidate/dashboard")
    # 302 = redirect (to the login page)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_recruiter_dashboard_requires_login(client):
    response = client.get("/recruiter/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_upload_resume_requires_login(client):
    response = client.get("/candidate/upload_resume")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_job_requires_login(client):
    response = client.get("/recruiter/post_job")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_redirects(client):
    response = client.post("/logout")
    assert response.status_code == 302
