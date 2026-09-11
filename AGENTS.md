# AI Agent Instructions

## Project Overview

**TalentAI** is an AI-assisted recruitment and applicant tracking platform built with Flask, MySQL, scikit-learn, and Bootstrap. It automates candidate resume intake, skill extraction, objective applicant ranking, coordinated interview scheduling with automatic state handling, recruiter pipeline workflows, and administrative governance.

Future AI coding agents working on this codebase must adhere strictly to the established patterns, constraints, and architecture documented herein.

---

## Documentation Snapshot

- Repository branch: `main`
- Repository HEAD: `891d7ac4947d7a4153d2da7389aabdaf116e3b52`
- Release snapshot: `v1.0.0`
- Current Date: `2026-09-11`
- Documentation suite: `docs/PRD.md`, `docs/TRD.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/API.md`, `docs/UI-UX.md`, `docs/TESTING.md`

---

## Architecture Summary

- **Pattern**: Modular layered monolith.
- **Layers**:
  - Routing: Flask Blueprints in `routes/` (`auth`, `candidate`, `recruiter`, `admin`, `analytics`).
  - Business Services: Pure Python services in `services/` (`candidate_service`, `recruiter_service`, `interview_service`, `audit_service`, etc.).
  - Parsing & ML: Stateless utilities in `models/resume_parser.py` using `pypdf` and `scikit-learn`.
  - Persistence: Raw parameterized SQL with DictCursor using `DBUtils.PooledDB` defined in `core.py`.
- **Decoupling Rule**: `core.py` houses shared database connection helpers and RBAC decorators (`@login_required`, `@admin_required`) to prevent circular imports between `app.py` and blueprints.

---

## Important Directories

- `routes/`: Flask blueprints handling HTTP request dispatching, input gathering, and rendering.
- `services/`: Core business logic, validation, audit dispatching, and notification triggers.
- `models/`: Parsing and machine learning logic (`resume_parser.py`).
- `database/`: Canonical DDL (`schema.sql`) and forward migration scripts (`migrations/001` through `009`).
- `templates/`: Jinja2 HTML templates organized by role and feature.
- `static/`: CSS styling tokens (`css/style.css`, `auth.css`, `landing.css`), JavaScript (`js/main.js`, `auth.js`), and favicon assets.
- `tests/`: Automated unit, integration, security, and schema contract tests.
- `uploads/`: Runtime directory storing uploaded candidate PDF resumes.

---

## Important Files

- `app.py`: Application factory, middleware (CSRF, limiter, security headers), error handlers, public endpoints, and health check (`/healthz`).
- `core.py`: Database connection pool `DB_POOL`, `get_db_connection()`, `@login_required`, and `@admin_required`.
- `config.py`: Environment configuration loading; enforces presence of `FLASK_SECRET_KEY`.
- `logging_config.py`: Structured logging configuration and `RequestContextFilter`.
- `models/resume_parser.py`: Skill database `SKILLS_DB`, PDF extraction, and scoring algorithms.
- `services/workflow.py`: Centralized state machine defining allowable status transitions.
- `services/interview_service.py`: Interview scheduling, updating, completing, and auto-cancellation logic.
- `services/audit_service.py`: Whitelist-sanitized audit log writer (`log_audit_event`).

---

## Coding Patterns

1. **Database Access Pattern**:
   Always use `contextlib.closing` when obtaining connections and cursors:
   ```python
   from contextlib import closing
   from core import get_db_connection

   with closing(get_db_connection()) as conn:
       with closing(conn.cursor()) as cur:
           cur.execute("SELECT * FROM table WHERE id = %s", (record_id,))
           record = cur.fetchone()
   ```
2. **Lean Route Handlers**:
   Keep routes focused on input parsing, calling services, flashing messages, and redirecting or rendering:
   ```python
   @recruiter_bp.route("/recruiter/job/<int:job_id>/delete", methods=["POST"])
   @login_required(role="recruiter")
   def delete_job(job_id):
       result = delete_job_service(session["user_id"], job_id)
       flash(result["message"], result["type"])
       return redirect(url_for("recruiter.recruiter_dashboard"))
   ```
3. **Safe Redirections**:
   Use `safe_redirect()` or whitelisted parameter builders (`_safe_redirect_dashboard()`) to preserve query/filter state without open redirect vulnerabilities.

---

## Coding Conventions

- **Formatting**: Adhere to `black` (120 character line length, Python 3.11 target).
- **Linting**: Pass `ruff check .` with zero errors. Configured rules: `E`, `W`, `F`, `I` (isort), `B` (flake8-bugbear). Exception: `E402` ignored for intentional late imports.
- **Typing & Strings**: Explicit SQL parameter binding (never use string formatting or f-strings to compose SQL queries).

---

## Authentication Rules

- All passwords must be hashed using `werkzeug.security.generate_password_hash` (uses `scrypt`).
- Registration must reject passwords under 8 characters.
- Session fixation must be prevented by calling `session.clear()` on login, logout, and password change.
- Never reveal whether an email exists during registration or password recovery (prevent account enumeration).

---

## Authorization Rules

- Protect every private route with `@login_required(role)` or `@admin_required`.
- Check ownership on every entity mutation:
  - Candidates: verify `candidate_id == session["user_id"]`.
  - Recruiters: verify `job.recruiter_id == session["user_id"]`.
- Enforce admin self-protection:
  - An admin cannot demote their own role.
  - An admin cannot deactivate their own account or the primary account matching `ADMIN_EMAIL`.

---

## Database Rules

- **100% Parameterized SQL**: Every query parameter must be passed as a tuple to `cur.execute(query, params)`.
- **Atomic Concurrency Checks**: Include current state in update conditions for stateful resources:
  `UPDATE applications SET status=%s WHERE id=%s AND status=%s`
- **Connection Return**: Never leave connections or cursors unclosed; always wrap with `closing()`.
- **Avoid ORMs**: Do not introduce SQLAlchemy or other ORMs; the platform relies on pure SQL via PyMySQL and `DBUtils`.

---

## API / Route Rules

- CSRF validation is universal on all POST routes. Any new POST endpoint must accept and validate a CSRF token.
- Apply rate limiting to all public authentication and expensive computation endpoints using `limiter.limit()`.
- Return proper HTTP status codes (e.g., 400 for bad inputs, 403 for unauthorized access, 404 for missing resources, 429 for rate limits, 503 for unavailable dependencies).

---

## UI Rules

- **Token Compliance**: Use CSS variables defined in `:root` and `[data-theme="dark"]` in `static/css/style.css`.
- **Zero Horizontal Overflow**: Ensure every new page or component maintains strictly $0\text{px}$ page-level overflow across viewports from 390px to 1536px. Wrap tables in `.table-responsive`.
- **Flash Alerts**: Use standard SaaS alert classes (`saas-alert-success`, `saas-alert-danger`, `saas-alert-warning`, `saas-alert-info`).
- **Unified Action Buttons**: In data tables, use a single dropdown button for row actions rather than cluttering rows with multiple inline buttons.

---

## Dependency Rules

- Do not introduce new dependencies without justification.
- When adding libraries, update both `requirements.txt` (or `requirements-dev.txt`) with exact pinned versions.
- Do not swap `pypdf` with outdated libraries (such as `PyPDF2`).

---

## Migration Rules

- All database schema modifications must be recorded as versioned, additive SQL migration scripts in `database/migrations/` (e.g., `010_...sql`).
- Synchronize canonical `database/schema.sql` with any new tables, columns, or indexes.
- Test migrations against baseline and drift fixtures using the pattern in `tests/test_schema_contract.py`.

---

## Testing Rules

- Every new feature, bug fix, or security control must have corresponding tests in `tests/`.
- Non-database tests must mock `get_db_connection` to run rapidly in memory.
- Integration tests requiring real MySQL must be isolated to test files that can be run independently in CI (`test_phase4a.py`, `test_phase4b.py`).
- Run `ruff check .` and `black --check .` before concluding any development task.

---

## Security Rules

- **PII Redaction**: Any text dispatched to external AI APIs must undergo sanitization via `sanitize_text()` in `services/ai_resume_service.py`.
- **Path Traversal Defense**: Always resolve paths and verify `is_relative_to(UPLOAD_FOLDER)` when streaming or reading uploaded files.
- **Audit Allowlist**: Any new details added to audit logging must be registered in `AUDIT_ALLOWLIST` in `services/audit_service.py` and `VIEWER_SAFE_DETAILS_ALLOWLIST` in `routes/admin.py`.

---

## External Service Rules

- Third-party API integrations (Resend, OpenAI) must be optional and non-blocking. If API keys are absent, the application must operate smoothly with user-friendly fallback notices.
- External API calls must configure explicit timeouts ($\le 30$ seconds).

---

## Environment Configuration Rules

- Access environment variables exclusively through `config.py` using `Config.<VARIABLE>`.
- Never commit secrets or credentials to source control. Use placeholders in `.env.example`.

---

## Sensitive Areas

1. `core.py`: Database connection pool and RBAC decorators.
2. `routes/auth.py`: Password hashing, token generation, session lifecycle.
3. `services/interview_service.py` & `services/recruiter_service.py`: Auto-cancellation of scheduled interviews upon application terminal state.
4. `routes/admin.py`: Self-protection checks preventing admin lockout.

---

## Areas That Should Not Be Changed Casually

- **Candidate Scoring Algorithm (`models/resume_parser.py`)**: The $(0.70 \times \text{Skill}) + (0.30 \times \text{TF-IDF})$ scoring formula is a core domain rule.
- **Application State Machine (`services/workflow.py`)**: Transition rules (`RECRUITER_TRANSITIONS`, `CANDIDATE_TRANSITIONS`) protect pipeline integrity.
- **Audit Log Schema & Sanitizer**: Must remain append-only and strictly sanitized to ensure regulatory compliance.

---

## Required Verification Before Changes

1. Run code linting: `ruff check .`
2. Run format check: `black --check .`
3. Run syntax compilation: `python -m compileall -q app.py core.py config.py routes/ services/ models/`
4. Run unit test suite:
   ```bash
   pytest -v tests/ --ignore=tests/test_schema_contract.py --ignore=tests/test_phase4a.py --ignore=tests/test_phase4b.py
   ```

---

## Definition of Done

A change to this repository is complete only when:
1. Application code conforms to all architecture and coding conventions.
2. All unit and regression tests pass without warnings.
3. Code is formatted with Black and passes Ruff with zero errors.
4. All state-modifying POST endpoints have CSRF protection and appropriate ownership validation.
5. All relevant documentation in `docs/` is updated to reflect changes accurately.

---

## Project-Specific Warnings

> [!CAUTION]
> **Auxiliary Tables DDL Discrepancy**: Runtime code references `notifications` and `password_resets`, but DDL statements for these tables are omitted from `database/schema.sql` and `database/migrations/`. When provisioning fresh database environments, verify that these tables are explicitly created if notifications or password reset workflows are needed.

> [!IMPORTANT]
> **Advisory AI Independence**: The OpenAI integration is strictly advisory. Never couple core applicant scoring or candidate ranking to third-party AI APIs. Core scoring must remain 100% deterministic, local, and cost-free.
