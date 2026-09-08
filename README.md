<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=32&pause=1000&color=6366F1&center=true&vCenter=true&width=650&lines=%F0%9F%A4%96+TalentAI;AI-Powered+Recruitment+Platform;Smart+Hiring+for+Modern+Teams" alt="TalentAI" />

<br/>

### An enterprise-grade, AI-assisted recruitment platform automating the hiring lifecycle — from intelligent resume parsing and semantic candidate ranking to multi-stage interview coordination and governance.

<br/>

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.4-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![CI/CD](https://img.shields.io/badge/CI-Passing-22c55e?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/govindturkar69-crypto/TalentAI-Recruitment-Platform/actions)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br/>

**[🌐 Live Demo](https://talentai-recruitment-platform.onrender.com) · [✨ Key Features](#-key-features) · [🏛️ Architecture](#%EF%B8%8F-architecture-overview) · [📸 UI Showcase](#-ui-showcase) · [⚙️ Local Setup](#%EF%B8%8F-local-development-setup) · [🧪 Testing & CI](#-automated-testing--ci) · [📄 Changelog](CHANGELOG.md)**

</div>

---

## 🌐 Live Production Demo

> ### 🔗 **[https://talentai-recruitment-platform.onrender.com](https://talentai-recruitment-platform.onrender.com)**
>
> Experience the live application directly in your browser. Register as a **Candidate** to upload resumes and apply to jobs, or log in as **Recruiter / Admin** to test candidate scoring, pipeline management, interview coordination, and audit trails.
>
> *Note: Hosted on cloud infrastructure; initial cold-start after periods of inactivity may take ~30 seconds while web and database containers initialize.*

---

## 📖 Project Overview

Modern recruitment pipelines struggle with manual resume screening, inefficient status coordination, and fragmented candidate communication. **TalentAI** streamlines and automates this process through a cohesive, full-stack SaaS platform powered by machine learning and enterprise design standards.

### Core Value Proposition
- **Resume Intake & Semantic Extraction**: Converts raw PDF resumes into structured skill profiles in milliseconds using PyPDF2 and custom NLP dictionaries.
- **Weighted Match Scoring**: Combines domain skill coverage (70%) and TF-IDF cosine similarity (30%) to objectively rank applicants.
- **Full-Lifecycle Candidate Coordination**: Tracks applications through structured states (`applied`, `shortlisted`, `rejected`, `hired`, `withdrawn`).
- **Coordinated Interview Scheduling**: Allows recruiters to schedule, reschedule, and conduct interviews while automatically syncing with candidate dashboards and handling terminal-state auto-cancellations.
- **Enterprise Governance & Multi-Tenancy**: Granular Role-Based Access Control (RBAC), multi-company isolation, administrative user management with self-protection guards, and immutable append-only audit logging.

---

## ✨ Key Features

### 👤 Candidate Experience
- **Smart Resume Ingestion**: Upload PDF resumes with immediate client-side validation and automated text extraction.
- **Dynamic Skill Profiling**: Extracts technical skills against a curated 50+ technology taxonomy.
- **Smart Application Flow**: Instant feedback displaying match percentages and fit scores upon submitting applications.
- **Job Discovery & Multi-Filter Search**: Full-text search across job titles, descriptions, required skills, and geographic locations.
- **Self-Service Application Management**: Candidates can track application progress in real time or withdraw non-terminal submissions.
- **Bookmarked / Saved Jobs**: Save listings to a persistent bookmark queue for later review.
- **Interactive Interview Portal**: View upcoming and past interviews with logistics (date, time, duration, mode, video conferencing links).
- **Comprehensive Profile Builder**: Manage personal bio, professional background, education, and portfolio/social links (GitHub, LinkedIn).
- **AI Keyword Suggestions**: Tailored suggestions to optimize resume keywords against target roles.

### 🏢 Recruiter Pipeline Management
- **Job Lifecycle Administration**: Create, edit, activate, close, and delete job requisitions mapped to tenant organizations.
- **Automated Candidate Ranking**: Applicants are dynamically ranked by AI match score upon receipt, eliminating manual filtering.
- **Batch Processing**: Shortlist, reject, or hire multiple candidates simultaneously with automated status validation.
- **Direct Candidate Profiles**: View applicant details, extracted skills, parsed resumes, and contact info in a consolidated view.
- **Integrated Interview Scheduling**: Schedule, reschedule, update logistics, or cancel interviews directly from candidate cards.
- **Terminal-State Automation**: Transitioning an application to `rejected`, `hired`, or `withdrawn` automatically and atomically cancels any pending future interviews.
- **Excel Report Generation**: Export applicant rosters, match scores, and status histories as structured `.xlsx` spreadsheets.
- **Real-Time Notification Alerts**: Instant notification badges for new applications and candidate withdrawals.

### 🛡️ Admin Console & Governance
- **Operational Health Telemetry**: Live metric cards displaying user counts, active listings, application throughput, interview metrics, and active tenant companies.
- **User Management**: Unified management table with server-side pagination, multi-filter dropdowns, and search by name/email.
- **Role Elevation & Self-Protection**: Role mutation controls with strict guards preventing the logged-in administrator from demoting or locking their own account.
- **Tenant Company Access Controls**: Recruiter-to-company assignments with validation preventing company allocation to candidates prior to role change.
- **Company CRUD Management**: Dedicated portal to create, edit, activate, and deactivate client organizations.
- **Immutable Append-Only Audit Trail**: Full regulatory compliance logging for sensitive security, role, company, status, and interview lifecycle transitions.
- **Semantic Audit Formatter**: Structured key-value event detail rendering with restricted enum humanization and neutral system actor avatars.

### 📊 Real-Time Analytics
- **Interactive Plotly Dashboards**: Executive-level data visualizations embedded natively:
  - Skill demand distribution across active listings.
  - Candidate match score distribution curves.
  - Application conversion funnel (Applied → Shortlisted → Hired).
  - Application volume timelines and trends.
  - Top hiring companies and departmental requisitions.

---

## 🤖 AI Resume Analysis & Scoring Engine

TalentAI evaluates candidate fit through a hybrid algorithmic approach combining deterministic domain skills extraction with natural language vectorization:

```
┌───────────────────────────────────────────────────────────┐
│                      Resume Upload                        │
└─────────────────────────────┬─────────────────────────────┘
                              │
               PyPDF2 Text Extraction & Cleaning
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    Deterministic Extraction        TF-IDF Vectorization
      (50+ Skill Taxonomy)         (Cosine Similarity vs JD)
              │                               │
              ▼                               ▼
      Skill Score (70%)              TF-IDF Score (30%)
              │                               │
              └───────────────┬───────────────┘
                              ▼
        Composite Match Score = (Skill × 0.70) + (TF-IDF × 0.30)
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
       ≥ 75%               50% – 74%             < 50%
   Strong Match          Moderate Match        Weak Match
  (Auto-Shortlist)          (Review)            (Flagged)
```

### Mathematical Formulation
$$\text{Skill Score} = \frac{|\text{Extracted Skills} \cap \text{Required Skills}|}{|\text{Required Skills}|} \times 100$$

$$\text{TF-IDF Score} = \cos(\mathbf{v}_{\text{resume}}, \mathbf{v}_{\text{job}}) \times 100$$

$$\text{Composite Score} = (0.70 \times \text{Skill Score}) + (0.30 \times \text{TF-IDF Score})$$

---

## 🔒 Security & Quality Highlights

- **Role-Based Access Control (RBAC)**: Centralized route decorators (`@login_required`, `@recruiter_required`, `@admin_required`) enforce authorization across all endpoints.
- **CSRF Token Validation**: Universal CSRF protection powered by Flask-WTF; all mutation forms and AJAX calls require signed tokens.
- **Cryptographic Password Security**: Hashed using Werkzeug `scrypt` key derivation with unique cryptographic salts.
- **Rate Limiting**: Integrated brute-force mitigation on authentication endpoints (`/login`, `/register`, `/forgot-password`) using Flask-Limiter.
- **Self-Protection Safeguards**: Built-in backend and frontend validation prevents administrators from accidentally revoking their own permissions or deactivating their own accounts.
- **SQL Injection Prevention**: 100% of database interactions utilize parameterized query builders; zero string concatenations.
- **Session Hardening**: Secure session cookies configured with `HttpOnly`, `SameSite=Lax`, and `Secure` flags in production.
- **Audit Immutability**: Dedicated append-only database table tracking actors, targets, actions, and timestamped payloads.

---

## 🛠️ Tech Stack

| Domain | Technology / Library | Purpose |
|---|---|---|
| **Backend Framework** | Python 3.13, Flask 2.3 | Modular Blueprints, REST APIs, Application Routing |
| **Database & Pooling** | MySQL 8.4, PyMySQL, DBUtils `PooledDB` | Transactional persistence, connection pool lifecycle |
| **AI / Machine Learning** | scikit-learn, PyPDF2 | TF-IDF vectorization, cosine similarity, PDF extraction |
| **Data Analytics** | Pandas, Plotly | Data manipulation, interactive SVG/HTML visualization charts |
| **Frontend Architecture** | Bootstrap 5.3, Bootstrap Icons, Vanilla JS | Responsive grid, accessible controls, theme engine |
| **Security & Auth** | Werkzeug Security, Flask-WTF, Flask-Limiter | scrypt password hashing, CSRF tokens, rate limiting |
| **Email Delivery** | Resend API | Transactional password reset and notification emails |
| **Export Engine** | openpyxl | Formatted Excel spreadsheet generation |
| **Production WSGI** | Gunicorn | High-concurrency WSGI HTTP server |
| **Cloud Hosting** | Render (Web Service), Aiven (Managed MySQL) | Cloud deployment with automatic SSL termination |
| **CI / CD Quality** | GitHub Actions, Pytest, Ruff, Black | Automated linting, code formatting, and test execution |

---

## 🏛️ Architecture Overview

TalentAI is architected with a decoupled 3-tier modular design separating routing, business orchestration, and database operations:

```
TalentAI Platform
├── routes/                      # Presentation & HTTP Routing (Flask Blueprints)
│   ├── auth.py                  # Authentication, Registration, Password Resets
│   ├── candidate.py             # Candidate Portal, Profile, Applications, Jobs
│   ├── recruiter.py             # Requisitions, Pipeline Management, Interviews
│   ├── admin.py                 # Admin Console, User Management, Companies, Audit Logs
│   └── analytics.py             # Executive Visualizations & Reporting
│
├── services/                    # Business Logic Layer (Pure Python Services)
│   ├── candidate_service.py     # Profile workflows, application submissions & withdrawal
│   ├── recruiter_service.py     # Applicant ranking, bulk actions, requisition updates
│   ├── interview_service.py     # Scheduling, rescheduling, terminal auto-cancellation
│   ├── audit_service.py         # Structured, append-only compliance logging
│   ├── ai_resume_service.py     # Resume scoring and keyword recommendation logic
│   ├── email_service.py         # Resend API integration for password reset delivery
│   ├── notification_service.py  # In-app transactional notification management
│   └── workflow.py              # Application status state machine validation
│
├── models/                      # Analytical & Machine Learning Models
│   └── resume_parser.py         # PyPDF2 extraction, 50+ skill taxonomy, TF-IDF engine
│
├── core.py                      # Connection Pooling (DBUtils PooledDB) & Lifecycle
├── config.py                    # Environment Configuration & Variable Validation
├── database/                    # Persistence Schema & Migrations
│   ├── schema.sql               # Baseline database tables & relational constraints
│   └── migrations/              # Versioned incremental SQL migrations (001 - 009)
│
└── templates/                   # Jinja2 Presentation Templates (HTML5 + CSS Tokens)
```

---

## 🗃️ Database Schema & Versioned Migrations

The relational schema is managed through MySQL 8.4 and tracked with explicit, forward-only SQL migration scripts:

| Table Name | Description | Key Indexes |
|---|---|---|
| `users` | Candidate, recruiter, and administrator accounts | `email`, `role`, `company_id`, `is_active` |
| `jobs` | Job listings and recruitment requirements | `recruiter_id`, `company_id`, `is_active`, `created_at` |
| `resumes` | Uploaded resumes, raw text, and parsed skills | `user_id`, `uploaded_at` |
| `applications` | Candidate-to-job mappings with status and score | `candidate_id`, `job_id`, `status`, `match_score` |
| `candidate_profiles`| Extended professional background and portfolio links | `candidate_id` |
| `companies` | Multi-tenant client organizations and settings | `name`, `is_active` |
| `interviews` | Scheduled, completed, and cancelled interviews | `application_id`, `recruiter_id`, `status`, `scheduled_at` |
| `audit_logs` | Append-only compliance and administrative trail | `actor_id`, `action`, `target_type`, `created_at` |
| `saved_jobs` | Candidate bookmarks and saved requisition queue | `candidate_id`, `job_id` |
| `notifications` | Transactional alerts and unread status markers | `user_id`, `is_read`, `created_at` |
| `password_resets` | Time-limited cryptographic password recovery tokens | `token`, `user_id`, `expires_at` |

### Migration History
1. `001_foundation.sql`: Base tables for users, jobs, applications, resumes, notifications.
2. `002_candidate_profile.sql`: Extended candidate profile metadata and social links.
3. `003_reconcile_foundation.sql`: Schema alignment and constraint reconciliation.
4. `004_job_lifecycle.sql`: Company association and lifecycle status tracking.
5. `005_reconcile_candidate_profile.sql`: Safe profile schema normalization.
6. `006_reconcile_job_lifecycle.sql`: Requisition integrity constraints.
7. `007_add_saved_jobs.sql`: Persistent bookmarking queue for candidates.
8. `008_add_withdrawn_status.sql`: Self-service application withdrawal state.
9. `009_add_interviews.sql`: Comprehensive interview coordination, company tenancy, and audit logs.

---

## 📸 UI Showcase

The user interface is designed according to modern SaaS principles, featuring responsive layouts, custom design tokens, dark theme support, and zero horizontal page overflow across all viewports.

### Admin Console & User Management (1366px Desktop)
![Admin Console Desktop](ui_screenshots/ProdAdminFinal_1366.png)
*Executive dashboard highlighting platform health telemetry, recruitment metrics, and user management table with aligned filters.*

### Single Reusable User Management Modal
![Admin User Manage Modal](ui_screenshots/ProdAdminFinal_Modal.png)
*Unified modal replacing inline mutation clutter. Includes role elevation, candidate company guards, and account status controls.*

### Admin Console in Dark Theme
![Admin Console Dark Theme](ui_screenshots/ProdAdminFinal_Dark.png)
*Tailored dark mode palette with high contrast, token-driven borders, and zero white background artifacts.*

### Audit Logs & Immutable Activity History
![Audit Logs Desktop](ui_screenshots/ProdAuditFinal_1366.png)
*Comprehensive regulatory audit trail showing actor avatars, human-readable dates, cohesive target pills, and semantic payload details.*

### Audit Logs in Dark Theme
![Audit Logs Dark Theme](ui_screenshots/ProdAuditFinal_Dark.png)
*Audit history in dark theme with semantic badges, event status pills, and structured change summaries.*

### Mobile Responsive Experience (390px Viewport)
<div align="center">
  <img src="ui_screenshots/ProdAdminFinal_390.png" width="300" alt="Admin Mobile" />
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="ui_screenshots/ProdAuditFinal_390.png" width="300" alt="Audit Mobile" />
</div>
*Fluid mobile experience featuring collapsible navigation, vertically stacked metric cards, and responsive data containers (verified 0px overflow).*

---

## ⚙️ Local Development Setup

Follow these instructions to run the TalentAI platform locally in your development environment:

### 1. Prerequisites
- **Python**: Version 3.11 or higher (Python 3.13 recommended)
- **MySQL**: Version 8.0 or higher
- **Git**: Installed and configured

### 2. Clone Repository & Setup Virtual Environment
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
# Install core and development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root by copying the template:
```bash
cp .env.example .env
```
Open `.env` and fill in your local MySQL and application values using placeholder credentials:
```env
# Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=recruitment_db
MYSQL_SSL=False

# Application Security
FLASK_SECRET_KEY=generate_a_random_32_character_secret_key
FLASK_DEBUG=True
ADMIN_EMAIL=admin@example.com
APP_ENV=development
APP_BASE_URL=http://localhost:5000

# Transactional Emails via Resend (Optional for local testing)
RESEND_API_KEY=re_your_placeholder_api_key
MAIL_FROM=onboarding@resend.dev

# Sentry Monitoring (Optional)
SENTRY_DSN=

# OpenAI Services (Optional)
OPENAI_API_KEY=your_placeholder_openai_key
OPENAI_MODEL=gpt-5.6-luna
```

### 5. Initialize Database Schema
Ensure your MySQL server is running, then create the database and apply the baseline schema:
```bash
# Create database and tables
mysql -u your_mysql_username -p -e "CREATE DATABASE IF NOT EXISTS recruitment_db;"
mysql -u your_mysql_username -p recruitment_db < database/schema.sql
```

### 6. Launch the Application
```bash
python app.py
```
Access the application at: **[http://localhost:5000](http://localhost:5000)**

---

## 🧪 Automated Testing & CI

TalentAI maintains a rigorous automated testing suite verifying route protection, authentication security, role authorization, resume parsing algorithms, and interview scheduling workflows.

### Running the Test Suite
```bash
# Run the complete test suite
pytest -v tests/ --ignore=tests/test_schema_contract.py --ignore=tests/test_phase4a.py --ignore=tests/test_phase4b.py

# Run targeted admin and audit tests
pytest -v tests/test_admin.py tests/test_admin_audit.py tests/test_admin_phase5e.py

# Run route and security tests
pytest -v tests/test_auth.py tests/test_security.py tests/test_candidate.py tests/test_recruiter.py
```

### Code Formatting & Static Analysis
```bash
# Check code formatting with Black
black --check app.py core.py config.py routes/ services/ models/ tests/

# Run lint checks with Ruff
ruff check .

# Verify Python syntax compilation
python -m compileall -q app.py core.py config.py routes/ services/ models/
```

### Continuous Integration (GitHub Actions)
Every pull request and push to `main` triggers our automated CI pipeline (`.github/workflows/ci.yml`), validating:
1. Python syntax via `compileall`.
2. PEP 8 adherence and lint rules via `ruff`.
3. Strict code formatting via `black`.
4. Automated test execution across all 267+ unit and integration tests via `pytest`.

---

## 🚀 Production Deployment Notes

The production release of TalentAI is hosted on a high-availability cloud architecture:
- **Web Application**: Hosted on **Render** using Gunicorn multi-worker WSGI processes.
- **Managed Database**: Hosted on **Aiven Cloud MySQL 8.4** with mandatory SSL certificate encryption and automated backups.
- **Transactional Delivery**: Powered by **Resend** for cryptographically secure password reset emails.
- **Uptime Monitoring**: Native `/healthz` endpoint verifying live database ping latency without mutating state.

### Production Readiness Verification Checklist
- [x] All database queries execute via DBUtils connection pool with safe release.
- [x] All state mutations protected by CSRF tokens and role-based guards.
- [x] Strict self-protection preventing administrative account lockout.
- [x] Zero page-level horizontal overflow across all responsive screen sizes (390px - 1536px).
- [x] Dark mode verified with zero white contrast bleed.
- [x] All passwords hashed with Werkzeug `scrypt`.
- [x] No plaintext credentials or API keys stored in version control.

---

## 🗺️ Roadmap & Future Milestones

### Completed in v1.0.0 (MVP)
- [x] Modular 3-tier Flask Blueprint and Service Layer architecture.
- [x] PyPDF2 resume parsing with 50+ skill taxonomy extraction.
- [x] Hybrid TF-IDF cosine similarity candidate match scoring.
- [x] Complete candidate application lifecycle and atomic self-withdrawal.
- [x] Candidate interview scheduling, rescheduling, and cancellation portal.
- [x] Terminal-state automated interview cancellation.
- [x] Recruiter applicant ranking, batch status transitions, and Excel export.
- [x] Enterprise Admin Console with pagination, filtering, and role elevation.
- [x] Multi-tenant company management and recruiter access controls.
- [x] Append-only audit logging and semantic activity history.
- [x] Full UI redesign with custom CSS design tokens and dark mode.
- [x] Production deployment on Render + Aiven Cloud MySQL with CI/CD.

### Upcoming Milestones
- [ ] **Calendar Integrations**: Two-way synchronization with Google Calendar and Outlook Calendar via OAuth.
- [ ] **Live Video Interviewing**: Native WebRTC integration for in-browser video interviews.
- [ ] **Webhook Integrations**: Outgoing webhook notifications for enterprise ATS (Greenhouse, Lever) syncing.
- [ ] **Advanced AI Summarization**: LLM-generated executive candidate summaries and interview question generation.

---

## 📄 License & Maintainer

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

<div align="center">

**Developed & Maintained by [Govind Turkar](https://github.com/govindturkar69-crypto)**<br/>
*AI & Full-Stack Software Engineer*

[![GitHub](https://img.shields.io/badge/GitHub-govindturkar69--crypto-181717?style=for-the-badge&logo=github)](https://github.com/govindturkar69-crypto)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Govind_Turkar-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/govind-turkar-1487a0430/)
[![Email](https://img.shields.io/badge/Email-Contact_Me-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:govindturkar69@gmail.com)

</div>