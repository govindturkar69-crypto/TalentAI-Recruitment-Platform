# Route and API Documentation

## Documentation Basis

- Repository branch: `main`
- Repository HEAD: `891d7ac4947d7a4153d2da7389aabdaf116e3b52`
- Release snapshot: `v1.0.0`
- Analysis method: Static repository inspection
- Runtime verification: Present but not runtime-verified (documentation-only analysis)
- Generated/updated: `2026-09-11`

---

## API Style Overview

TalentAI implements a **mixed routing architecture**:
1. **Server-Rendered Routes (Jinja2 HTML)**: The primary mechanism for user interaction. Form submissions use standard HTTP POST encoding (`application/x-www-form-urlencoded` or `multipart/form-data`) with CSRF token validation, returning HTML views or HTTP 302 redirects accompanied by Flask session flash messages.
2. **JSON REST Endpoints**: Targeted endpoints delivering JSON payloads for operational monitoring (`/healthz`), system data feeds (`/api/jobs`), candidate self-service scoring (`/api/candidate/<id>/score`), and client-side resume analysis (`/api/resume/score_local`, `/api/resume/analyze`).
3. **Binary File Delivery**: Endpoints serving binary file attachments, including generated Excel spreadsheets (`/recruiter/job/<id>/export`) and stored PDF resumes (`/recruiter/application/<id>/resume`).

---

## Authentication Requirements

- **Session-Based Authentication**: Routes requiring authentication read `session["user_id"]`. Unauthenticated requests to protected endpoints receive HTTP 302 redirects to `/login`.
- **CSRF Token Requirement**: All state-modifying POST requests require a valid `csrf_token` in form data or headers (`X-CSRFToken`), enforced universally by Flask-WTF.

---

## Authorization Model

- **Public**: Accessible without login (`/`, `/login`, `/register`, `/forgot_password`, `/reset_password/<token>`, `/healthz`).
- **Candidate-Only**: Enforced via `@login_required(role="candidate")`. Access granted only if `session.get("role") == "candidate"`.
- **Recruiter-Only**: Enforced via `@login_required(role="recruiter")`. Access granted only if `session.get("role") == "recruiter"`.
- **Admin-Only**: Enforced via `@admin_required`. Access granted only if `session.get("user_id")` is present, `is_active == TRUE`, and the user's email matches `Config.ADMIN_EMAIL`.
- **Resource Ownership**:
  - Candidates may only query their own score, edit their own profile, or withdraw their own applications.
  - Recruiters may only view, edit, update status, export, or schedule interviews for job requisitions they posted (`jobs.recruiter_id == session["user_id"]`).

---

## Endpoint / Route Reference

### 1. Authentication & Account Management (`routes/auth.py`, `app.py`)

#### `GET /register` & `POST /register`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/register` |
| **Purpose** | Render candidate registration form and register new candidate account |
| **Authentication** | Public (Rate limited: 5/hour) |
| **Authorization** | Anonymous |
| **Inputs** | Form: `name` (str), `email` (str), `password` (str) |
| **Validation** | All fields required; password $\ge 8$ chars; email $\ne$ `ADMIN_EMAIL`; unique email |
| **Response** | `GET`: 200 HTML (`register.html`); `POST`: 302 Redirect to `/login` |
| **Side Effects** | Inserts record into `users` table with role `'candidate'` |

#### `GET /login` & `POST /login`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/login` |
| **Purpose** | Authenticate user credentials and establish session |
| **Authentication** | Public (Rate limited: 5/minute) |
| **Authorization** | Anonymous |
| **Inputs** | Form: `email` (str), `password` (str) |
| **Validation** | Email and password required; account must have `is_active = TRUE` |
| **Response** | `GET`: 200 HTML (`login.html`); `POST`: 302 Redirect to role dashboard |
| **Side Effects** | Clears previous session, populates `user_id`, `name`, `role`, `is_admin` in session |

#### `POST /logout`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/logout` |
| **Purpose** | Terminate authenticated session |
| **Authentication** | Authenticated |
| **Authorization** | Any logged-in user |
| **Inputs** | Form: `csrf_token` |
| **Validation** | CSRF token required |
| **Response** | 302 Redirect to `/login` |
| **Side Effects** | Clears session cookie (`session.clear()`) |

#### `GET /forgot_password` & `POST /forgot_password`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/forgot_password` |
| **Purpose** | Initiate password reset workflow |
| **Authentication** | Public (Rate limited: 3/hour) |
| **Authorization** | Anonymous |
| **Inputs** | Form: `email` (str) |
| **Validation** | Valid email format |
| **Response** | `GET`: 200 HTML (`forgot_password.html`); `POST`: 302 Redirect with uniform flash |
| **Side Effects** | Generates 32-byte token in `password_resets`; sends email via Resend API |

#### `GET /reset_password/<token>` & `POST /reset_password/<token>`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/reset_password/<token>` |
| **Purpose** | Validate reset token and update password |
| **Authentication** | Public |
| **Authorization** | Possessor of valid token |
| **Inputs** | Path: `token` (str); Form: `password` (str), `confirm_password` (str) |
| **Validation** | Token exists, `used = FALSE`, `expires_at > NOW()`, passwords match, length $\ge 8$ |
| **Response** | `GET`: 200 HTML (`reset_password.html`); `POST`: 302 Redirect to `/login` |
| **Side Effects** | Updates `users.password` hash; marks token `used = TRUE`; clears session |

#### `GET /settings` & `POST /settings`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/settings` |
| **Purpose** | Authenticated password change |
| **Authentication** | `@login_required()` |
| **Authorization** | Any active user |
| **Inputs** | Form: `current_password`, `new_password`, `confirm_password` |
| **Validation** | Verification of current password; passwords match; new password $\ge 8$ chars |
| **Response** | `GET`: 200 HTML (`settings.html`); `POST`: 302 Redirect to `/login` |
| **Side Effects** | Updates `users.password`; clears session |

---

### 2. Candidate Portal (`routes/candidate.py`)

#### `GET /candidate/dashboard`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/candidate/dashboard` |
| **Purpose** | Display candidate summary dashboard |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | None |
| **Validation** | None |
| **Response** | 200 HTML (`candidate_dashboard.html`) |
| **Side Effects** | None |

#### `GET /candidate/upload_resume` & `POST /candidate/upload_resume`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/candidate/upload_resume` |
| **Purpose** | Ingest and parse candidate PDF resume |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | Form (`multipart/form-data`): `resume` (PDF file) |
| **Validation** | File present; filename ends with `.pdf`; file size $\le 5$ MB |
| **Response** | `GET`: 200 HTML (`upload_resume.html`); `POST`: 302 Redirect to dashboard |
| **Side Effects** | Saves file in `uploads/`; inserts record in `resumes` table |

#### `POST /candidate/apply/<int:job_id>`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/candidate/apply/<job_id>` |
| **Purpose** | Apply for an active job requisition |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | Path: `job_id` (int) |
| **Validation** | Candidate has resume uploaded; not previously applied; job exists and `is_active = TRUE` |
| **Response** | 302 Redirect to dashboard |
| **Side Effects** | Computes composite score; inserts row into `applications`; creates notifications |

#### `POST /candidate/withdraw/<int:app_id>`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/candidate/withdraw/<app_id>` |
| **Purpose** | Candidate self-service withdrawal from active application |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Application belongs to logged-in candidate |
| **Inputs** | Path: `app_id` (int) |
| **Validation** | Current status in `{'applied', 'shortlisted'}` |
| **Response** | 302 Redirect to dashboard |
| **Side Effects** | Updates `applications.status = 'withdrawn'`; cancels future interviews; logs audit event |

#### `POST /candidate/save_job/<int:job_id>` & `POST /candidate/unsave_job/<int:job_id>`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/candidate/save_job/<job_id>`, `/candidate/unsave_job/<job_id>` |
| **Purpose** | Bookmark or remove bookmark for a job |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | Path: `job_id` (int) |
| **Validation** | Job exists |
| **Response** | 302 Safe redirect to dashboard or saved jobs page |
| **Side Effects** | Inserts or deletes row in `saved_jobs` table |

#### `GET /candidate/saved_jobs`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/candidate/saved_jobs` |
| **Purpose** | View list of bookmarked jobs |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | None |
| **Validation** | None |
| **Response** | 200 HTML (`saved_jobs.html`) |
| **Side Effects** | None |

#### `GET /candidate/profile` & `POST /candidate/profile`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/candidate/profile` |
| **Purpose** | View profile with portfolio or update bio and contact information |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | Form: `bio`, `phone`, `location`, `experience_years`, `linkedin_url`, `github_url`, `portfolio_url` |
| **Validation** | URLs must start with `http://` or `https://` with valid hostname |
| **Response** | `GET`: 200 HTML (`candidate_profile.html`); `POST`: 302 Redirect to profile |
| **Side Effects** | Inserts or updates row in `candidate_profiles` |

#### `POST /candidate/skills/edit`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/candidate/skills/edit` |
| **Purpose** | Update candidate curated skills taxonomy |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | Form: `skills` (str) |
| **Validation** | Normalized, deduplicated, capped at 100 skills |
| **Response** | 302 Redirect to profile |
| **Side Effects** | Updates `candidate_profiles.skills` |

#### Candidate Portfolio CRUD Routes
The following endpoints manage candidate sub-entities via POST:
- `POST /candidate/education/add`, `/candidate/education/<id>/edit`, `/candidate/education/<id>/delete`
- `POST /candidate/experience/add`, `/candidate/experience/<id>/edit`, `/candidate/experience/<id>/delete`
- `POST /candidate/projects/add`, `/candidate/projects/<id>/edit`, `/candidate/projects/<id>/delete`
- `POST /candidate/certifications/add`, `/candidate/certifications/<id>/edit`, `/candidate/certifications/<id>/delete`
- `POST /candidate/achievements/add`, `/candidate/achievements/<id>/edit`, `/candidate/achievements/<id>/delete`
*All edit and delete endpoints enforce ownership check (`user_id == session["user_id"]`), date order checks (`start_date <= end_date`), and URL validation.*

#### `GET /candidate/jobs` & `GET /candidate/job/<int:job_id>`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/candidate/jobs`, `/candidate/job/<job_id>` |
| **Purpose** | Search listings or view requisition details with skill match analysis |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | Query: `keyword`, `location`; Path: `job_id` (int) |
| **Validation** | Inactive jobs blocked unless already applied |
| **Response** | 200 HTML (`candidate_jobs.html` / `candidate_job_details.html`) |
| **Side Effects** | None |

#### `GET /candidate/applications`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/candidate/applications` |
| **Purpose** | Real-time tracking of candidate's submitted applications |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | None |
| **Validation** | None |
| **Response** | 200 HTML (`candidate_applications.html`) |
| **Side Effects** | None |

#### `GET /candidate/interviews`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/candidate/interviews` |
| **Purpose** | View scheduled, completed, and cancelled interviews |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | None |
| **Validation** | None |
| **Response** | 200 HTML (`candidate_interviews.html`) |
| **Side Effects** | None |

#### `GET /candidate/recommendations`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/candidate/recommendations` |
| **Purpose** | View recommended jobs based on skill overlap |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | None |
| **Validation** | None |
| **Response** | 200 HTML (`job_recommendations.html`) |
| **Side Effects** | None |

#### `POST /api/resume/score_local`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/resume/score_local` |
| **Purpose** | Deterministic local match scoring for a target job |
| **Authentication** | `@login_required(role="candidate")` |
| **Authorization** | Candidate role |
| **Inputs** | JSON: `job_id` (optional int) |
| **Validation** | Valid job ID if provided; candidate has uploaded resume |
| **Response** | 200 JSON: `{"success": true, "mode": str, "match_score": float, ...}` |
| **Side Effects** | None |

#### `POST /api/resume/analyze`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/resume/analyze` |
| **Purpose** | Request advisory OpenAI Structured Outputs resume suggestions |
| **Authentication** | `@login_required(role="candidate")` (Rate limited: 3/day) |
| **Authorization** | Candidate role |
| **Inputs** | JSON: `job_id` (optional int) |
| **Validation** | Valid job ID if provided; PII sanitized |
| **Response** | 200 JSON: structured suggestion payload matching `AIResumeSuggestions` |
| **Side Effects** | Calls external OpenAI API (if configured) |

---

### 3. Recruiter Pipeline (`routes/recruiter.py`)

#### `GET /recruiter/dashboard`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/recruiter/dashboard` |
| **Purpose** | Display recruiter overview and posted jobs |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Recruiter role |
| **Inputs** | None |
| **Validation** | None |
| **Response** | 200 HTML (`recruiter_dashboard.html`) |
| **Side Effects** | None |

#### `GET /recruiter/post_job` & `POST /recruiter/post_job`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/recruiter/post_job` |
| **Purpose** | Create a new job requisition |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Recruiter role |
| **Inputs** | Form: `job_title`, `required_skills`, `description`, `location`, `experience` |
| **Validation** | Title and required skills are mandatory |
| **Response** | `GET`: 200 HTML (`post_job.html`); `POST`: 302 Redirect to dashboard |
| **Side Effects** | Inserts row into `jobs` table |

#### `GET /recruiter/job/<int:job_id>/edit` & `POST /recruiter/job/<int:job_id>/edit`
| Field | Details |
|---|---|
| **Method** | `GET`, `POST` |
| **Path** | `/recruiter/job/<job_id>/edit` |
| **Purpose** | Modify existing job requisition |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Job belongs to logged-in recruiter |
| **Inputs** | Form: `job_title`, `required_skills`, `description`, `location`, `experience` |
| **Validation** | Ownership verified; title and skills mandatory |
| **Response** | `GET`: 200 HTML (`edit_job.html`); `POST`: 302 Redirect to dashboard |
| **Side Effects** | Updates row in `jobs` table |

#### `POST /recruiter/job/<int:job_id>/toggle_active`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/recruiter/job/<job_id>/toggle_active` |
| **Purpose** | Toggle job active status (`is_active = not is_active`) |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Job belongs to logged-in recruiter |
| **Inputs** | Path: `job_id` (int) |
| **Validation** | Ownership verified |
| **Response** | 302 Redirect to dashboard |
| **Side Effects** | Inverts boolean `jobs.is_active` |

#### `POST /recruiter/job/<int:job_id>/delete`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/recruiter/job/<job_id>/delete` |
| **Purpose** | Permanently remove job requisition |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Job belongs to logged-in recruiter |
| **Inputs** | Path: `job_id` (int) |
| **Validation** | Ownership verified |
| **Response** | 302 Redirect to dashboard |
| **Side Effects** | Deletes row from `jobs` (cascades to applications) |

#### `GET /recruiter/job/<int:job_id>/applicants`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/recruiter/job/<job_id>/applicants` |
| **Purpose** | View ranked candidate roster for a requisition |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Job belongs to logged-in recruiter |
| **Inputs** | Query: `q` (name/email search), `status` (filter) |
| **Validation** | Ownership verified |
| **Response** | 200 HTML (`view_applicants.html`) |
| **Side Effects** | None |

#### `POST /recruiter/applications/bulk_update`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/recruiter/applications/bulk_update` |
| **Purpose** | Batch update status for multiple selected candidates |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | All updated applications belong to jobs owned by recruiter |
| **Inputs** | Form: `selected_apps` (list of IDs), `bulk_status` (`shortlisted`, `rejected`, `hired`), `job_id` |
| **Validation** | Target status in allowed set; state machine transitions valid |
| **Response** | 302 Redirect to applicant list |
| **Side Effects** | Updates `applications.status`; auto-cancels interviews on terminal status; logs audit events |

#### `GET /recruiter/job/<int:job_id>/export`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/recruiter/job/<job_id>/export` |
| **Purpose** | Export ranked applicant roster to Excel |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Job belongs to logged-in recruiter |
| **Inputs** | Path: `job_id` (int) |
| **Validation** | Ownership verified |
| **Response** | 200 Binary: `.xlsx` file download via `send_file` |
| **Side Effects** | None |

#### `POST /recruiter/application/<int:app_id>/status`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/recruiter/application/<app_id>/status` |
| **Purpose** | Single applicant status transition |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Application belongs to job owned by recruiter |
| **Inputs** | Path: `app_id` (int); Form: `status` (str) |
| **Validation** | Valid transition in `RECRUITER_TRANSITIONS` |
| **Response** | 302 Safe redirect to dashboard |
| **Side Effects** | Updates `applications.status`; auto-cancels future interviews if rejected/hired; logs audit event |

#### `GET /recruiter/application/<int:app_id>/candidate` & `GET /recruiter/application/<int:app_id>/resume`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/recruiter/application/<app_id>/candidate`, `/recruiter/application/<app_id>/resume` |
| **Purpose** | View candidate profile portfolio or stream uploaded PDF resume |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Application belongs to job owned by recruiter |
| **Inputs** | Path: `app_id` (int) |
| **Validation** | Path traversal check verifies resume is strictly within `UPLOAD_FOLDER` |
| **Response** | 200 HTML (`recruiter_candidate_profile.html`) or 200 PDF stream |
| **Side Effects** | None |

#### Recruiter Interview Endpoints
- `GET /recruiter/application/<app_id>/interviews`: Render interview hub (`recruiter_interviews.html`).
- `POST /recruiter/application/<app_id>/interviews/schedule`: Schedule new round (requires `shortlisted` status, future date/time, duration 5–480 mins).
- `POST /recruiter/interview/<interview_id>/update`: Reschedule/edit details for scheduled interview.
- `POST /recruiter/interview/<interview_id>/cancel`: Cancel scheduled interview.
- `POST /recruiter/interview/<interview_id>/complete`: Mark scheduled interview as completed (only after scheduled time has passed).

---

### 4. Admin Console (`routes/admin.py`)

#### `GET /admin/dashboard`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/admin/dashboard` |
| **Purpose** | Operational metrics and server-side paginated user management |
| **Authentication** | `@admin_required` |
| **Authorization** | Admin only (`email == ADMIN_EMAIL`) |
| **Inputs** | Query: `q` (name/email search), `role` (`candidate`/`recruiter`), `status` (`active`/`inactive`), `company_id`, `page`, `per_page` |
| **Validation** | Paginated query bounds normalized |
| **Response** | 200 HTML (`admin_dashboard.html`) |
| **Side Effects** | None |

#### `POST /admin/users/<int:user_id>/role`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/admin/users/<user_id>/role` |
| **Purpose** | Update user role (`candidate` $\leftrightarrow$ `recruiter`) |
| **Authentication** | `@admin_required` |
| **Authorization** | Admin only; self-mutation forbidden (`user_id != session["user_id"]`) |
| **Inputs** | Path: `user_id` (int); Form: `role` (str) |
| **Validation** | Role in `{'candidate', 'recruiter'}`; admin cannot change own role |
| **Response** | 302 Safe redirect to dashboard |
| **Side Effects** | Updates `users.role`; logs audit event |

#### `POST /admin/users/<int:user_id>/status`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/admin/users/<user_id>/status` |
| **Purpose** | Activate or deactivate a user account |
| **Authentication** | `@admin_required` |
| **Authorization** | Admin only; self-deactivation and primary admin deactivation forbidden |
| **Inputs** | Path: `user_id` (int); Form: `status` (`active`/`inactive`) |
| **Validation** | Target is not logged-in admin; target email $\ne$ `ADMIN_EMAIL` |
| **Response** | 302 Safe redirect to dashboard |
| **Side Effects** | Updates `users.is_active`; logs audit event |

#### `POST /admin/users/<int:user_id>/company`
| Field | Details |
|---|---|
| **Method** | `POST` |
| **Path** | `/admin/users/<user_id>/company` |
| **Purpose** | Assign recruiter to a tenant company |
| **Authentication** | `@admin_required` |
| **Authorization** | Admin only |
| **Inputs** | Path: `user_id` (int); Form: `company_id` (optional int) |
| **Validation** | Target user must have `role == 'recruiter'`; target company must be active |
| **Response** | 302 Safe redirect to dashboard |
| **Side Effects** | Updates `users.company_id`; logs audit event |

#### `GET /admin/companies`, `POST /admin/companies/create`, `/admin/companies/<id>/edit`, `/admin/companies/<id>/status`
- `GET /admin/companies`: Server-side paginated list of client companies (`admin_companies.html`).
- `POST /admin/companies/create`: Create company with name, description, website URL.
- `POST /admin/companies/<company_id>/edit`: Update company name, description, website URL.
- `POST /admin/companies/<company_id>/status`: Toggle company active status (`is_active = TRUE/FALSE`) using atomic state predicate.

#### `GET /admin/audit-logs`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/admin/audit-logs` |
| **Purpose** | Search and inspect immutable audit trail |
| **Authentication** | `@admin_required` |
| **Authorization** | Admin only |
| **Inputs** | Query: `action`, `target_type`, `actor`, `date_from`, `date_to`, `page`, `per_page` |
| **Validation** | Date order validation (`date_from <= date_to`) |
| **Response** | 200 HTML (`admin_audit_logs.html`) |
| **Side Effects** | None |

---

### 5. Analytics & Notifications (`routes/analytics.py`, `app.py`)

#### `GET /recruiter/analytics`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/recruiter/analytics` |
| **Purpose** | View interactive recruitment dashboards and Plotly charts |
| **Authentication** | `@login_required(role="recruiter")` |
| **Authorization** | Recruiter role |
| **Inputs** | None |
| **Validation** | None |
| **Response** | 200 HTML (`analytics.html`) |
| **Side Effects** | None |

#### `GET /notifications` & `POST /notifications/mark_all_read`
- `GET /notifications`: View latest 50 notifications for authenticated user (`notifications.html`).
- `POST /notifications/mark_all_read`: Update all user notifications to `is_read = TRUE`.

---

### 6. Public & Health / System Routes (`app.py`)

#### `GET /`
- Renders public landing page (`templates/index.html`).

#### `GET /healthz`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/healthz` |
| **Purpose** | Liveness and database connectivity health probe |
| **Authentication** | Public |
| **Authorization** | Anonymous |
| **Inputs** | None |
| **Validation** | Executes `SELECT 1` against MySQL connection pool |
| **Response** | 200 JSON `{"status": "ok", "database": "connected"}` or 503 JSON `{"status": "error", "database": "unreachable"}` |
| **Side Effects** | None |

#### `GET /api/jobs`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/jobs` |
| **Purpose** | JSON feed of all currently active jobs |
| **Authentication** | `@login_required()` |
| **Authorization** | Any authenticated user |
| **Inputs** | None |
| **Validation** | Filters strictly by `is_active = TRUE` |
| **Response** | 200 JSON list of job dictionaries |
| **Side Effects** | None |

#### `GET /api/candidate/<int:user_id>/score`
| Field | Details |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/candidate/<user_id>/score` |
| **Purpose** | Fetch application scores for a candidate |
| **Authentication** | `@login_required()` |
| **Authorization** | Candidates can only access their own score (`session["user_id"] == user_id`); Recruiters/Admin can access any |
| **Inputs** | Path: `user_id` (int) |
| **Validation** | Returns 404 JSON if candidate attempts to query another user's score |
| **Response** | 200 JSON list: `[{"score": float, "job_title": str}]` |
| **Side Effects** | None |
