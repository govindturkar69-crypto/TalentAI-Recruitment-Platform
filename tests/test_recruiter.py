def test_post_job_unauthenticated(client):
    response = client.post("/recruiter/post_job", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_job_success(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    # Add cnt: 0 to satisfy inject_unread_count context processor
    mock_db.fetchone.return_value = {"cnt": 0}

    response = client.post(
        "/recruiter/post_job",
        data={
            "job_title": "Engineer",
            "required_skills": "Python, SQL",
            "description": "A good job",
            "location": "Remote",
            "experience": "2 years",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"posted successfully!" in response.data
    assert mock_db.execute.called


def test_edit_job_missing_fields(client, mock_db):
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["role"] = "recruiter"

    # Provide cnt:0 for inject_unread_count
    mock_db.fetchone.return_value = {"id": 1, "recruiter_id": 2, "job_title": "Old", "cnt": 0}

    response = client.post(
        "/recruiter/job/1/edit",
        data={
            "job_title": "",  # missing title
            "required_skills": "Python",
            "description": "",
            "location": "",
            "experience": "",
        },
        follow_redirects=True,
    )

    assert b"Title and required skills are mandatory." in response.data
