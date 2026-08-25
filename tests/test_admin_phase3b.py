def _login_as(client, user_id=1, role="candidate", email="user@test.com"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role
        sess["email"] = email


def test_admin_companies_page_access(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")

    # 1. Unauthenticated
    response = client.get("/admin/companies", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # 2. Candidate
    _login_as(client, role="candidate", email="cand@company.com")
    mock_db.fetchone.return_value = {"email": "cand@company.com", "is_active": True}
    response = client.get("/admin/companies", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    # 3. Recruiter (non-admin)
    _login_as(client, role="recruiter", email="rec@company.com")
    mock_db.fetchone.return_value = {"email": "rec@company.com", "is_active": True}
    response = client.get("/admin/companies", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    # 4. Admin
    _login_as(client, role="candidate", email="admin@company.com")
    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},  # login_required
    ]
    mock_db.fetchall.return_value = [{"id": 1, "name": "Test Co", "is_active": True, "recruiter_count": 0}]
    response = client.get("/admin/companies", follow_redirects=False)
    assert response.status_code == 200
    assert b"Test Co" in response.data


def test_admin_create_company(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    # Success
    mock_db.fetchone.return_value = {"email": "admin@company.com", "is_active": True}
    mock_db.lastrowid = 5
    response = client.post(
        "/admin/companies/create",
        data={"name": "New Co", "description": "A new company", "website": "https://newco.com"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/admin/companies" in response.headers["Location"]

    company_insert_calls = [call for call in mock_db.execute.call_args_list if "INSERT INTO companies" in call[0][0]]
    assert len(company_insert_calls) == 1
    query, params = company_insert_calls[0][0]
    assert params == ("New Co", "A new company", "https://newco.com")

    audit_insert_calls = [call for call in mock_db.execute.call_args_list if "INSERT INTO audit_logs" in call[0][0]]
    assert len(audit_insert_calls) == 1
    import json

    audit_params = audit_insert_calls[0][0][1]
    assert "create_company" in audit_params
    details = json.loads(audit_params[4])
    assert details == {"company_name": "New Co"}


def test_admin_create_company_validation(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")
    mock_db.fetchone.return_value = {"email": "admin@company.com", "is_active": True}

    # Empty name
    response = client.post("/admin/companies/create", data={"name": "   ", "website": ""}, follow_redirects=False)
    assert response.status_code == 302
    for call in mock_db.execute.call_args_list:
        assert "INSERT INTO companies" not in call[0][0]

    # Bad websites
    bad_urls = ["javascript:alert(1)", "https://", "http://", "ftp://example.com"]
    for url in bad_urls:
        mock_db.execute.reset_mock()
        response = client.post(
            "/admin/companies/create",
            data={"name": "Test", "website": url},
            follow_redirects=False,
        )
        assert response.status_code == 302
        for call in mock_db.execute.call_args_list:
            assert "INSERT INTO companies" not in call[0][0]

    # Good website
    mock_db.execute.reset_mock()
    response = client.post(
        "/admin/companies/create",
        data={"name": "Test", "website": "https://example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    insert_found = False
    for call in mock_db.execute.call_args_list:
        if "INSERT INTO companies" in call[0][0]:
            insert_found = True
    assert insert_found


def test_admin_edit_company(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [{"email": "admin@company.com", "is_active": True}, {"id": 1, "name": "Old Co"}]
    response = client.post(
        "/admin/companies/1/edit",
        data={"name": "Updated Co", "description": "Desc", "website": "http://updated.com"},
        follow_redirects=False,
    )

    assert response.status_code == 302

    update_found = False
    for call in mock_db.execute.call_args_list:
        if "UPDATE companies SET name = %s" in call[0][0]:
            update_found = True
            assert call[0][1] == ("Updated Co", "Desc", "http://updated.com", 1)
    assert update_found

    audit_insert_calls = [call for call in mock_db.execute.call_args_list if "INSERT INTO audit_logs" in call[0][0]]
    assert len(audit_insert_calls) == 1
    import json

    audit_params = audit_insert_calls[0][0][1]
    assert "update_company" in audit_params
    details = json.loads(audit_params[4])
    assert details == {
        "previous_name": "Old Co",
        "new_name": "Updated Co",
    }


def test_admin_edit_company_invalid_website(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    # Bad websites
    bad_urls = ["javascript:alert(1)", "https://"]
    for url in bad_urls:
        mock_db.execute.reset_mock()
        mock_db.fetchone.side_effect = [{"email": "admin@company.com", "is_active": True}, {"id": 1, "name": "Old Co"}]
        response = client.post(
            "/admin/companies/1/edit", data={"name": "Updated Co", "website": url}, follow_redirects=False
        )
        assert response.status_code == 302
        for call in mock_db.execute.call_args_list:
            assert "UPDATE companies SET name = %s" not in call[0][0]


def test_admin_edit_company_nonexistent(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [{"email": "admin@company.com", "is_active": True}, None]  # company not found
    response = client.post("/admin/companies/99/edit", data={"name": "Test"}, follow_redirects=False)
    assert response.status_code == 302


def test_admin_assign_company_success(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},
        {"id": 2, "role": "recruiter", "company_id": None},
        {"id": 5, "is_active": True},
    ]

    response = client.post("/admin/users/2/company", data={"company_id": "5"}, follow_redirects=False)
    assert response.status_code == 302

    update_found = False
    for call in mock_db.execute.call_args_list:
        sql = call[0][0]
        params = call[0][1] if len(call[0]) > 1 else ()
        if "UPDATE users SET company_id = %s" in sql:
            update_found = True
            assert params == (5, 2)
    assert update_found

    audit_insert_calls = [call for call in mock_db.execute.call_args_list if "INSERT INTO audit_logs" in call[0][0]]
    assert len(audit_insert_calls) == 1
    import json

    audit_params = audit_insert_calls[0][0][1]
    assert "assign_recruiter_company" in audit_params
    details = json.loads(audit_params[4])
    assert details == {
        "previous_company_id": None,
        "new_company_id": 5,
    }


def test_admin_assign_company_null(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},
        {"id": 2, "role": "recruiter", "company_id": 5},
    ]

    response = client.post("/admin/users/2/company", data={"company_id": ""}, follow_redirects=False)
    assert response.status_code == 302

    update_found = False
    for call in mock_db.execute.call_args_list:
        if "UPDATE users SET company_id = %s" in call[0][0]:
            update_found = True
            assert call[0][1] == (None, 2)
    assert update_found


def test_admin_assign_company_candidate_rejected(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},
        {"id": 3, "role": "candidate", "company_id": None},
    ]

    response = client.post("/admin/users/3/company", data={"company_id": "5"}, follow_redirects=False)
    assert response.status_code == 302

    for call in mock_db.execute.call_args_list:
        assert "UPDATE users SET company_id" not in call[0][0]


def test_admin_assign_inactive_company(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},
        {"id": 2, "role": "recruiter", "company_id": None},
        {"id": 5, "is_active": False},
    ]

    response = client.post("/admin/users/2/company", data={"company_id": "5"}, follow_redirects=False)
    assert response.status_code == 302

    for call in mock_db.execute.call_args_list:
        assert "UPDATE users SET company_id" not in call[0][0]


def test_admin_assign_company_invalid_id(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},
        {"id": 2, "role": "recruiter", "company_id": None},
    ]

    response = client.post("/admin/users/2/company", data={"company_id": "abc"}, follow_redirects=False)
    assert response.status_code == 302

    for call in mock_db.execute.call_args_list:
        assert "UPDATE users SET company_id" not in call[0][0]

    mock_db.execute.reset_mock()
    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},
        {"id": 2, "role": "recruiter", "company_id": None},
    ]

    response = client.post("/admin/users/2/company", data={"company_id": "-1"}, follow_redirects=False)
    assert response.status_code == 302

    for call in mock_db.execute.call_args_list:
        assert "UPDATE users SET company_id" not in call[0][0]


def test_admin_assign_company_nonexistent(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},
        {"id": 2, "role": "recruiter", "company_id": None},
        None,  # company 999 not found
    ]

    response = client.post("/admin/users/2/company", data={"company_id": "999"}, follow_redirects=False)
    assert response.status_code == 302

    company_lookup_found = False
    for call in mock_db.execute.call_args_list:
        sql = call[0][0]
        params = call[0][1] if len(call[0]) > 1 else ()
        assert "UPDATE users SET company_id" not in sql
        if "SELECT id, is_active FROM companies WHERE id = %s" in sql:
            company_lookup_found = True
            assert params == (999,)
    assert company_lookup_found


def test_admin_reassign_company(client, monkeypatch, mock_db):
    monkeypatch.setitem(client.application.config, "ADMIN_EMAIL", "admin@company.com")
    _login_as(client, email="admin@company.com")

    mock_db.fetchone.side_effect = [
        {"email": "admin@company.com", "is_active": True},
        {"id": 2, "role": "recruiter", "company_id": 5},
        {"id": 6, "is_active": True},
    ]

    response = client.post("/admin/users/2/company", data={"company_id": "6"}, follow_redirects=False)
    assert response.status_code == 302

    update_found = False
    for call in mock_db.execute.call_args_list:
        sql = call[0][0]
        params = call[0][1] if len(call[0]) > 1 else ()
        if "UPDATE users SET company_id = %s WHERE id = %s" in sql:
            update_found = True
            assert params == (6, 2)
    assert update_found

    audit_insert_calls = [call for call in mock_db.execute.call_args_list if "INSERT INTO audit_logs" in call[0][0]]
    assert len(audit_insert_calls) == 1
    import json

    audit_params = audit_insert_calls[0][0][1]
    assert "assign_recruiter_company" in audit_params
    details = json.loads(audit_params[4])
    assert details == {
        "previous_company_id": 5,
        "new_company_id": 6,
    }
