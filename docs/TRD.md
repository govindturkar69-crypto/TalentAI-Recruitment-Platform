# Technical Requirements Document

## Documentation Basis

- Repository branch: `main`
- Repository HEAD: `891d7ac4947d7a4153d2da7389aabdaf116e3b52`
- Release snapshot: `v1.0.0`
- Analysis method: Static repository inspection
- Runtime verification: Present but not runtime-verified (documentation-only analysis)
- Generated/updated: `2026-09-11`

---

## Technical Overview

**TalentAI** is a modular web application written in Python using Flask 2.3 and MySQL 8.4. The backend is structured into decoupled Flask Blueprints (`auth`, `candidate`, `recruiter`, `admin`, `analytics`) and a distinct Service layer for business logic, data persistence, and auditing. Database access relies on raw parameterized SQL using PyMySQL and DBUtils connection pooling (`PooledDB`), avoiding ORM overhead while preventing SQL injection. Machine learning algorithms for TF-IDF vectorization and cosine similarity are executed locally via `scikit-learn`. The frontend utilizes server-rendered Jinja2 templates styled with Bootstrap 5.3, Bootstrap Icons, Plotly 2.27 for interactive analytics, and custom CSS variables supporting a fluid dark theme.

---

## Technology Stack

| Layer / Component | Technology | Version | Purpose |
|---|---|---|---|
| **Programming Language** | Python | 3.11 / 3.13 | Primary server-side application logic |
| **Web Framework** | Flask | 2.3.3 | Routing, Blueprints, request handling, Jinja2 templating |
| **WSGI Server** | Gunicorn | 21.2.0 | Production HTTP server |
| **Database** | MySQL | 8.4 / 8.0+ | Relational storage for platform entities |
| **DB Driver & Pooling** | PyMySQL, DBUtils | 1.1.0, 3.1.0 | Pure Python MySQL client with pooled connection reuse |
| **Security & Auth** | Werkzeug, Flask-WTF, Flask-Limiter | 2.3.7, 1.2.1, 3.8.0 | `scrypt` password hashing, CSRF protection, rate limiting |
| **Document Processing** | pypdf | 5.1.0 | Extraction of raw text from uploaded PDF resumes |
| **Text Similarity & ML** | scikit-learn | 1.6.1 | `TfidfVectorizer` and `cosine_similarity` candidate match scoring |
| **Data Analysis** | pandas | 2.2.3 | Aggregation of recruiter analytics metrics |
| **Visualization** | Plotly (Python + JS) | 5.17.0 (Py), 2.27.0 (JS) | Generation and native browser rendering of analytical charts |
| **Spreadsheet Generation** | openpyxl | 3.1.2 | Formatted `.xlsx` applicant roster generation |
| **Error Monitoring** | sentry-sdk[flask] | 2.68.0 | Exception capturing and performance telemetry |
| **Transactional Email** | resend | 2.2.0 | API-driven password recovery email delivery |
| **Advisory AI** | openai | $\ge 1.0.0$ | Optional Structured Outputs for resume advice |
| **Styling & Icons** | Bootstrap, Bootstrap Icons | 5.3.0, 1.11.0 | Responsive layout, UI components, iconography |
| **Code Quality & Linting** | Ruff, Black, Pytest | 0.6.5, 24.8.0, 8.3.3 | Linting, formatting verification, test suite execution |

---

## Languages

- **Python**: Primary language for backend logic, routing, services, data parsing, machine learning, and tests (configured for `py311` target in `pyproject.toml`, compatible with Python 3.11–3.13).
- **SQL**: DDL schemas, migration scripts, and parameterized SQL queries for MySQL 8.4.
- **HTML5 (Jinja2)**: Server-side template markup with blocks, macros, filters, and context processors.
- **CSS3**: Custom stylesheets (`static/css/style.css`, `auth.css`, `landing.css`) leveraging custom variables, CSS Grid, and Flexbox.
- **JavaScript (ES6+)**: Client-side interactivity (`static/js/main.js`, `auth.js`) for theme toggling, instant alerts, dynamic filtering, and score animations.

---

## Runtime

- **Runtime Specification**: `python-3.11.9` declared in `runtime.txt` (used by platform-as-a-service hosts like Render).
- **Execution Mode**: Multi-threaded or multi-worker WSGI process managed by Gunicorn (`gunicorn app:app`).

---

## Frameworks and Libraries

### Backend Framework
- **Flask (2.3.3)**: Application core utilizing modular blueprints registered in `app.py`:
  - `auth_blueprint` (`routes/auth.py`): Registration, login, logout, password recovery, settings.
  - `candidate_bp` (`routes/candidate.py`): Candidate portal, profiles, resumes, job applications, saved jobs.
  - `recruiter_bp` (`routes/recruiter.py`): Job management, candidate evaluation, interview coordination, exports.
  - `admin_bp` (`routes/admin.py`): Operational dashboards, user role mutations, tenant company management, audit logs.
  - `analytics_bp` (`routes/analytics.py`): Recruitment metrics and charts.

### Supporting Libraries
- **Werkzeug (2.3.7)**: Cryptographic password hashing (`generate_password_hash`, `check_password_hash`), filename sanitization (`secure_filename`).
- **Flask-WTF (1.2.1)**: Universal CSRF protection via `CSRFProtect(app)`.
- **Flask-Limiter (3.8.0)**: Endpoint rate limiting using client IP address (`get_remote_address`).
- **pypdf (5.1.0)**: Reading and extracting plain text from PDF resume uploads.
- **scikit-learn (1.6.1)**: TF-IDF vectorization with English stop words and cosine similarity computation.
- **openpyxl (3.1.2)**: Creation of multi-column styled `.xlsx` spreadsheets with custom header backgrounds and font fills.
- **resend (2.2.0)**: REST API client for transactional email delivery.
- **openai ($\ge 1.0.0$)**: Client for OpenAI API leveraging Pydantic schemas (`AIResumeSuggestions`) with Structured Outputs.

---

## Frontend

- **CSS Architecture**: Custom CSS architecture with CSS Custom Properties defined in `:root` and `[data-theme="dark"]` in `static/css/style.css`.
- **Responsive Viewport Support**: Verified zero horizontal overflow from 390px mobile viewports up to 1536px desktop viewports.
- **Iconography**: Bootstrap Icons 1.11.0 loaded via CDN.
- **Interactive Visualizations**: Plotly.js 2.27.0 loaded via CDN to render JSON-serialized figures generated by Plotly Python.
- **Client Scripting**: Vanilla JavaScript (`static/js/main.js`, `static/js/auth.js`) without heavyweight frontend frameworks; handles theme persistence in `localStorage`, auto-dismissing flash alerts, input lowercasing, and table filter DOM updates.

---

## Backend

- **Application Factory & Initialization**: Configured in `app.py`. Initializes logging, Sentry monitoring, upload folder directory creation, CSRF protection, and rate limiting before registering blueprints.
- **Architecture Style**: Layered architecture separating Routing/HTTP handlers (`routes/`), Business Logic (`services/`), Local ML & Parsing (`models/`), and Configuration/Persistence (`core.py`, `config.py`).
- **Circular Import Prevention**: Shared database pool `DB_POOL` and decorators (`@login_required`, `@admin_required`) reside in `core.py`, allowing blueprints and `app.py` to import them independently.

---

## Database

- **Engine**: MySQL 8.4 (or 8.0+ compatible).
- **Connection Management**: DBUtils `PooledDB` configured in `core.py`:
  - `maxconnections`: 10
  - `mincached`: 0 (during tests) or `DB_MIN_CACHED` (default: 2)
  - `maxcached`: 5
  - `blocking`: True
  - `ping`: 1 (checks connection validity before reuse)
  - `cursorclass`: `pymysql.cursors.DictCursor` (returns results as dictionaries)
- **SSL Support**: Automatically enabled when `MYSQL_SSL=True` (required for cloud-managed providers like Aiven).
- **Transaction Handling**: Explicit `conn.commit()` and `conn.rollback()` blocks. Cursors and connections wrapped in `contextlib.closing`.

---

## Authentication

- **Mechanism**: Server-side session authentication using signed client cookies (`session["user_id"]`, `session["role"]`, `session["is_admin"]`).
- **Password Hashing**: Implemented via Werkzeug `generate_password_hash(password)` utilizing `scrypt` key derivation with random salts.
- **Session Lifetime**: Permanent session lifetime configured to 8 hours (`timedelta(hours=8)`).
- **Session Hardening**:
  - `SESSION_COOKIE_HTTPONLY = True`: Blocks JavaScript access to session cookies.
  - `SESSION_COOKIE_SAMESITE = "Lax"`: Prevents CSRF on cross-site requests while permitting top-level navigation.
  - `SESSION_COOKIE_SECURE`: Enabled automatically when `FLASK_DEBUG != "True"`.
  - Session clearing on login, logout, and password change to prevent session fixation.
- **Password Recovery**: Time-limited (1-hour) URL-safe tokens generated with `secrets.token_urlsafe(32)`. Previous unused tokens for the user are invalidated upon new requests.

---

## Authorization

- **RBAC Decorators**:
  - `@login_required(role=None)`: Validates active session and confirms account active state (`is_active = TRUE`). If a role is specified, rejects mismatched roles with HTTP 302 and an "Access denied" flash.
  - `@admin_required`: Validates active session, active status, and verifies that the logged-in user's email matches `Config.ADMIN_EMAIL` (case-insensitive).
- **Object-Level Access Control (Ownership Checks)**:
  - Candidates may only view their own score endpoint (`/api/candidate/<id>/score`) and their own profile/applications.
  - Recruiters may only view, edit, delete, export, or schedule interviews for jobs where `job.recruiter_id == session["user_id"]`.
  - Applications and resumes can only be inspected by recruiters who own the requisition associated with the application.
- **Admin Self-Protection**:
  - Administrators cannot change their own role (`/admin/users/<id>/role`).
  - Administrators cannot deactivate their own account or the primary account matching `ADMIN_EMAIL` (`/admin/users/<id>/status`).

---

## Routes / APIs

- **Server-Rendered Routes**: 35+ Jinja2 HTML endpoints across authentication, candidate portal, recruiter management, administrative console, notifications, and analytics.
- **JSON REST Endpoints**:
  - `GET /healthz`: Health monitoring returning status and database connectivity.
  - `GET /api/jobs`: List of active jobs (`is_active = TRUE`) for authenticated users.
  - `GET /api/candidate/<int:user_id>/score`: Candidate match scores with ownership enforcement.
  - `POST /api/resume/score_local`: Deterministic local candidate match scoring without third-party API calls.
  - `POST /api/resume/analyze`: Advisory resume enhancement recommendations via OpenAI Structured Outputs.

---

## External Services

- **OpenAI API**: Used optionally for advisory resume feedback (`services/ai_resume_service.py`). Activated only if `OPENAI_API_KEY` is present. Uses model defined in `OPENAI_MODEL` (default: `gpt-5.6-luna`).
- **Resend API**: Used for sending password recovery transactional emails (`services/email_service.py`). Activated only if `RESEND_API_KEY` and `MAIL_FROM` are set.
- **Sentry SDK**: Optional error tracking and crash reporting initialized if `SENTRY_DSN` is populated. Configured with `send_default_pii=False`.
- **Aiven / Cloud MySQL**: Managed relational database hosting providing SSL-encrypted database connections.

---

## Configuration

Configuration is managed via class `Config` in `config.py` using `python-dotenv`:
- Mandatory validation: If `FLASK_SECRET_KEY` is missing or empty, `Config` raises a `RuntimeError` on startup to prevent insecure deployment.
- Fallback defaults for local development: Localhost MySQL parameters, 8-hour session lifetimes, default model settings.

---

## Environment Variables

| Variable Name | Purpose | Required? | Safe Example |
|---|---|---|---|
| `FLASK_SECRET_KEY` | Secret key for signing session cookies and CSRF tokens | **Required** | `<random-hex-string>` |
| `FLASK_DEBUG` | Enables Flask debug mode (disables Secure cookie flag if True) | Optional (Default: `False`) | `False` |
| `MYSQL_HOST` | Hostname or IP address of the MySQL database server | Optional (Default: `localhost`) | `localhost` |
| `MYSQL_PORT` | Port number of the MySQL server | Optional (Default: `3306`) | `3306` |
| `MYSQL_USER` | MySQL database username | Optional (Default: `root`) | `root` |
| `MYSQL_PASSWORD` | Password for the MySQL user | Optional (Default: `""`) | `<database-password>` |
| `MYSQL_DB` | Database schema name | Optional (Default: `recruitment_db`) | `recruitment_db` |
| `MYSQL_SSL` | Enable SSL encryption for cloud database connections | Optional (Default: `False`) | `True` |
| `ADMIN_EMAIL` | Email address designated as the platform Super-Admin | Optional (Default in code) | `admin@example.com` |
| `APP_ENV` | Application environment identifier (`development`, `production`) | Optional (Default: `development`) | `production` |
| `APP_BASE_URL` | Base URL used to construct absolute password reset links | Optional in dev, required in prod | `https://app.example.com` |
| `RESEND_API_KEY` | API key for Resend email delivery service | Optional | `<resend-api-key>` |
| `MAIL_FROM` | Sender email address for outgoing system emails | Optional | `noreply@example.com` |
| `SENTRY_DSN` | Sentry monitoring DSN for error telemetry | Optional | `https://<key>@o0.ingest.sentry.io/<id>` |
| `OPENAI_API_KEY` | OpenAI API key for optional advisory resume analysis | Optional | `<openai-api-key>` |
| `OPENAI_MODEL` | OpenAI model name for structured resume suggestions | Optional (Default: `gpt-5.6-luna`) | `gpt-5.6-luna` |
| `TESTING` | Testing flag disabling real connection pool initialization | Optional (Default: `False`) | `True` |
| `DB_MIN_CACHED` | Minimum number of cached idle connections in PooledDB | Optional (Default: `2`) | `2` |

---

## Security Implementation

1. **Authentication & Password Storage**: Passwords hashed with `scrypt` through Werkzeug `generate_password_hash`. Account enumeration avoided on registration and password reset.
2. **Access Control**: Role enforcement on routes via `@login_required(role)` and `@admin_required`. Strict record-level ownership checks preventing cross-tenant and cross-recruiter access.
3. **CSRF Protection**: Universal token validation on all POST endpoints via Flask-WTF.
4. **Rate Limiting**: Throttling on sensitive endpoints (`/login`, `/register`, `/forgot_password`, `/api/resume/analyze`) via Flask-Limiter.
5. **SQL Injection Defense**: 100% parameterized SQL queries with `pymysql` and DBUtils. No raw string interpolation in SQL statements.
6. **Path Traversal & Safe Redirects**: File uploads sanitized via `secure_filename`. Resume download verifies that canonical path resides within `UPLOAD_FOLDER`. URL redirects validated via `is_safe_redirect_url` to prevent open redirects.
7. **Security Headers**: Injected on every response via `@app.after_request`:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: SAMEORIGIN`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
8. **PII Protection**: Regex-based redaction of emails and phone numbers before dispatching resume text to third-party AI APIs.

---

## Validation

- **File Uploads**: Only `.pdf` files allowed (`allowed_file`), validated on extension and MIME type.
- **Profile URLs**: Strict validation of LinkedIn, GitHub, and Portfolio URLs requiring valid `http://` or `https://` schemes and non-empty hosts.
- **Date Constraints**: Verification that educational and employment start dates precede or equal end dates (`start_date <= end_date`).
- **Interview Fields**: Validation that duration is an integer between 5 and 480 minutes, mode belongs to `{'online', 'in_person', 'phone'}`, online mode includes a valid HTTP/HTTPS URL $\le 500$ chars, and notes are $\le 2000$ chars.
- **Audit Details**: Sanitization of audit payloads using a strict allowlist (`AUDIT_ALLOWLIST`). Values truncated to a maximum of 100 characters to prevent log injection.

---

## Error Handling

- **HTTP 404 & 500 Pages**: Custom error templates (`templates/errors/404.html`, `templates/errors/500.html`) rendered without leaking internal stack traces.
- **Database Exceptions**: Handled gracefully using try/except blocks around transactional operations, logging errors with Python's `logging` module and returning user-friendly flash messages.
- **AI Service Degradation**: Handled via structured error dictionaries with specific HTTP status codes (e.g., 429 for provider rate limits, 503 for timeouts or missing keys).

---

## Logging

- **Configuration**: Implemented in `logging_config.py` using `logging.config.dictConfig`.
- **Request Context Filter**: Custom filter (`RequestContextFilter`) that automatically injects HTTP method, path, and authenticated user ID into log records:
  `[YYYY-MM-DD HH:MM:SS] INFO in <module> [METHOD /path | User: <id>]: <message>`
- **Audit Logging**: Structured events written to the `audit_logs` database table via `services/audit_service.py`.

---

## Performance-Related Implementation

- **Database Connection Pooling**: DBUtils `PooledDB` eliminates connection setup latency on repeated requests.
- **Server-Side Pagination**: Admin user management, company management, and audit log tables utilize database `LIMIT` and `OFFSET` to maintain constant memory consumption.
- **Database Indexes**: Strategic indexes on foreign keys (`users.company_id`, `audit_logs.actor_user_id`, `candidate_*.user_id`) and composite indexes (`idx_interviews_application_scheduled`, `idx_interviews_status_scheduled`).
- **In-Memory Score Computation**: Resume parsing, skill extraction, and TF-IDF calculation run in-memory without external sub-processes.
- **Context Processor Caching**: `inject_unread_count` caches unread notification count on Flask's request-scoped `g` object to prevent redundant database queries within the same request.

---

## Build / Runtime Process

1. **Local Setup**:
   - Create Python 3.11+ virtual environment (`python -m venv venv`).
   - Install dependencies: `pip install -r requirements.txt` and `pip install -r requirements-dev.txt`.
   - Initialize MySQL schema: `mysql -u root -p recruitment_db < database/schema.sql`.
   - Run development server: `python app.py`.
2. **Syntax Compilation Check**:
   - `python -m compileall -q app.py core.py config.py routes/ services/ models/`.

---

## Deployment

- **Hosting Platform**: Designed for cloud container and PaaS deployment (e.g., Render Web Service).
- **WSGI Server**: Gunicorn HTTP Server configured via `gunicorn app:app`.
- **Database Hosting**: Managed MySQL 8.4 (e.g., Aiven Cloud MySQL) requiring SSL encryption (`MYSQL_SSL=True`).
- **File Storage**: Uploaded PDF files are stored in `uploads/` on the local file system. (Persistent volume recommended in production).
- **Health Check**: Cloud uptime probes query `/healthz` to confirm operational readiness.

---

## CI/CD

- **Automation Engine**: GitHub Actions (`.github/workflows/ci.yml`).
- **Triggers**: Pushes and pull requests across all branches.
- **Pipeline Jobs**:
  1. Service container: Spin up `mysql:8.4` with health checks.
  2. Dependency installation: Python 3.11 with cached pip dependencies.
  3. Ruff check: Code quality and import order linting.
  4. Black check: Code formatting enforcement.
  5. Compileall check: Static bytecode compilation validation.
  6. Pytest Unit Tests: In-memory test suite with mocked database connections.
  7. Schema Contract Tests: Verification of canonical DDL against live MySQL.
  8. DB Integration Tests (Phase 4A & 4B): Database integration tests on live MySQL.
  9. Migration Reconciliation Tests: Testing forward migrations and backfill against schema fixtures.

---

## Technical Constraints

1. **Single-Instance In-Memory Limiter**: Flask-Limiter uses in-memory storage; horizontal scaling across multiple instances requires configuring a shared Redis storage URI.
2. **Filesystem Upload Storage**: Resume PDFs are written to local disk (`uploads/`); multi-instance deployments require shared storage or cloud object storage (e.g., S3/GCS).
3. **Database Client Library**: Uses PyMySQL (pure Python); does not require native MySQL C client compilation.

---

## Known Technical Limitations

1. **Schema DDL Discrepancy**: While the code in `app.py`, `services/notification_service.py`, and `routes/auth.py` actively reads and writes to `notifications` and `password_resets` tables, DDL definitions for these two tables are missing from `database/schema.sql` and the `database/migrations/` directory.
2. **Stateless Cookie Session Invalidation**: Because sessions are stored in client-side signed cookies, server-side session revocation on password reset only clears the requesting browser's cookie; existing cookies on other browsers remain cryptographically valid until expiration.
3. **Synchronous Upload Latency**: PDF parsing and text vectorization occur synchronously during HTTP POST handling, which can introduce latency on larger documents.
4. **Legacy Setup Documentation**: `SETUP_GUIDE.md` contains superseded setup instructions and deprecated library references; `README.md` and repository configuration files are the authoritative operational sources.
