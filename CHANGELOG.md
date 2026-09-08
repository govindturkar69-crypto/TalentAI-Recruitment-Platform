# Changelog

All notable changes to the **TalentAI Recruitment Platform** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-08

### Added
- **Candidate Portal**:
  - PDF resume text extraction via `pypdf`.
  - Deterministic skill extraction matched against a curated 50+ technical skill catalog.
  - Job discovery and search with keyword, location, and active requisition filters.
  - Real-time application tracking across lifecycle states (`applied`, `shortlisted`, `rejected`, `hired`, `withdrawn`).
  - Atomic self-service application withdrawal for active submissions.
  - Persistent saved jobs bookmarking.
  - Candidate interview schedule view with date, time, duration, mode, and meeting links.
  - Candidate profile editor for bios, experience, education, and portfolio links.
- **Recruiter Pipeline**:
  - Job requisition lifecycle management (create, edit, close, reopen, delete) with company assignment.
  - Automated applicant ranking powered by composite match scores (70% skill match + 30% TF-IDF text similarity).
  - Bulk candidate processing for status transitions (shortlist, reject, hire).
  - Dedicated candidate profile viewer displaying parsed skills and uploaded resumes.
  - Integrated interview scheduling, rescheduling, logistics updates, and cancellations.
  - Formatted applicant roster export to Excel (`.xlsx`) via `openpyxl`.
  - Transactional notification badges for new applications and candidate withdrawals.
- **Interview Coordination & Automation**:
  - Centralized interview tracking for recruiters and candidates.
  - Atomic helper automatically cancelling upcoming interviews when an application reaches a terminal state (`rejected`, `hired`, or `withdrawn`).
- **Admin Console & Governance**:
  - Operational health metrics covering users, jobs, applications, interviews, and tenant companies.
  - User management interface with server-side pagination, role filtering, status filtering, and search.
  - Tenant company management (create, edit, toggle active status).
  - Recruiter-to-company assignments with candidate validation safeguards.
  - Append-only audit logging capturing administrative, security, and workflow transitions.
  - Structured semantic audit details with human-readable enum formatting.
- **Recruitment Analytics**:
  - Interactive Plotly dashboards visualising skill demand distributions, score distributions, and application conversion funnels.
- **User Interface & Theme Engine**:
  - Enterprise SaaS styling using custom CSS variables and utility classes.
  - Full dark mode theme support.
  - Responsive layouts supporting mobile (390px) to desktop (1536px) viewports with zero horizontal overflow.
- **Optional Advisory AI**:
  - Optional resume improvement suggestions powered by OpenAI Structured Outputs when an API key is configured.
- **Operational Monitoring**:
  - `/healthz` health check endpoint for uptime and database connection monitoring.

### Security
- Role-based access control (RBAC) enforced via centralized route decorators (`@login_required`, `@recruiter_required`, `@admin_required`).
- Universal CSRF token validation on state-modifying requests via Flask-WTF.
- Password hashing using Werkzeug `scrypt` with unique cryptographic salts.
- Brute-force rate limiting on authentication routes via Flask-Limiter.
- Token-based, time-limited password recovery workflow integrated with the Resend email API.
- Administrative self-protection rules preventing administrators from demoting or deactivating their own accounts.
- Guard preventing company assignment to candidate accounts before role elevation.
- 100% parameterized SQL queries through MySQL connection pooling via DBUtils `PooledDB`.
- PII redaction (emails and phone numbers) before sending resume text to optional advisory services.

### Changed
- Replaced inline table mutation controls with single, focused administrative action modals.
- Updated user management and audit log tables to responsive grid structures with verified zero horizontal overflow.
