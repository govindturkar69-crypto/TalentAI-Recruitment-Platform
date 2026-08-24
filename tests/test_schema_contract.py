import os

import pymysql
import pytest


def get_test_db_connection():
    test_db = os.environ.get("TEST_DB_NAME", "test_db")
    if test_db not in ["test_db"]:
        pytest.fail(f"ABORT: TEST_DB_NAME '{test_db}' is not an explicitly whitelisted test database.")

    host = os.environ.get("TEST_DB_HOST", "127.0.0.1")
    if host not in ["localhost", "127.0.0.1", "mysql"]:
        pytest.fail(f"ABORT: Host '{host}' is forbidden in schema integration tests.")

    return pymysql.connect(
        host=host,
        user=os.environ.get("TEST_DB_USER", "root"),
        password=os.environ.get("TEST_DB_PASSWORD", "root"),
        database=test_db,
        cursorclass=pymysql.cursors.DictCursor,
    )


def test_schema_contract_users():
    """Verify canonical schema contains required users table objects."""
    conn = get_test_db_connection()
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM users")
    columns = {row["Field"] for row in cur.fetchall()}
    assert "id" in columns
    assert "is_active" in columns
    assert "company_id" in columns
    cur.close()
    conn.close()


def test_schema_contract_jobs():
    """Verify canonical schema contains required jobs table objects."""
    conn = get_test_db_connection()
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM jobs")
    rows = cur.fetchall()
    columns = {row["Field"]: row for row in rows}

    assert "id" in columns
    assert "recruiter_id" in columns
    assert "job_title" in columns
    assert "is_active" in columns

    # Explicitly assert jobs.is_active properties
    col_def = columns["is_active"]
    assert col_def["Null"] == "NO"
    assert col_def["Default"] == "1"

    cur.close()
    conn.close()


def test_schema_contract_candidate_profiles():
    """Verify canonical schema contains required candidate_profiles table objects."""
    conn = get_test_db_connection()
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM candidate_profiles")
    columns = {row["Field"] for row in cur.fetchall()}
    assert "user_id" in columns
    assert "skills" in columns
    cur.close()
    conn.close()


def test_schema_contract_tables_exist():
    """Verify canonical schema contains required tables including Phase 1B."""
    conn = get_test_db_connection()
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = {list(row.values())[0] for row in cur.fetchall()}
    required_tables = {
        "users",
        "jobs",
        "applications",
        "resumes",
        "candidate_profiles",
        "companies",
        "audit_logs",
        "candidate_education",
        "candidate_experience",
        "candidate_projects",
        "candidate_certifications",
        "candidate_achievements",
        "saved_jobs",
    }
    assert required_tables.issubset(tables)
    cur.close()
    conn.close()


def test_schema_contract_saved_jobs():
    """Verify canonical schema contains required saved_jobs table objects."""
    conn = get_test_db_connection()
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM saved_jobs")
    rows = cur.fetchall()
    columns = {row["Field"]: row for row in rows}

    assert "id" in columns
    assert "candidate_id" in columns
    assert "job_id" in columns
    assert "saved_at" in columns

    # Verify attributes
    assert columns["id"]["Key"] == "PRI"
    assert "auto_increment" in columns["id"]["Extra"].lower()

    assert columns["candidate_id"]["Null"] == "NO"
    assert columns["job_id"]["Null"] == "NO"

    # Check default on saved_at (could be CURRENT_TIMESTAMP)
    assert columns["saved_at"]["Default"] is not None or columns["saved_at"]["Extra"] != ""

    cur.execute("SHOW CREATE TABLE saved_jobs")
    create_table = cur.fetchone()["Create Table"]

    normalized_create = " ".join(create_table.split())

    # Check foreign keys ignoring auto-generated names
    assert "FOREIGN KEY (`candidate_id`) REFERENCES `users` (`id`) ON DELETE CASCADE" in normalized_create

    assert "FOREIGN KEY (`job_id`) REFERENCES `jobs` (`id`) ON DELETE CASCADE" in normalized_create

    # Check UNIQUE constraint
    assert "UNIQUE KEY" in normalized_create and "`candidate_id`" in normalized_create and "`job_id`" in normalized_create

    cur.close()
    conn.close()
