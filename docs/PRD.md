# Product Requirements Document

## Documentation Basis

- Repository branch: `main`
- Repository HEAD: `891d7ac4947d7a4153d2da7389aabdaf116e3b52`
- Release snapshot: `v1.0.0`
- Analysis method: Static repository inspection
- Runtime verification: Present but not runtime-verified (documentation-only analysis)
- Generated/updated: `2026-09-11`

---

## Product Overview

**TalentAI** is an AI-assisted recruitment and applicant tracking platform built with Flask and MySQL. It manages the complete hiring pipeline: candidate resume parsing and profile management, objective candidate ranking against job descriptions using deterministic skill extraction and TF-IDF text similarity, coordinated multi-round interview scheduling with automatic state handling, recruiter pipeline workflows with batch processing and Excel export, and administrative governance featuring tenant company management, role assignment, and append-only audit logging.

The product separates deterministic local evaluation from optional advisory AI. Core applicant scoring operates entirely in-process using `pypdf`, `scikit-learn`, and a curated technical taxonomy, while optional OpenAI Structured Outputs integration provides candidates with non-authoritative resume enhancement advice.

---

## Problem Statement

Traditional talent intake and recruitment workflows suffer from fragmented tooling, subjective manual screening, lack of auditability, and poor visibility across stages:
1. **Manual Resume Screening**: Reviewing PDF resumes manually is slow and inconsistent across candidates.
2. **Subjective Scoring**: Recruiters often lack standardized metrics to rank candidates objectively against job requisitions.
3. **Disjointed Interview Logistics**: Interview scheduling often occurs outside the applicant tracking pipeline, resulting in scheduling conflicts or orphaned interviews when applications are rejected or withdrawn.
4. **Governance Deficits**: In growing organizations, recruiter access, company tenant assignments, and administrative state mutations lack immutable audit trails.
5. **Candidate Blindspots**: Applicants rarely have real-time visibility into their application stages, match scores, or interview schedules.

TalentAI solves these issues in a unified, self-contained web platform with role-based portals for candidates, recruiters, and administrators.

---

## Goals

1. **Automate Resume Intake**: Extract plain text from PDF resumes and match skills against a catalog of 50+ technical skills.
2. **Provide Objective Ranking**: Compute a deterministic composite fit score (70% skill coverage + 30% TF-IDF cosine similarity) for every application.
3. **Streamline Recruiter Operations**: Provide job posting, status transitions, batch applicant updates, formatted Excel roster export, and candidate detail viewers.
4. **Coordinate Interviews**: Enable scheduling, updating, completing, and cancelling of interviews, with automatic cancellation of future interviews upon terminal application decisions.
5. **Ensure Governance & Traceability**: Centralize user management, multi-tenant company association, and append-only audit logging with safe detail formatting.
6. **Support Responsive & Themed Access**: Deliver a responsive UI (from 390px mobile viewports to desktop) featuring a built-in dark theme.

---

## Target Users

1. **Job Candidates**: Technical professionals searching for job opportunities, submitting applications, maintaining their portfolios, reviewing match scores, tracking interview dates, and seeking resume optimization advice.
2. **Recruiters & Hiring Managers**: Corporate recruiters and talent acquisition staff creating requisitions, assessing ranked candidates, scheduling interviews, updating candidate statuses, and exporting rosters.
3. **Platform Administrators**: Super-users and HR operations personnel responsible for tenant company management, user role elevation, account activation/deactivation, and auditing compliance logs.

---

## User Roles

The platform enforces three distinct user roles:

| Role | Definition in System | Key Capabilities |
|---|---|---|
| **Candidate** | `role = 'candidate'` in `users` table | Upload PDF resumes, manage personal profile (education, experience, projects, certifications, achievements, curated skills), search active jobs, bookmark jobs, apply for jobs, withdraw active applications, view interview schedules, request optional AI resume improvement advice. |
| **Recruiter** | `role = 'recruiter'` in `users` table | Post, edit, close, reopen, and delete job requisitions; view ranked applicant lists with composite scores; view applicant candidate profiles and PDF resumes; update applicant statuses individually or in bulk; schedule, reschedule, complete, and cancel interviews; export applicant rosters to Excel (`.xlsx`); view recruitment analytics charts. |
| **Admin** | Email matches `Config.ADMIN_EMAIL` (`session["is_admin"] = True`) | Access the Admin Console (`/admin/dashboard`); monitor platform-wide operational telemetry; view server-side paginated user management table; search, filter, and modify user roles (`candidate` $\leftrightarrow$ `recruiter`); toggle account activation status (`is_active`); assign recruiters to tenant companies; create, edit, and toggle active status of companies; inspect append-only audit logs with action, actor, target, and date filters. |

*Note on Admin Identity*: An admin account is identified dynamically at login when the user's email matches the configured `ADMIN_EMAIL`. In the database, the admin user's `role` column is set to `'recruiter'`.

---

## User Journeys

### 1. Candidate Onboarding to Application
1. Candidate navigates to `/register` and signs up with name, email, and password ($\ge 8$ characters).
2. Candidate logs in at `/login` and is redirected to `/candidate/dashboard`.
3. Candidate uploads a PDF resume at `/candidate/upload_resume`. The system extracts raw text and detects skills via `models/resume_parser.py`.
4. Candidate enriches their profile at `/candidate/profile` with education, work history, projects, certifications, and achievements.
5. Candidate browses active listings at `/candidate/jobs` or views personalized recommendations at `/candidate/recommendations`.
6. Candidate inspects a job's details at `/candidate/job/<job_id>`, reviews matched and missing skills, and clicks **Apply Now**.
7. System immediately computes the composite fit score (70% skill coverage + 30% TF-IDF similarity), creates the application record, and emits notifications.
8. Candidate monitors status on `/candidate/applications`. If circumstances change prior to a terminal decision, candidate can click **Withdraw Application**.

### 2. Recruiter Sourcing to Interview Coordination
1. Recruiter logs in at `/login` and is redirected to `/recruiter/dashboard`.
2. Recruiter posts a new job requisition at `/recruiter/post_job` specifying title, comma-separated required skills, description, location, and experience.
3. As candidates apply, recruiter navigates to `/recruiter/job/<job_id>/applicants`.
4. Recruiter views applicants ranked from highest to lowest composite score, filters by candidate name/email or status, and selects candidates.
5. Recruiter inspects individual candidate profiles (`/recruiter/application/<app_id>/candidate`) and views the submitted PDF resume (`/recruiter/application/<app_id>/resume`).
6. Recruiter updates applicant status to `shortlisted` (either individually or via bulk selection).
7. Recruiter opens the interview scheduling hub at `/recruiter/application/<app_id>/interviews`, selects date/time, duration, mode (`online`, `in_person`, `phone`), provides a meeting link or location, and submits.
8. When the interview occurs, recruiter marks it completed or reschedules if needed.
9. If the recruiter decides to hire or reject the applicant, setting status to `hired` or `rejected` automatically cancels any remaining upcoming scheduled interviews and logs audit events.
10. Recruiter exports the final ranked list to Excel via `/recruiter/job/<job_id>/export`.

### 3. Administrator Governance & Tenant Management
1. Administrator logs in using the account matching `ADMIN_EMAIL` and is redirected to `/admin/dashboard`.
2. Admin reviews operational telemetry: total users, active jobs, applications across stages, interviews, and tenant companies.
3. Admin searches for a user in the server-side paginated user management table.
4. Using focused action modals, admin promotes a candidate to recruiter, assigns the recruiter to an active tenant company, or deactivates an inactive user (with self-protection safeguards preventing admin self-deactivation/demotion).
5. Admin visits `/admin/companies` to create new tenant organizations or toggle company active status.
6. Admin visits `/admin/audit-logs` to review platform activities (role changes, status changes, company updates, interview cancellations) with date, action, and actor filters.

---

## Main Workflows

```
Candidate Uploads Resume (PDF)
        │
        ▼
Extracts Text (pypdf) & Skills (SKILLS_DB)
        │
        ▼
Candidate Applies to Job Requisition
        │
        ▼
Calculates Local Composite Score:
  • Skill Score (70%): |Matched Skills| / |Required Skills| * 100
  • TF-IDF Score (30%): Cosine Similarity(Resume, Job Description) * 100
        │
        ▼
Recruiter Reviews Ranked Applicants
        │
        ├───────────────────────────────┐
        ▼                               ▼
    [Shortlist]                     [Reject] ──► Auto-cancels future interviews
        │
        ▼
Recruiter Schedules Interview (Online / In-Person / Phone)
        │
        ├───────────────────────────────┐
        ▼                               ▼
  [Complete]                        [Cancel]
        │
        ▼
Recruiter Makes Final Decision
        │
        ├───────────────────────────────┐
        ▼                               ▼
     [Hire]                          [Reject]
        │                               │
        ▼                               ▼
Auto-cancels future interviews   Auto-cancels future interviews
```

---

## Implemented Features

### Candidate Capabilities
- **Resume Upload & Parsing**: PDF upload with secure filename sanitization, text extraction via `pypdf`, and skill detection against 50+ technical keywords.
- **Application Submission**: One-click job application calculating real-time composite match score.
- **Self-Service Withdrawal**: Withdrawal allowed for active applications in `applied` or `shortlisted` status.
- **Saved Jobs**: Bookmarking and unsaving of job requisitions for later review.
- **Job Discovery & Search**: Keyword and location-based filtering of active listings.
- **Candidate Profile Management**: Editor for bio, contact number, location, years of experience, LinkedIn/GitHub/Portfolio URLs, and curated skills taxonomy.
- **Profile Sub-Entities**: CRUD management for Education, Work Experience (with current employer flag), Projects (with URL), Certifications (with credential URL), and Achievements.
- **Profile Completion Metric**: Weighted completion algorithm (up to 100%) factoring in core bio fields, uploaded resume, curated skills, education, experience, and projects.
- **Candidate Interview View**: Chronological view of scheduled, upcoming, completed, and cancelled interviews with logistics and meeting links.
- **Optional Advisory AI**: Local-context-aware resume enhancement recommendations powered by OpenAI Structured Outputs (when configured).

### Recruiter Capabilities
- **Requisition Lifecycle**: Create, edit, close (deactivate), reopen (activate), and delete job postings.
- **Candidate Ranking**: Automatic sorting of applicants by descending composite score.
- **Status Filtering & Search**: Instant filtering of applicants by keyword (name/email) and pipeline status.
- **Batch Processing**: Multi-select bulk status updates (`shortlisted`, `rejected`, `hired`).
- **Profile & Resume Inspection**: Access to candidate background information and inline view of uploaded PDF resumes.
- **Interview Coordination**: Schedule, edit/reschedule, cancel, and mark complete interviews for shortlisted candidates.
- **Terminal State Auto-Cancellation**: Atomic cancellation of future scheduled interviews when an application transitions to `rejected`, `hired`, or `withdrawn`.
- **Excel Roster Export**: Formatted `.xlsx` download including rank, applicant name, email, score, matched/missing skills, status, and application date.
- **Recruiter Settings**: View assigned company tenant details (name, description, website).

### Administrator Capabilities
- **Operational Metrics**: Aggregated counters for platform users, active jobs, applications pipeline, interview states, and active companies.
- **User Management**: Server-side paginated table with name/email search, role filter, status filter, and company assignment filter.
- **Admin Action Modals**: Dedicated modals for role updates, company assignment, and status modification.
- **Administrative Self-Protection**: Enforced guard preventing the active administrator from demoting their own role or deactivating their own account.
- **Tenant Management**: Server-side paginated list of client companies with creation form, editor, and active status toggling.
- **Company Assignment Guard**: Restriction ensuring only recruiter accounts can be assigned to companies.
- **Audit Logging**: Immutable, append-only log recording actor, action, target type, target ID, and sanitized key-value details.
- **Audit Viewer**: Comprehensive filter bar (action, target type, actor, date range) with human-readable enum labels and sanitized detail parsing.

---

## Functional Requirements

- **FR-01: User Authentication**: The system shall authenticate users via email and password, utilizing `scrypt` hashing with unique salts.
- **FR-02: Rate Limiting**: The system shall throttle authentication requests (5/min for `/login`, 5/hour for `/register`, 3/hour for `/forgot_password`, 3/day for `/api/resume/analyze`).
- **FR-03: Candidate Profile Completion**: The system shall compute a completion percentage based on core profile fields, resume presence, curated skills, education, and optional history items.
- **FR-04: Skill Extraction**: The system shall match extracted resume text against a predefined database of technical keywords (`SKILLS_DB`).
- **FR-05: Objective Match Scoring**: The system shall calculate applicant scores as $(\text{Skill Score} \times 0.70) + (\text{TF-IDF Score} \times 0.30)$ when a job description is present, or Skill Score alone when no description exists.
- **FR-06: State Machine Enforcement**: The system shall enforce valid status transitions for applications (`applied` $\rightarrow$ `shortlisted` $\rightarrow$ `hired`/`rejected`, or `withdrawn` by candidate).
- **FR-07: Interview Scheduling Validation**: The system shall permit interview scheduling only for `shortlisted` applications, requiring a future date/time, duration between 5 and 480 minutes, and valid URLs for online mode.
- **FR-08: Automatic Interview Cancellation**: The system shall atomically cancel any future scheduled interviews when an application enters `rejected`, `hired`, or `withdrawn`.
- **FR-09: Recruiter Isolation**: The system shall restrict recruiters to viewing, editing, updating, and exporting only jobs and applications belonging to their own user account.
- **FR-10: Audit Event Capture**: The system shall write an immutable log entry to `audit_logs` for administrative actions, application status changes, candidate withdrawals, and interview lifecycle events.
- **FR-11: Excel Roster Export**: The system shall generate styled `.xlsx` spreadsheets containing ranked candidate rosters.
- **FR-12: Health Check**: The system shall expose a `/healthz` endpoint returning HTTP 200 when the database is reachable and HTTP 503 when unreachable.

---

## Non-Functional Requirements

### Security
- **RBAC**: All protected routes must enforce `@login_required` or `@admin_required`.
- **CSRF Protection**: All state-modifying requests (POST) must validate a CSRF token generated by Flask-WTF.
- **SQL Injection Prevention**: All database access must use parameterized queries via `pymysql` and DBUtils `PooledDB`.
- **Cookie Flags**: Session cookies must be configured with `HttpOnly=True`, `SameSite=Lax`, and `Secure` (in non-debug environments).
- **PII Redaction**: Email addresses and phone numbers must be redacted from resume text before dispatching to external AI services.

### Usability & Responsiveness
- **Fluid Layout**: All pages must render without horizontal scrollbars across viewports from 390px mobile screens to 1536px desktop monitors.
- **Dark Mode**: Complete CSS custom property theme engine supporting instant switching between light and dark modes with zero contrast bleed.

### Reliability
- **Connection Pooling**: Database queries reuse pooled connections via DBUtils `PooledDB` to prevent socket exhaustion.
- **Graceful Error Handling**: Custom HTTP 404 and 500 error pages to prevent framework stack trace leakage.

---

## Business Rules

1. **Role Registration**: Public registration at `/register` creates candidate accounts only (`role = 'candidate'`). Recruiter elevation is performed exclusively by administrators.
2. **Admin Email Protection**: The primary admin email configured in `ADMIN_EMAIL` cannot be registered via public registration, cannot be demoted, and cannot be deactivated.
3. **Application Uniqueness**: A candidate may submit only one application per job requisition.
4. **Interview Eligibility**: Only applications in `shortlisted` status are eligible to have new interviews scheduled.
5. **Interview Past-Date Rule**: Interviews cannot be scheduled or rescheduled to a timestamp in the past.
6. **Interview Completion Rule**: Interviews cannot be marked as completed before their scheduled date and time has passed.
7. **Terminal Application State**: Applications in `rejected`, `hired`, or `withdrawn` states cannot undergo further status transitions.
8. **Recruiter Ownership**: Recruiters cannot view, alter, or schedule interviews for requisitions owned by other recruiters.
9. **Company Assignment Constraint**: Only recruiter accounts may be associated with a tenant company.

---

## Inputs and Outputs

| Component | Key Inputs | Key Outputs |
|---|---|---|
| **Resume Upload** | PDF file ($\le 5$ MB) | Stored PDF file in `uploads/`, raw text in `resumes.raw_text`, comma-separated skill list in `resumes.skills`. |
| **Job Application** | `job_id`, candidate session | Application record with composite score, matched skills, missing skills, initial status `applied`. |
| **Interview Scheduling** | `application_id`, `scheduled_at`, `duration_minutes`, `mode`, `location_or_link`, `notes` | Record in `interviews`, candidate notification, audit log entry. |
| **Batch Status Update** | List of `selected_apps`, `bulk_status`, recruiter session | Updated status in `applications`, cancelled interviews (if applicable), candidate notifications, audit logs. |
| **Roster Export** | `job_id`, recruiter session | Downloadable `.xlsx` spreadsheet with styled headers and ranked applicant rows. |
| **AI Resume Suggestions** | Resume raw text, local analysis dict, optional job context | Structured JSON containing summary, strengths, priority improvements, and section-specific tips. |

---

## Scope

### In Scope (Implemented in Repository)
- Three-tier user access: Candidate, Recruiter, Admin.
- Local deterministic resume parsing and keyword matching via `pypdf`.
- TF-IDF cosine similarity text scoring via `scikit-learn`.
- Job posting, editing, active toggle, and deletion.
- Candidate application lifecycle (`applied`, `shortlisted`, `rejected`, `hired`, `withdrawn`).
- Complete interview lifecycle (`scheduled`, `completed`, `cancelled`) with automated terminal-state cancellation.
- Excel candidate roster export via `openpyxl`.
- Interactive Plotly analytics dashboards.
- Multi-tenant company creation and recruiter assignment.
- Append-only audit logging with safe detail rendering.
- Password reset token workflow with Resend transactional email integration.
- Light and dark theme engine with responsive UI down to 390px.
- Health check endpoint `/healthz`.

### Out of Scope (Not Implemented / Future Consideration)
- Real-time video/audio calling embedded inside the application.
- Direct integration with calendar providers (Google Calendar, Microsoft Outlook, CalDAV).
- Automated interview reminder emails or SMS delivery.
- Complex resume formats beyond PDF (e.g., `.docx`, `.rtf`, `.odt`).
- Native billing, subscription tiers, or payment gateway processing.
- Two-factor authentication (2FA/MFA) or SSO (SAML, OAuth2 social logins).
- Full-text database search engine integration (Elasticsearch, OpenSearch).

---

## Current Limitations

1. **In-Memory Rate Limiting**: The Flask-Limiter instance uses `memory://` storage, which limits rate limiting coordination to single-process deployments. Distributed deployments would require a Redis backend.
2. **Synchronous PDF Processing**: Text extraction and skill parsing run synchronously inside the request loop during resume upload. Very large or complex PDFs may cause brief request latency.
3. **Session Invalidation Scope**: Password reset clears the session of the current browser client, but does not invalidate existing signed cookie sessions on secondary devices due to stateless cookie storage.
4. **Single Admin Definition**: Administrative privileges are granted exclusively by matching the single email specified in `ADMIN_EMAIL`.
5. **PDF-Only Resumes**: Only `.pdf` extensions are accepted by the upload validator; Word documents (`.docx`) are rejected.

---

## Acceptance Criteria

1. **AC-01 (Authentication)**: Registering with valid credentials creates an active candidate account. Registration with passwords $<8$ characters or empty fields fails with a warning flash.
2. **AC-02 (Admin Isolation)**: Non-admin users attempting to access `/admin/*` routes are redirected to `/` with an "Access denied" message.
3. **AC-03 (Scoring Integrity)**: When a candidate applies for a job, the calculated score is stored in `applications.score` and exactly matches $(0.70 \times \text{Skill Score}) + (0.30 \times \text{TF-IDF Score})$ rounded to 2 decimal places.
4. **AC-04 (Interview Scheduling Guard)**: Attempting to schedule an interview for an application with status other than `shortlisted` returns an error message.
5. **AC-05 (Auto-Cancellation)**: Updating an application to `rejected`, `hired`, or `withdrawn` immediately updates any future interviews with status `scheduled` to `cancelled`.
6. **AC-06 (Recruiter Data Boundary)**: A recruiter accessing `/recruiter/job/<id>/applicants` for a job requisition owned by another recruiter is redirected with a "Job not found" message.
7. **AC-07 (Audit Completeness)**: Every role update, company status toggle, application withdrawal, and interview cancellation records a corresponding row in `audit_logs`.
