<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=32&pause=1000&color=6366F1&center=true&vCenter=true&width=650&lines=%F0%9F%A4%96+TalentAI;AI-Assisted+Recruitment+Platform;Smart+Hiring+for+Modern+Teams" alt="TalentAI" />

<br/>

### An AI-assisted recruitment platform automating the hiring lifecycle — from resume parsing and candidate ranking to interview coordination and administrative governance.

<br/>

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.4-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-22c55e?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/govindturkar69-crypto/TalentAI-Recruitment-Platform/actions)

<br/>

**[🌐 Live Demo](https://talentai-recruitment-platform.onrender.com) · [✨ Features](#-features) · [🤖 Resume Analysis](#-resume-parsing--candidate-scoring) · [🏛️ Architecture](#%EF%B8%8F-architecture-overview) · [⚙️ Local Setup](#%EF%B8%8F-local-development-setup) · [🧪 Testing & CI](#-automated-testing--ci) · [📄 Changelog](CHANGELOG.md)**

</div>

---

## 🌐 Live Production Demo

> ### 🔗 **[https://talentai-recruitment-platform.onrender.com](https://talentai-recruitment-platform.onrender.com)**
>
> Experience the deployed application directly in your browser. Register as a **Candidate** to upload resumes and track applications, or explore **Recruiter / Admin** capabilities including candidate ranking, pipeline status transitions, interview management, and audit logs.
>
> *Note: Hosted on cloud infrastructure; initial cold-start after periods of inactivity may take ~30–50 seconds while the web service container initializes.*

---

## 📖 Project Overview

**TalentAI** is a recruitment management platform built to streamline the candidate intake, evaluation, and hiring workflow:
- **Resume Intake & Skill Extraction**: Parses uploaded PDF resumes using `pypdf` and extracts technical skills against a curated 50+ skill taxonomy.
- **Deterministic Candidate Ranking**: Calculates an objective match score for each applicant based on required skills coverage and TF-IDF text similarity against the job description.
- **Full Lifecycle Application Tracking**: Manages candidate submissions across structured stages (`applied`, `shortlisted`, `rejected`, `hired`, `withdrawn`).
- **Coordinated Interview Scheduling**: Allows recruiters to schedule, reschedule, and cancel interviews, with synchronized calendar views for candidates and automatic cancellation when applications reach terminal states.
- **Governance & Multi-Tenancy**: Centralizes user administration, company tenant assignments, and immutable append-only audit logging.

---

## ✨ Features

### 👤 Candidate Portal
- **PDF Resume Upload**: Client-validated upload with text extraction via `pypdf`.
- **Skill Extraction**: Automatic identification of technical skills from a 50+ keyword catalog.
- **Smart Application Flow**: Instant fit score computation and match percentage display upon application.
- **Job Discovery & Search**: Multi-filter job search across job titles, descriptions, required skills, and locations.
- **Application Tracking**: Dedicated dashboard to monitor application status in real time.
- **Self-Service Application Withdrawal**: Candidates can withdraw active applications prior to a terminal decision.
- **Saved Jobs**: Bookmark job postings to apply later.
- **Candidate Interview Hub**: View scheduled, completed, and cancelled interviews with logistics and meeting links.
- **Profile Management**: Maintain personal bio, experience, education, and portfolio/social links.
- **Optional AI Suggestions**: On-demand resume improvement suggestions when OpenAI is configured.

### 🏢 Recruiter Management
- **Job Requisition Lifecycle**: Create, edit, close, reopen, and delete listings associated with tenant companies.
- **Automatic Candidate Ranking**: Dynamic sorting of applicants by composite match score.
- **Batch Processing**: Bulk actions to shortlist, reject, or hire multiple applicants simultaneously.
- **Candidate Profiles**: View applicant details, contact information, extracted skills, and uploaded resumes.
- **Interview Scheduling**: Schedule, reschedule, update logistics (date, time, duration, mode), or cancel interviews.
- **Terminal State Auto-Cancellation**: Moving an application to `rejected`, `hired`, or `withdrawn` atomically cancels any future scheduled interviews.
- **Excel Data Export**: Download structured `.xlsx` applicant rosters using `openpyxl`.
- **Notification Alerts**: In-app alerts triggered on new candidate applications and withdrawals.

### 🛡️ Admin Console & Governance
- **Operational Metrics**: Platform-wide telemetry covering user totals, active listings, applications, interviews, and tenant companies.
- **User Management**: Server-side paginated user management table with role filters, status filters, and search.
- **Self-Protection Rules**: Enforced safeguards preventing the logged-in administrator from demoting their own role or deactivating their own account.
- **Company Access Controls**: Recruiter-to-company assignments with validation preventing company assignment to candidate accounts.
- **Tenant Management**: Interface to create, edit, activate, and deactivate client organizations.
- **Immutable Audit Trail**: Append-only audit table logging administrative, security, role, company, status, and interview events.
- **Semantic Audit Formatter**: Structured key-value event detail rendering with human-readable enum mapping and neutral system actor avatars.

### 📊 Recruitment Analytics
- **Interactive Plotly Charts**: Visual dashboards embedded natively:
  - Skill demand distribution across active listings.
  - Candidate match score distribution curves.
  - Application status conversion funnel.

---

## 🤖 Resume Parsing & Candidate Scoring

TalentAI clearly separates core deterministic local scoring from optional advisory AI services:

### 1. Local Deterministic Scoring (Core Engine)
The primary scoring and candidate ranking engine executes 100% locally and does not depend on third-party AI APIs:
- **PDF Text Extraction**: Uses `pypdf` to extract raw text content from uploaded PDF resumes.
- **Skill Extraction**: Matches resume text against a predefined database of 50+ technical skills (`models/resume_parser.py`).
- **Skill Score**: Measures the percentage of required skills satisfied by the candidate:
  $$\text{Skill Score} = \frac{|\text{Matched Skills}|}{|\text{Total Required Skills}|} \times 100$$
- **TF-IDF Text Similarity**: Uses scikit-learn's `TfidfVectorizer` (with English stop words) and `cosine_similarity` to measure textual alignment between the resume and the job description:
  $$\text{TF-IDF Score} = \cos(\mathbf{v}_{\text{resume}}, \mathbf{v}_{\text{job}}) \times 100$$
- **Composite Final Score**:
  $$\text{Final Score} = (\text{Skill Score} \times 0.70) + (\text{TF-IDF Score} \times 0.30)$$
  *(When no job description is provided, the Skill Score is used on its own.)*

### 2. Optional Advisory AI (OpenAI Structured Outputs)
- **Purpose**: Provides candidates with optional, advisory resume improvement recommendations (`services/ai_resume_service.py`).
- **Configuration**: Activated only when `OPENAI_API_KEY` is present in the application environment.
- **Advisory Only**: Does not calculate, alter, or override candidate match scores or recruiter rankings.
- **Privacy Safeguards**: PII (email addresses and phone numbers) is automatically redacted before text is transmitted to the advisory model.
- **Independent Operation**: If `OPENAI_API_KEY` is not provided, the core application, scoring engine, ranking, and application workflows remain fully operational.

---

## 🔒 Security & Quality Highlights

- **Role-Based Access Control (RBAC)**: Centralized route decorators (`@login_required`, `@recruiter_required`, `@admin_required`) strictly guard endpoint access.
- **CSRF Protection**: Universal CSRF token validation on all state-modifying POST requests via Flask-WTF.
- **Cryptographic Password Security**: Passwords hashed using Werkzeug `scrypt` key derivation with cryptographic salts.
- **Rate Limiting**: Brute-force protection on authentication routes (`/login`, `/register`, `/forgot-password`) using Flask-Limiter.
- **Administrative Safeguards**: Backend and UI checks prevent administrators from locking themselves out or changing their own administrative role.
- **SQL Injection Prevention**: All database queries utilize parameterized SQL query strings with DBUtils connection pooling.
- **Session Hardening**: Cookies configured with `HttpOnly` and `SameSite=Lax` flags.
- **Audit Immutability**: Dedicated append-only table recording actor, target, timestamp, and structured change payloads.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | Python 3.13, Flask 2.3 | Modular Blueprints, REST routes, web application logic |
| **Database & Pooling** | MySQL 8.4, PyMySQL, DBUtils `PooledDB` | Relational storage, connection pool management |
| **Data Processing & ML** | scikit-learn, `pypdf` | TF-IDF vectorization, cosine similarity, PDF extraction |
| **Analytics & Visualization** | Pandas, Plotly | Metric aggregation, interactive visualization charts |
| **Frontend Presentation** | Bootstrap 5.3, Bootstrap Icons, Vanilla JS | Responsive layouts, design tokens, client-side behavior |
| **Security & Auth** | Werkzeug Security, Flask-WTF, Flask-Limiter | scrypt password hashing, CSRF tokens, rate limiting |
| **Email Delivery** | Resend API | Transactional password recovery emails |
| **Export Engine** | openpyxl | Formatted Excel spreadsheet generation |
| **Production WSGI** | Gunicorn | Production WSGI HTTP server |
| **Hosting & Infrastructure**| Render, Aiven Cloud MySQL | Web service hosting, managed MySQL with SSL |
| **CI / Quality** | GitHub Actions, Pytest, Ruff, Black | Automated test execution, linting, formatting checks |

---

## 🏛️ Architecture Overview

TalentAI follows a decoupled architecture separating presentation, HTTP routing, business services, and database persistence:

```
TalentAI Platform
├── Presentation Layer
│   ├── templates/               # Jinja2 HTML5 templates (with custom CSS tokens)
│   └── static/                  # CSS stylesheets, client-side JavaScript, assets
│
├── Flask Route / Blueprint Layer
│   ├── routes/auth.py           # Authentication, registration, password recovery
│   ├── routes/candidate.py      # Candidate dashboard, profile, applications, jobs
│   ├── routes/recruiter.py      # Requisitions, applicant ranking, interviews
│   ├── routes/admin.py          # Admin console, user management, companies, audit logs
│   └── routes/analytics.py      # Analytics dashboards and chart endpoints
│
├── Service / Data-Access Layer
│   ├── services/candidate_service.py     # Application submission and withdrawal logic
│   ├── services/recruiter_service.py     # Applicant ranking, batch status transitions
│   ├── services/interview_service.py     # Interview scheduling and auto-cancellations
│   ├── services/audit_service.py         # Structured append-only audit trail logging
│   ├── services/ai_resume_service.py     # Optional OpenAI advisory suggestion service
│   ├── services/email_service.py         # Transactional email delivery via Resend
│   ├── services/notification_service.py  # User notification management
│   └── services/workflow.py              # Application status state machine validation
│
├── Model & Parsing Layer
│   └── models/resume_parser.py  # PDF text extraction, skill matching, TF-IDF scoring
│
├── Database & Configuration
│   ├── core.py                  # Database connection pool (DBUtils PooledDB)
│   ├── config.py                # Environment configuration loading
│   └── database/migrations/     # Versioned forward-only SQL migration scripts (001 - 009)
```

---

## 🗃️ Database Schema & Migrations

The relational schema is managed on MySQL 8.4 across 11 core tables:
- `users`: User accounts with role-based attributes (`candidate`, `recruiter`, `admin`).
- `jobs`: Requisitions with status flags, required skills, and company associations.
- `resumes`: Uploaded resume metadata, extracted text, and skill tags.
- `applications`: Candidate-to-job mappings with status and composite match scores.
- `candidate_profiles`: Candidate professional background, education, and links.
- `companies`: Multi-tenant organization records and active flags.
- `interviews`: Interview schedule records with status, timing, and meeting details.
- `audit_logs`: Immutable compliance logs recording platform state transitions.
- `saved_jobs`: Candidate bookmarked job listings.
- `notifications`: User notification alerts and read states.
- `password_resets`: Time-limited password reset tokens.

### Versioned Migration History (001–009)
1. `001_foundation.sql`: Core baseline tables (users, jobs, applications, resumes, notifications).
2. `002_candidate_profile.sql`: Extended candidate profile metadata and social links.
3. `003_reconcile_foundation.sql`: Schema reconciliation and column constraints.
4. `004_job_lifecycle.sql`: Company association and requisition status tracking.
5. `005_reconcile_candidate_profile.sql`: Safe profile schema normalization.
6. `006_reconcile_job_lifecycle.sql`: Requisition integrity constraints.
7. `007_add_saved_jobs.sql`: Persistent bookmarking queue for candidates.
8. `008_add_withdrawn_status.sql`: Self-service candidate application withdrawal state.
9. `009_add_interviews.sql`: Interview coordination, company multi-tenancy, and audit logs.

*Note: Migrations are tracked sequentially in source control and are not intended to be rerun manually against active production environments.*

---

## 📸 UI Highlights

The application interface is styled using a modern SaaS design system with custom CSS tokens, supporting fluid responsiveness and a built-in dark theme:

- **Admin Console (Desktop 1366px)**: Clean layout presenting platform operational metrics, unassigned recruiter indicators, aligned multi-filter toolbars, and server-side paginated user management with exactly one action trigger per row.
- **Unified Action Modals**: Replaces inline table form controls with single, focused administrative modals for role elevation, company access management, and account activation/deactivation.
- **Dark Mode**: Token-compliant dark slate theme applied across all pages, controls, cards, and modals with zero contrast bleed.
- **Audit Logs Activity History**: Structured compliance history displaying actor avatars, neutral system icons, human-readable timestamps, cohesive target pills, and formatted key-value event details.
- **Mobile Responsive Design (390px Viewport)**: Collapsible navigation bar, single-column metric card stacking, and horizontally contained data tables verified with 0px page-level horizontal overflow.

---

## ⚙️ Local Development Setup

### 1. Prerequisites
- **Python**: Version 3.11 or higher (Python 3.13 recommended)
- **MySQL**: Version 8.0 or higher
- **Git**: Installed and configured

### 2. Clone Repository & Create Virtual Environment
```bash
# Clone the repository
git clone https://github.com/govindturkar69-crypto/TalentAI-Recruitment-Platform.git
cd TalentAI-Recruitment-Platform

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` in the repository root:
```bash
cp .env.example .env
```
Populate `.env` using your local configuration values (placeholders shown below):
```env
# Database Settings
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=recruitment_db
MYSQL_SSL=False

# Application Security
FLASK_SECRET_KEY=your_random_secret_key_here
FLASK_DEBUG=True
ADMIN_EMAIL=admin@example.com
APP_ENV=development
APP_BASE_URL=http://localhost:5000

# Transactional Emails (Optional)
RESEND_API_KEY=your_resend_api_key
MAIL_FROM=noreply@example.com

# Error Monitoring (Optional)
SENTRY_DSN=your_sentry_dsn

# Advisory AI Service (Optional)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.6-luna
```

### 5. Initialize Database Schema
Ensure MySQL is running, create the database, and apply `database/schema.sql`:
```bash
mysql -u your_mysql_username -p -e "CREATE DATABASE IF NOT EXISTS recruitment_db;"
mysql -u your_mysql_username -p recruitment_db < database/schema.sql
```

### 6. Run Application
```bash
python app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## 🧪 Automated Testing & CI

### Running the Test Suite
```bash
# Run the automated test suite
pytest -v tests/ --ignore=tests/test_schema_contract.py --ignore=tests/test_phase4a.py --ignore=tests/test_phase4b.py
```
*Current verified pre-release test execution result: **267 passed, 1 skipped** in 9.25s.*

### Code Quality Checks
```bash
# Check code formatting with Black
black --check app.py core.py config.py routes/ services/ models/ tests/

# Run Ruff linter
ruff check .

# Syntax compilation check
python -m compileall -q app.py core.py config.py routes/ services/ models/
```

### Continuous Integration
A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on pushes and pull requests to enforce:
1. Syntax validation via `compileall`.
2. PEP 8 compliance via `ruff`.
3. Code formatting via `black`.
4. Automated test execution via `pytest`.

---

## 🚀 Production Deployment Notes

- **Hosting**: Deployed on **Render** as a web service running Gunicorn.
- **Managed Database**: Hosted on **Aiven Cloud MySQL 8.4** with required SSL connection encryption (`MYSQL_SSL=True`).
- **Health Monitoring**: Monitored via the `/healthz` endpoint returning database connectivity status without modifying state.
- **Email Delivery**: Integrated with Resend for secure, tokenized password recovery.

---

## 🗺️ Roadmap

### Completed in v1.0.0
- [x] Modular architecture with Flask Blueprints and Service layer.
- [x] Resume parsing and deterministic skill extraction via `pypdf`.
- [x] TF-IDF cosine similarity candidate match scoring via scikit-learn.
- [x] Candidate job search, application lifecycle, and self-service withdrawal.
- [x] Candidate interview dashboard and recruiter scheduling workflow.
- [x] Terminal-state automatic interview cancellation.
- [x] Recruiter applicant ranking, batch status updates, and Excel export.
- [x] Admin console with server-side pagination, user filters, and role mutation guards.
- [x] Multi-tenant company management and recruiter access controls.
- [x] Append-only audit logging and semantic detail formatting.
- [x] Responsive SaaS UI with dark theme support and zero horizontal overflow.
- [x] Production deployment on Render + Aiven Cloud MySQL with CI/CD.

### Future Work
Potential future enhancements may be evaluated separately.

---

## 📄 License

License: not specified.