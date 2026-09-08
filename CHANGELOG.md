# Changelog

All notable changes to the **TalentAI Recruitment Platform** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-08

### Initial Production Release (MVP)

TalentAI v1.0.0 delivers a complete, production-ready, AI-assisted recruitment platform automating the hiring lifecycle from resume intake and semantic matching to candidate evaluation, interview coordination, and administrative governance.

#### 🔐 Authentication & Security
- **Role-Based Access Control (RBAC)**: Enforced strict permission boundaries across `candidate`, `recruiter`, and `admin` roles.
- **Cryptographic Security**: Password hashing powered by Werkzeug `scrypt` with salting.
- **CSRF Protection**: Universal CSRF token validation on all state-modifying POST/PUT/DELETE requests.
- **Session Protection**: Hardened HTTP session cookies (`HttpOnly`, `SameSite=Lax`).
- **Rate Limiting**: Brute-force protection on authentication endpoints via Flask-Limiter.
- **Password Reset**: Token-based, time-limited password recovery workflow integrated with the Resend email API.
- **SQL Injection Prevention**: 100% parameterized SQL statements across all database queries.

#### 👤 Candidate Experience
- **AI Resume Upload & Parsing**: Drag-and-drop PDF resume extraction via PyPDF2.
- **Skill Extraction & Matching**: Automated extraction against a curated 50+ technical skill dictionary.
- **Smart Job Search & Filters**: Search jobs by keywords, locations, and skills with real-time active status filtering.
- **Application Tracking**: Dedicated candidate dashboard to view application status (`applied`, `shortlisted`, `rejected`, `hired`, `withdrawn`).
- **Atomic Application Withdrawal**: Self-service withdrawal option for candidates on non-terminal applications.
- **Saved Jobs**: Bookmark job listings for later review and application.
- **Candidate Interview Hub**: Clean view of scheduled, completed, and cancelled interviews with upcoming dates, duration, mode, and meeting details.
- **Candidate Profile**: Comprehensive profile builder for bios, experience, education, and portfolio/social links.
- **AI Resume Suggestions**: Interactive recommendations to optimize resume keywords against target job descriptions.

#### 🏢 Recruiter Workflows
- **Job Lifecycle Management**: Post, edit, close, reopen, and delete job listings with company association.
- **AI-Ranked Applicant Tracking**: Automatic candidate ranking sorting applicants by composite match score (`70%` skill coverage + `30%` TF-IDF semantic cosine similarity).
- **Bulk Candidate Processing**: Batch actions to shortlist, reject, or hire multiple candidates simultaneously.
- **Excel Data Export**: One-click download of applicant pipelines formatted into structured `.xlsx` spreadsheets.
- **Company Settings**: Configure company details, recruiter affiliations, and profile metadata.
- **Real-Time Notifications**: Instant alert triggers when candidates submit applications or status changes occur.

#### 📅 Interview Scheduling & State Automation
- **Interview Coordination**: Schedule, reschedule, update logistics (date, time, duration, online/in-person mode, meeting link), and cancel interviews.
- **Terminal State Auto-Cancellation**: Atomic helper ensuring all upcoming scheduled interviews for an application are automatically cancelled when the application is transitioned to `rejected`, `hired`, or `withdrawn`.
- **Multi-Party Visibility**: Coordinated interview views for both recruiters (job-specific applicants) and candidates (personal calendar).

#### 🛡️ Admin Console & Governance
- **Operational Metrics**: Platform-wide telemetry covering total users, active jobs, applications, interviews, active companies, and unassigned recruiters.
- **User Management**: Unified administration interface with server-side pagination, role filtering, status filtering, and search.
- **Self-Protection Guard**: Enforced business logic preventing logged-in administrators from modifying their own roles or deactivating their own accounts.
- **Company Multi-Tenancy Access**: Recruiter-to-company assignments with candidate guards (preventing company assignment to candidates before role elevation).
- **Company Management**: Full CRUD interface for managing enterprise tenant organizations.
- **Append-Only Audit Logs**: Immutable compliance audit trail tracking security, role, company, status, and interview lifecycle events.
- **Semantic Audit Details**: Standardized key-value detail formatting with restricted enum humanization and neutral system actor avatars.

#### 📊 Recruitment Analytics
- **Interactive Plotly Visualizations**: Real-time recruitment intelligence dashboards:
  - Skill demand frequency distribution.
  - Candidate match score distributions.
  - Application volume and status conversion pipeline.
  - Application trend timelines.
  - Top hiring companies and job categories.

#### 🎨 Design System & Accessibility
- **Enterprise SaaS Aesthetic**: Cohesive design system built on custom CSS variables and utility classes.
- **Full Dark Theme**: High-contrast, dark slate theme with zero white artifacts or contrast bleed.
- **Responsive Layouts**: Engineered for mobile (390px), tablet, standard desktop (1366px), and wide monitors (1536px) with verified `0px` horizontal page overflow.
- **Unified Action Modals**: Replaced dense, inline table forms with single, focused administrative modals.

#### 🚀 Production Readiness & DevOps
- **Cloud Architecture**: Deployed live on Render web services backed by managed MySQL 8.4 on Aiven Cloud with SSL encryption.
- **Database Connection Pooling**: Resilient connection lifecycle management using DBUtils `PooledDB`.
- **Database Migrations**: Version-controlled incremental schema evolution from `001_foundation.sql` through `009_add_interviews.sql`.
- **Uptime Monitoring**: Dedicated `/healthz` health-check endpoint verifying database connectivity.
- **Automated CI/CD**: GitHub Actions pipeline enforcing syntax validation (`compileall`), formatting (`black`), linting (`ruff`), and 267+ automated unit and integration tests (`pytest`).
