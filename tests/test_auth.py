def test_login_success(client, mock_db):
    # Mocking user validation
    mock_db.fetchone.return_value = {
        "id": 1,
        "email": "test@test.com",
        "password": "scrypt:32768:8:1$test$test",
        "role": "candidate",
        "name": "Test User",
    }

    from werkzeug.security import generate_password_hash

    mock_db.fetchone.return_value["password"] = generate_password_hash("password123")

    response = client.post("/login", data={"email": "test@test.com", "password": "password123"}, follow_redirects=False)

    assert response.status_code == 302
    assert "/candidate/dashboard" in response.headers["Location"]


def test_login_failure(client, mock_db):
    mock_db.fetchone.return_value = None
    response = client.post(
        "/login", data={"email": "test@test.com", "password": "wrongpassword"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Incorrect email or password." in response.data


def test_register_duplicate_email(client, mock_db):
    mock_db.execute.side_effect = Exception("Duplicate email")

    response = client.post(
        "/register",
        data={"name": "Test User", "email": "test@test.com", "password": "password123", "role": "candidate"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Registration could not be completed" in response.data
