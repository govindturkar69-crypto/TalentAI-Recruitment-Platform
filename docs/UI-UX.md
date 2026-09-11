# UI / UX Documentation

## Documentation Basis

- Repository branch: `main`
- Repository HEAD: `891d7ac4947d7a4153d2da7389aabdaf116e3b52`
- Release snapshot: `v1.0.0`
- Analysis method: Static repository inspection
- Runtime verification: Present but not runtime-verified (documentation-only analysis)
- Generated/updated: `2026-09-11`

---

## Design Overview

TalentAI features an **Enterprise SaaS** visual design system defined in `static/css/style.css` and augmented by `auth.css` and `landing.css`. The design is built on Bootstrap 5.3 and Bootstrap Icons, layered with custom CSS variables (tokens) that provide a cohesive aesthetic in both light and dark themes. The UI emphasizes clarity, typography, information hierarchy, responsive containment with zero horizontal overflow, and contextual action triggers.

---

## Navigation Model

The primary navigation resides in a fixed-top responsive navigation bar (`templates/base.html`):
- **Brand**: Displays the robot icon (`bi-robot`) and platform name `TalentAI`, linking to the root landing page (`/`).
- **Contextual Role Links**:
  - *Anonymous / Logged Out*: Links to **Login** (`/login`) and **Register** (`/register`).
  - *Candidate*: Links to **Dashboard** (`/candidate/dashboard`), **Profile** (`/candidate/profile`), **Resume** (`/candidate/upload_resume`), **Jobs** (`/candidate/jobs`), **Applications** (`/candidate/applications`), **Interviews** (`/candidate/interviews`), and **AI Suggestions** (`/candidate/resume_suggestions`).
  - *Recruiter*: Links to **Dashboard** (`/recruiter/dashboard`), **Post Job** (`/recruiter/post_job`), and **Analytics** (`/analytics/analytics`).
  - *Admin*: Replaces standard links with a prominent **Admin Console** link (`/admin/dashboard`).
- **Utility Items (Navbar Right)**:
  - **Notification Bell**: Shows unread count badge (displaying counts up to `9+`), linking to `/notifications`.
  - **Theme Toggle Button**: Switches between light and dark modes instantly.
  - **User Pill**: Displays the user's name or email, an account settings gear icon (`/settings`), and a POST-based logout trigger with CSRF token.

---

## Role-Specific Interfaces

### 1. Candidate Interface
- **Primary Dashboard (`candidate_dashboard.html`)**: Features an introductory hero greeting, stats cards for active applications, saved jobs count, and uploaded resume status; contains quick-action buttons for uploading a resume, browsing jobs, or viewing recommendations.
- **Profile Hub (`candidate_profile.html`)**: Rich tabbed or modular layout displaying candidate contact details, profile completion percentage bar, curated skills editor, and CRUD sections for Education, Experience, Projects, Certifications, and Achievements.
- **Job Details View (`candidate_job_details.html`)**: Comprehensive requisition viewer highlighting company name, location, experience requirements, description, and an automated match box breaking down matched vs. missing skills.

### 2. Recruiter Interface
- **Recruiter Dashboard (`recruiter_dashboard.html`)**: Displays operational counters (total candidates, total applications, shortlisted count) and an active job requisition table with quick toggles to close/reopen, edit, view applicants, or delete jobs.
- **Applicant Ranking Board (`view_applicants.html`)**: Candidate evaluation roster ranked in descending order of composite score. Features a multi-select checkbox column for batch status updates (`shortlisted`, `rejected`, `hired`), candidate filter search bar, status dropdown, and Excel export button.
- **Interview Coordination Hub (`recruiter_interviews.html`)**: Dedicated schedule manager for an application showing historical, upcoming, and completed rounds, with modals to schedule new interviews, edit logistics, or cancel rounds.

### 3. Administrator Interface
- **Admin Console (`admin_dashboard.html`)**: High-level platform telemetry grid (Total Users, Active Jobs, Total Applications, Total Interviews, Active Companies) and server-side paginated user management table. Each row includes exactly one focused "Actions" dropdown button to open dedicated mutation modals.
- **Tenant Management (`admin_companies.html`)**: List of organizations with recruiter headcount indicators, creation modal, editing modal, and active/inactive status toggle buttons.
- **Compliance Audit Viewer (`admin_audit_logs.html`)**: Chronological audit stream featuring actor avatar circles, system actor indicators, action badges, target pills, formatted key-value event detail drawers, and date range filters.

---

## Pages / Screens

| Page / Template | Route / URL | Core UI Components |
|---|---|---|
| **Landing Page** (`index.html`) | `GET /` | Hero banner, feature highlights grid, role CTA buttons, live platform stats. |
| **Registration** (`register.html`) | `GET /register` | Split-screen auth layout, candidate signup form, client password strength meter. |
| **Login** (`login.html`) | `GET /login` | Split-screen auth card, email/password inputs, forgot password link. |
| **Forgot Password** (`forgot_password.html`) | `GET /forgot_password` | Email input card, instructions, back to login link. |
| **Reset Password** (`reset_password.html`) | `GET /reset_password/<token>` | Password & confirmation inputs, password complexity hints. |
| **Account Settings** (`settings.html`) | `GET /settings` | Current password, new password, and confirmation form. |
| **Candidate Dashboard** (`candidate_dashboard.html`)| `GET /candidate/dashboard` | Metric summary cards, resume status card, active applications table, saved jobs list. |
| **Upload Resume** (`upload_resume.html`) | `GET /candidate/upload_resume` | Drag-and-drop styled file upload box, format restrictions note (`.pdf`, $\le 5$ MB). |
| **Candidate Profile** (`candidate_profile.html`) | `GET /candidate/profile` | Completion meter, bio form, portfolio CRUD tables with modal editors. |
| **Job Search** (`candidate_jobs.html`) | `GET /candidate/jobs` | Search toolbar (keyword, location), job cards grid, match tags, bookmark icon. |
| **Job Details** (`candidate_job_details.html`) | `GET /candidate/job/<id>` | Full description, company info, match analysis breakdown card, apply button. |
| **Candidate Applications** (`candidate_applications.html`)| `GET /candidate/applications` | Application status cards, stage badges, withdrawal trigger. |
| **Candidate Interviews** (`candidate_interviews.html`)| `GET /candidate/interviews` | Chronological interview list, mode badges, meeting links, status indicators. |
| **Recruiter Dashboard** (`recruiter_dashboard.html`)| `GET /recruiter/dashboard` | Telemetry counters, job requisition table, status pills, action buttons. |
| **Post / Edit Job** (`post_job.html`, `edit_job.html`)| `GET /recruiter/post_job`, `.../edit` | Job title, comma-separated skill tagger with live preview, description textarea. |
| **View Applicants** (`view_applicants.html`)| `GET /recruiter/job/<id>/applicants` | Ranked table, bulk action bar, score badges, candidate profile links, Excel export. |
| **Candidate Profile View** (`recruiter_candidate_profile.html`)| `GET /recruiter/application/<id>/candidate` | Read-only candidate portfolio overview, parsed skills, application metadata. |
| **Interview Manager** (`recruiter_interviews.html`)| `GET /recruiter/application/<id>/interviews` | Candidate summary, interview timeline, schedule modal, completion button. |
| **Recruiter Analytics** (`analytics.html`) | `GET /recruiter/analytics` | Plotly charts grid (skill demand, score distribution, funnel, donut). |
| **Admin Dashboard** (`admin_dashboard.html`) | `GET /admin/dashboard` | Platform metrics, unassigned recruiter alerts, paginated user table, action modals. |
| **Admin Companies** (`admin_companies.html`) | `GET /admin/companies` | Company table, recruiter count badges, create/edit modals, status toggles. |
| **Admin Audit Logs** (`admin_audit_logs.html`)| `GET /admin/audit-logs` | Filter toolbar (action, target, actor, dates), structured audit log stream. |
| **Notifications** (`notifications.html`) | `GET /notifications` | Chronological notifications list, mark all read button, unread highlights. |
| **Error 404** (`errors/404.html`) | Any unmatched URL | "Page Not Found" illustration, friendly message, return home button. |
| **Error 500** (`errors/500.html`) | Unhandled exceptions | "Something went wrong" illustration, safe error notice, return home button. |

---

## Forms

- **CSRF Token Injection**: Every form includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **Validation Styling**: Uses Bootstrap `.form-control`, `.form-select`, and `.form-check`. In case of error, invalid fields are indicated and server flash messages display error details.
- **Dynamic Tag Previews**: The job posting form (`post_job.html`) listens to inputs on `required_skills` in real time, splitting comma-separated items and rendering visual pill badges (`#skillsPreview`).

---

## Tables

- **Responsive Table Containers**: All data tables are wrapped inside `.table-responsive` to guarantee zero page-level horizontal overflow on narrow screens.
- **Alignment Conventions**:
  - Text columns (Name, Email, Title) left-aligned.
  - Numbers, Dates, and Ranks center-aligned.
  - Action buttons right-aligned.
- **Server-Side Paginated Tables**:
  - Admin User Management: 20 per page default (configurable to 50 or 100).
  - Admin Companies: 20 per page default.
  - Admin Audit Logs: 25 per page default.

---

## Modals

The administrative and recruiter portals avoid chaotic inline editing in favor of focused, accessible Bootstrap modals:
1. **Role Update Modal (`updateRoleModal`)**: Select dropdown to switch a user between `candidate` and `recruiter`.
2. **Company Assignment Modal (`assignCompanyModal`)**: Select dropdown to associate a recruiter with an active tenant company.
3. **User Status Modal (`updateStatusModal`)**: Confirmation modal to activate or deactivate a user account.
4. **Create / Edit Company Modal (`createCompanyModal`, `editCompanyModal`)**: Clean form inputs for organization name, description, and website URL.
5. **Interview Scheduling Modal (`scheduleInterviewModal`)**: Inputs for datetime, duration (mins), mode (online, in-person, phone), meeting URL/location, and notes.
6. **Portfolio Entity Modals**: Focused dialogs for adding/editing Education, Experience, Projects, Certifications, and Achievements.

---

## Actions

- **Single Action Trigger per Row**: In user management and audit tables, actions are grouped under a unified dropdown button (`bi-three-dots-vertical`), preventing horizontal crowding.
- **Bulk Pipeline Actions**: In `view_applicants.html`, recruiters select multiple candidates using checkboxes, choose an action (`Shortlist`, `Reject`, `Hire`), and click **Apply to Selected**.
- **Excel Export**: A single click on **Export to Excel** triggers an on-the-fly binary download of `.xlsx` data.

---

## User Flows

### Applicant Screening Flow
1. Recruiter opens `/recruiter/job/<id>/applicants`.
2. Candidates are automatically sorted by `score` descending.
3. Recruiter inspects match tags (`matched_skills` in green, `missing_skills` in red/gray).
4. Recruiter clicks **View Profile** to inspect full background or **Resume** to review PDF.
5. Recruiter selects status dropdown or uses bulk update bar $\rightarrow$ submits transition.

### Interview Scheduling Flow
1. From the applicant list, recruiter clicks **Schedule Interview** for a shortlisted candidate.
2. Recruiter completes modal: Date & Time, Duration, Mode (`online`), and pastes meeting URL.
3. Upon submission, system confirms date is in the future, records interview, logs audit event, and notifies candidate.
4. Candidate opens `/candidate/interviews` and sees the new round under **Upcoming Interviews** with a direct meeting link.

---

## Loading States

- **Initial Theme Loading Script**: An inline script in `<head>` executes before the DOM renders to read `localStorage.getItem('talentai_theme')` and set `document.documentElement.setAttribute('data-theme', saved)`. This completely eliminates light/dark theme flicker on page refresh.
- **Animated Match Bars**: Progress bars dynamically animate from `0%` to their target percentage on page load via JavaScript (`main.js`).

---

## Empty States

When tables or feeds have no records, styled empty state containers appear:
- **No Jobs Found**: "No active job listings match your criteria."
- **No Applications Yet**: "You haven't applied to any jobs yet." with a CTA button pointing to `/candidate/jobs`.
- **No Notifications**: Clean bell icon with "No notifications yet."
- **No Interviews**: "No interviews scheduled."

---

## Error States

- **Flash Alert System**: Flash notifications are categorized into five semantic types:
  - `success` (`saas-alert-success` with `bi-check-circle-fill`)
  - `danger` / `error` (`saas-alert-danger` with `bi-exclamation-circle-fill`)
  - `warning` (`saas-alert-warning` with `bi-exclamation-triangle-fill`)
  - `info` (`saas-alert-info` with `bi-info-circle-fill`)
  - `neutral` (`saas-alert-neutral` with `bi-bell-fill`)
- **Auto-Dismissal**: Informational alerts automatically fade after 4 seconds, with an explicit close button (`bi-x-lg`) available for immediate dismissal.

---

## Responsive Behavior

- **Mobile Viewport (390px - 768px)**:
  - Navbar collapses into a hamburger toggler.
  - Multi-column metric grids stack into a single vertical column.
  - Data tables scroll horizontally within `.table-responsive` while the outer page maintains strictly $0\text{px}$ overflow.
  - Modal dialogues adapt to 100% viewport width with touch-friendly button targets ($\ge 44\text{px}$).
- **Desktop Viewport (1024px - 1536px+)**:
  - Full horizontal navbar with role navigation.
  - Multi-card metric rows (4–5 cards per row).
  - Side-by-side forms and full table views.

---

## Theme Support

- **Light Mode (Default)**: Clean white and light gray backgrounds (`#f8fafc`, `#ffffff`), deep slate text (`#1e293b`), and indigo primary accents (`#6366f1`).
- **Dark Mode**: Activated via `data-theme="dark"` on `<html>`. Deep dark slate surfaces (`#0f172a`, `#1e293b`), crisp light text (`#f1f5f9`), subtle borders (`#334155`), and luminous primary highlights.
- **Persistence**: Stored in browser `localStorage.getItem('talentai_theme')`.

---

## Accessibility Implementation

- **Color Contrast**: Compliant foreground-to-background contrast ratios for primary text and buttons across both light and dark modes.
- **Semantic HTML**: Standard semantic landmarks (`<nav>`, `<main>`, `<footer>`, `<header>`, `<table>`).
- **Aria Attributes**: Used extensively on navigation menus (`aria-expanded`, `aria-label`), alert dismiss triggers (`aria-label="Dismiss"`), tooltips, and modal dialogues (`role="dialog"`, `aria-modal="true"`).

---

## Animations and Interactions

- **Score Bar Fill Animation**: Smooth 0.8s CSS transition filling candidate match score meters.
- **Status Change Confirmations**: Interactive confirmation dialogs triggered before marking a candidate as `hired` or `rejected`.
- **Button Hover States**: Subtle elevation and color transitions on primary action buttons.

---

## Reusable UI Patterns

- **Metric Cards (`.stat-card`)**: Uniform cards presenting a top icon, large metric number, descriptive label, and secondary trend subtitle.
- **Status Badges (`.badge`)**: Color-coded badges for application states (`applied` = blue/indigo, `shortlisted` = green, `rejected` = red, `hired` = amber, `withdrawn` = secondary gray).
- **Actor Avatars**: Circle initials or system icons utilized across audit logs to differentiate human actors from automated system events.

---

## Not Implemented / Not Observed

- **Drag-and-Drop Kanban Pipeline**: Applications are managed via tabular lists and dropdowns; an interactive drag-and-drop Kanban board is not implemented.
- **Rich Text / WYSIWYG Editor**: Job descriptions and notes use plain HTML `<textarea>` inputs; rich-text editors (e.g., TinyMCE, Quill) are not implemented.
- **Client-Side SPA Transitions**: Page transitions rely on standard multi-page application (MPA) HTTP requests and server-side rendering rather than client-side SPA routing.
