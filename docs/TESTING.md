# Testing Documentation

## Documentation Basis

- Repository branch: `main`
- Repository HEAD: `891d7ac4947d7a4153d2da7389aabdaf116e3b52`
- Release snapshot: `v1.0.0`
- Analysis method: Static repository inspection
- Runtime verification: Present but not runtime-verified (documentation-only analysis)
- Generated/updated: `2026-09-11`

---

## Testing Strategy

TalentAI employs a multi-tiered automated testing strategy designed to validate core parsing, security boundaries, status machine rules, and database schema contracts:
1. **Unit Testing with In-Memory Mocks**: Fast, decoupled tests that execute without requiring a real database instance. The shared `conftest.py` fixture patches `get_db_connection` across all modules with `unittest.mock.MagicMock` objects.
2. **Schema Contract Testing**: Validates that canonical database tables, columns, data types, nullability, defaults, foreign keys, and indexes match strict architectural contracts against an active MySQL 8.4 instance.
3. **Database Integration Testing**: Verifies multi-step database transactions, status transitions, interview auto-cancellation, and role guards on a dedicated test database (`test_phase4a.py`, `test_phase4b.py`).
4. **Migration Path & Reconciliation Verification**: Tests sequential schema migrations and backfill routines against baseline and drift fixtures.

---

## Framework

- **Test Runner**: `pytest` (version 8.3.3)
- **Mocking Library**: Python standard library `unittest.mock` (`patch`, `MagicMock`)
- **HTTP Client**: Flask Test Client (`app.test_client()`) with CSRF disabled for test isolation (`WTF_CSRF_ENABLED = False`)
- **Linting & Code Quality**: `ruff` (version 0.6.5) and `black` (version 24.8.0)
- **Bytecode Verification**: Python standard library `compileall`

---

## Test Structure

All tests reside in the `tests/` directory:

```
tests/
├── __init__.py
├── conftest.py                       # Global Pytest fixtures (client, autouse mock_db)
├── fixtures/                         # SQL schema fixtures for drift & migration tests
│   ├── current_production_drift_schema.sql
│   └── pre_003_004_schema.sql
├── test_admin.py                     # Admin authentication, user mutations, self-protection
├── test_admin_audit.py               # Audit log filtering, pagination, safe_details parser
├── test_admin_phase3b.py             # Tenant company management and company audit trails
├── test_admin_phase5e.py             # UI semantic validation, table pagination, filter tests
├── test_ai_resume.py                 # OpenAI structured outputs, PII redaction, error codes
├── test_auth.py                      # Registration, login, logout, password hashing
├── test_candidate.py                 # Candidate dashboard and application workflows
├── test_candidate_phase2.py          # Saved jobs, profile fields, validation rules
├── test_candidate_profile.py         # Portfolio CRUD, URL validation, date validation
├── test_email_service.py             # Resend API integration and error handling
├── test_monitoring.py                # /healthz endpoint and error handlers (404, 500)
├── test_phase1a.py                   # User roles, company associations, audit logs
├── test_phase4a.py                   # DB integration: Recruiter ownership & isolation
├── test_phase4b.py                   # DB integration: Interview coordination & auto-cancellation
├── test_recruiter.py                 # Job posting, applicant ranking, status updates
├── test_recruiter_phase3a.py         # Advanced recruiter filters, ranking, bulk updates
├── test_recruiter_phase3b.py         # Recruiter settings and company profile inspection
├── test_resume_parser.py             # PDF text extraction, skill matching, TF-IDF scoring
├── test_routes.py                    # Public route availability and error handler checks
├── test_schema_contract.py           # MySQL live schema contract assertions
├── test_security.py                  # Security regression: RBAC, CSRF, rate limits, headers
└── test_services.py                  # Unit tests for domain services
```

---

## Test Commands

### 1. In-Memory Unit Test Suite (No Database Required)
```bash
pytest -v tests/ --ignore=tests/test_schema_contract.py --ignore=tests/test_phase4a.py --ignore=tests/test_phase4b.py
```

### 2. Live Database Integration Suite (Requires MySQL on localhost:3306)
```bash
# Run schema contract tests
pytest -v tests/test_schema_contract.py

# Run Phase 4A & 4B integration tests
pytest -v tests/test_phase4a.py
pytest -v tests/test_phase4b.py
```

### 3. Code Quality & Syntax Checks
```bash
# Ruff linter check
ruff check .

# Black formatting verification
black --check .

# Syntax bytecode validation
python -m compileall -q app.py core.py config.py routes/ services/ models/
```

---

## Unit Tests

Unit tests constitute the majority of test files (21 out of 24 test files). They run in isolated in-memory Python processes without opening database connections. The global `mock_db` fixture in `conftest.py` automatically intercepts all `get_db_connection` calls and supplies mock database connections and cursors.

---

## Integration Tests

Integration tests (`test_phase4a.py`, `test_phase4b.py`, `test_schema_contract.py`) bypass the autouse `mock_db` fixture. They establish live connections to MySQL via PyMySQL to execute real DDL/DML transactions:
- `test_phase4a.py`: Verifies recruiter data isolation (Recruiter A cannot modify Recruiter B's jobs or applications).
- `test_phase4b.py`: Tests complete interview workflows, including concurrent state locking (`FOR UPDATE`) and automatic cancellation of future interviews when an application reaches `rejected`, `hired`, or `withdrawn`.
- `test_schema_contract.py`: Connects to `test_db` and verifies table definitions, foreign keys, and indexes against schema expectations.

---

## End-to-End Tests

**No browser-driven end-to-end (E2E) automation frameworks** (such as Selenium, Playwright, or Cypress) are implemented in the repository. Frontend testing is conducted via the Flask HTTP test client asserting rendered HTML fragments, status codes, and JSON responses.

---

## Fixtures

- `client` (`conftest.py`): Yields a configured Flask test client with `TESTING = True` and `WTF_CSRF_ENABLED = False`.
- `mock_db` (`conftest.py`): Autouse fixture that automatically patches `get_db_connection` across 12 module targets for all non-integration test modules.
- `pre_003_004_schema.sql` (`tests/fixtures/`): Fixture representing the database state prior to migrations 003 and 004, used by CI to test forward migration paths.
- `current_production_drift_schema.sql` (`tests/fixtures/`): Fixture capturing historical production schema drift, used to verify schema reconciliation migrations.

---

## Mocks

- **Database Mocks**: `MagicMock` instances returning configured row dictionaries (`fetchone()`, `fetchall()`) and simulating `cursor.rowcount`.
- **OpenAI API Mocks**: In `test_ai_resume.py`, `client.responses.parse` is mocked to simulate valid Structured Output payloads, `RateLimitError` (HTTP 429), and `APITimeoutError` (HTTP 503).
- **Email Delivery Mocks**: In `test_email_service.py` and `test_security.py`, `resend.Emails.send` is patched to verify outgoing message parameters without hitting external networks.

---

## Important Test Areas

### Authentication Tests (`test_auth.py`, `test_security.py`)
- User registration requires valid email and password length $\ge 8$.
- Public registration cannot register the `ADMIN_EMAIL`.
- Passwords are verified using `scrypt` hashes.
- Successful login clears previous session data to prevent fixation.
- Deactivated accounts cannot log in.
- Password reset token generation invalidates prior unused tokens.

### Authorization Tests (`test_admin.py`, `test_security.py`)
- Anonymous requests to `/admin/*` or `/recruiter/*` redirect to `/login`.
- Non-admin users attempting to access `/admin/*` are rejected with HTTP 302 and an error flash.
- Logged-in admin cannot demote their own role or deactivate their own account.
- Recruiters cannot view or edit jobs/applicants belonging to other recruiters.
- Candidate cannot query another candidate's score endpoint (`/api/candidate/<id>/score`).

### Database Tests (`test_schema_contract.py`, `test_phase4a.py`, `test_phase4b.py`)
- Validates 14 canonical tables exist in MySQL.
- Verifies foreign key constraints with `ON DELETE CASCADE` and `ON DELETE SET NULL`.
- Verifies composite indexes on `interviews` (`(application_id, scheduled_at)` and `(status, scheduled_at)`).
- Validates that `jobs.is_active` is non-nullable with default `1`.

### Candidate Workflow Tests (`test_candidate.py`, `test_candidate_phase2.py`, `test_candidate_profile.py`)
- PDF resume text extraction and skill keyword matching.
- Composite score calculation: $(0.70 \times \text{Skill}) + (0.30 \times \text{TF-IDF})$.
- Self-service application withdrawal transitions application to `withdrawn` and auto-cancels scheduled interviews.
- Profile completion percentage calculation.
- URL validation rejects non-HTTP(S) or malformed URLs.
- Date validation rejects end dates preceding start dates.

### Recruiter Workflow Tests (`test_recruiter.py`, `test_recruiter_phase3a.py`)
- Posting, editing, and closing jobs.
- Applicant list sorted strictly by descending match score.
- Single and bulk status updates (`shortlisted`, `rejected`, `hired`).
- Excel export constructs `.xlsx` with valid headers and data formatting via `openpyxl`.
- Interview scheduling validates future dates, allowed duration (5–480 min), and valid URLs for online mode.

### Admin Workflow Tests (`test_admin.py`, `test_admin_audit.py`, `test_admin_phase3b.py`)
- Operational metrics computation across users, jobs, applications, interviews, and companies.
- Server-side user table pagination and multi-field filtering.
- Company creation, editing, and active status toggling.
- Company assignment guard: only recruiters can be assigned to companies.
- Audit log query filtering (by action, actor, target type, date range) and safe detail parsing.

---

## Edge Cases

- **Zero Division Safety**: Zero applications or zero required skills handle calculations gracefully without raising `ZeroDivisionError` (e.g., candidate scoring returns `0.0%`).
- **Inverted Date Ranges**: Supplying a `date_from` that occurs after `date_to` in audit logs returns an empty result set and emits a warning flash rather than crashing.
- **Concurrent Status Updates**: Status updates verify previous state with `WHERE id=%s AND status=%s`; if modified concurrently, rowcount is zero and a warning is flashed.
- **Empty Resume Content**: Handled gracefully by `ai_resume_service.py` with an explicit error response rather than sending empty strings to OpenAI.

---

## Error Scenarios

- **Database Disconnection**: The `/healthz` route returns HTTP 503 `{"status": "error", "database": "unreachable"}` when connection fails.
- **404 Handling**: Unmatched routes trigger `templates/errors/404.html`.
- **500 Handling**: Unhandled exceptions render `templates/errors/500.html` and log stack traces.
- **AI Rate Limits**: Catches `openai.RateLimitError` and translates it into HTTP 429 JSON response.

---

## Coverage

*Code coverage tools (e.g. `pytest-cov`) are not configured in `pyproject.toml` or `requirements-dev.txt`. Exact percentage coverage is therefore not established from repository evidence.*

---

## Latest Verified Test Evidence

- **Latest verified release test result**: **267 passed, 1 skipped** in 9.25 seconds (documented in repository release verification).
- **Audit Execution Status**: Tests were not executed during this documentation-only audit.
- **CI Pipeline Configuration**: `.github/workflows/ci.yml` actively enforces unit tests, schema contract tests, DB integration tests, and migration tests against a live `mysql:8.4` service container.

---

## Testing Gaps

1. **Missing DDL Tests for Auxiliary Tables**: No test verifies schema contracts for `notifications` or `password_resets`, as they are not defined in `database/schema.sql`.
2. **Absence of Browser E2E Tests**: No Selenium or Playwright tests exist to verify JavaScript behaviors (such as the instant dark mode toggle or dynamic filter bar) in real browser engines.
3. **Absence of Automated Load / Stress Tests**: No automated load testing scripts (e.g. Locust, k6) exist in the repository.

---

## Safe Verification Procedure

To safely verify the repository without modifying state:
1. Run static linting: `ruff check .`
2. Run code format validation: `black --check .`
3. Run static bytecode compilation: `python -m compileall -q app.py core.py config.py routes/ services/ models/`
4. Run the in-memory test suite:
   ```bash
   pytest -v tests/ --ignore=tests/test_schema_contract.py --ignore=tests/test_phase4a.py --ignore=tests/test_phase4b.py
   ```
*(Note: Do not execute `test_schema_contract.py`, `test_phase4a.py`, or `test_phase4b.py` against production databases; they require an isolated test database with drop/create permissions).*
