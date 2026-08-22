def test_apply_job_unauthenticated(client):
    response = client.post("/candidate/apply/1", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_apply_job_duplicate_prevented(client, mock_db):
    # Setup session
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "candidate"
        sess["name"] = "Candidate"

    # First fetchone is is_active check, second is the resume check, third is the duplicate application check
    mock_db.fetchone.side_effect = [
        {"is_active": True},
        {"id": 10, "skills": "python", "raw_text": "resume text"},  # Resume found
        {"id": 5},  # Duplicate application found
    ]

    response = client.post("/candidate/apply/1", follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        # Flash messages are stored in session['_flashes']
        flashes = sess.get("_flashes", [])
        assert any(b"already applied" in str(msg).encode() for cat, msg in flashes)


def test_withdraw_hired_application(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "candidate"

    # Mock finding a hired application (with is_active True for login_required)
    mock_db.fetchone.side_effect = [
        {"is_active": True},
        {"id": 5, "job_title": "Dev", "status": "hired"}
    ]

    response = client.post("/candidate/withdraw/5", follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
        assert any(
            b"can&#39;t withdraw" in str(msg).encode() or b"can't withdraw" in str(msg).encode() for cat, msg in flashes
        )
