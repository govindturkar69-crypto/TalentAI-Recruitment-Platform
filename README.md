<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=32&pause=1000&color=6366F1&center=true&vCenter=true&width=650&lines=%F0%9F%A4%96+TalentAI;AI-Powered+Recruitment+Platform;Smart+Hiring+for+Modern+Teams" alt="TalentAI" />

<br/>

### Automate your entire hiring pipeline with AI — parse resumes, extract skills, score candidates, and rank them instantly.

<br/>

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.4-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)

<br/>

[![Live Demo](https://img.shields.io/badge/🚀_LIVE_DEMO-Click_Here-22c55e?style=for-the-badge)](https://talentai-recruitment-platform.onrender.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br/>

**[🌐 Live Demo](#-live-demo) · [✨ Features](#-features) · [⚙️ Setup](#%EF%B8%8F-installation) · [📬 Contact](#-contact)**

</div>

---

## 🌐 Live Demo

> ### 🔗 **[https://talentai-recruitment-platform.onrender.com](https://talentai-recruitment-platform.onrender.com)**

Register with any email to explore as a **Candidate**. The **Recruiter** dashboard is restricted to the admin account only, keeping the platform secure and realistic.

> ⏳ **Note:** The app is hosted on a free tier, so the first load after a period of inactivity may take 30–50 seconds while the server wakes up. Subsequent loads are instant.

---

## 📖 About The Project

Hiring teams waste countless hours manually screening **hundreds of resumes** — a process that's slow, biased, and error-prone. **TalentAI** solves this by using **AI and Machine Learning** to automatically read resumes, extract skills, and score every candidate against a job's requirements — surfacing the best-fit people in seconds.

The platform has two sides:
- **Candidates** upload their resume, get AI-matched to jobs, and track applications in real time.
- **Recruiters** post jobs and receive an automatically ranked list of applicants, complete with match scores, analytics, and Excel export.



## ✨ Features

### 👤 For Candidates
- 📄 **Resume Upload** — drag & drop PDF, AI extracts skills automatically
- 🎯 **Smart Apply** — instant AI match score when applying to any job
- ⭐ **AI Job Recommendations** — best-fit jobs ranked by resume match %
- 🔖 **Saved Jobs** — bookmark jobs to apply later
- ↩️ **Withdraw Applications** — cancel anytime (except hired)
- 👤 **Profile Page** — bio, experience, LinkedIn / GitHub / portfolio links
- 🔔 **Real-time Notifications** — get alerts on shortlist / rejection / hire
- 🔍 **Search & Filter** — find jobs by title, location, or skill

### 🏢 For Recruiters (Admin Only)
- 💼 **Post & Manage Jobs** — create, edit, close, reopen, or delete listings
- 🏆 **AI-Ranked Candidates** — applicants auto-sorted by match score
- ☑️ **Bulk Actions** — shortlist / reject / hire multiple candidates at once
- 📥 **Export to Excel** — download the full applicant list as `.xlsx`
- 📊 **Analytics Dashboard** — 5 interactive charts (skill demand, scores, trends)
- 🔔 **Application Alerts** — notified instantly when someone applies

### 🤖 AI / ML Engine
- 📑 **PDF Parsing** — extracts raw text from resumes (PyPDF2)
- 🧠 **Skill Extraction** — matches against a 50+ skills database
- 📐 **Skill Match Score** — `matched / required × 100` (70% weight)
- 🔍 **TF-IDF Similarity** — resume vs job cosine similarity (30% weight)
- 🏅 **Final Score** — `(Skill × 0.7) + (TF-IDF × 0.3)`

### 🎨 Platform & Engineering
- 🌙 **Dark Mode** — full dark theme with smooth transitions
- 🔐 **Admin-Only Recruiter** — only the admin email can be a recruiter
- 🔑 **Forgot Password** — secure token-based password reset
- 🛡️ **Secure Config** — all secrets stored in environment variables
- ⚡ **Connection Pooling** — reused DB connections instead of opening a new one per request
- 🗂️ **Database Indexes** — indexed columns on all frequently queried fields
- ❤️ **Health Check** — `/healthz` endpoint for uptime monitoring

---

## 📊 How The Scoring Works

```python
# Skill Match (70% weight)
skill_score = len(matched_skills) / len(required_skills) * 100

# TF-IDF Cosine Similarity (30% weight)
tfidf_score = cosine_similarity(resume_text, job_description) * 100

# Final Score
final_score = (skill_score * 0.70) + (tfidf_score * 0.30)
```

**Example:**
```
Job requires : python, flask, mysql, javascript, html   →  5 skills
Resume has   : python, mysql, html, react               →  3 matched

Skill Score  = 3/5 × 100          = 60.0%
TF-IDF Score = (auto-calculated)   = 45.0%
Final Score  = (60×0.7)+(45×0.3)   = 55.5%   →  ⚠️ Review
```

| Score | Decision |
|:-----:|:--------:|
| ≥ 75% | ✅ Shortlist |
| 50–74% | ⚠️ Review |
| < 50% | ❌ Reject |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.13, Flask, PyMySQL |
| **Database** | MySQL 8.4 (hosted on Aiven) |
| **Connection Pool** | DBUtils `PooledDB` |
| **AI / ML** | scikit-learn (TF-IDF + Cosine Similarity), PyPDF2 |
| **Analytics** | Plotly, Pandas |
| **Frontend** | Bootstrap 5.3, Vanilla JavaScript |
| **Auth** | Werkzeug (password hashing), Flask sessions |
| **Export** | openpyxl (Excel) |
| **Deployment** | Render (web service) + Aiven (MySQL), Gunicorn |
| **Security** | python-dotenv (.env for secrets), SSL DB connection |

---

## 📁 Project Structure

```
TalentAI/
├── app.py                     # Main Flask app (30 routes)
├── requirements.txt           # Python dependencies
├── Procfile                   # Deployment start command
├── runtime.txt                # Python version
├── .env.example               # Environment variable template
├── .gitignore
│
├── models/
│   └── resume_parser.py       # PDF parsing + skill extraction + scoring
├── analytics/
│   └── dashboard.py           # 5 Plotly chart generators
├── database/
│   └── schema.sql             # 8 MySQL tables
│
├── templates/                 # 17 Jinja2 HTML templates
│   ├── base.html              # Navbar, dark mode, notifications
│   ├── index.html             # Landing page
│   ├── login.html / register.html
│   ├── forgot_password.html / reset_password.html
│   ├── candidate_dashboard.html
│   ├── candidate_profile.html
│   ├── upload_resume.html
│   ├── job_recommendations.html
│   ├── saved_jobs.html
│   ├── notifications.html
│   ├── recruiter_dashboard.html
│   ├── post_job.html / edit_job.html
│   ├── view_applicants.html
│   └── analytics.html
│
├── static/
│   ├── css/style.css          # Dark mode + animations
│   └── js/main.js             # Theme toggle + filters
└── uploads/                   # Uploaded resumes
```

---

## ⚙️ Installation

### Prerequisites
- Python 3.11+
- MySQL 8.0+

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/govindturkar69-crypto/TalentAI-Recruitment-Platform.git
cd TalentAI-Recruitment-Platform

# 2. Create & activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate      # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your MySQL credentials

# 5. Create the database
mysql -u root -p < database/schema.sql

# 6. Run the app
python app.py
```

Open **http://localhost:5000** in your browser.

### Environment Variables (`.env`)
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=recruitment_db
MYSQL_SSL=False
FLASK_SECRET_KEY=your_random_secret_key
FLASK_DEBUG=True
```

---

## 🗃️ Database Schema

| Table | Purpose |
|-------|---------|
| `users` | Candidates + Recruiters (role-based) |
| `jobs` | Job listings (with active/closed flag) |
| `resumes` | Uploaded PDFs + extracted skills |
| `applications` | Candidate ↔ Job links (score, status) |
| `candidate_profiles` | Bio, contact, social links |
| `notifications` | Real-time alerts |
| `saved_jobs` | Bookmarked jobs |
| `password_resets` | Secure reset tokens |

Indexed columns: `users.email`, `applications.candidate_id`, `applications.job_id`, `applications.status`, `jobs.recruiter_id`, `jobs.is_active`, `resumes.user_id`, `saved_jobs.candidate_id`, `notifications(user_id, is_read)`, `password_resets.token`.

---

## 🚀 Deployment

The app runs on a **fully free stack** — Render for the web service, Aiven for managed MySQL.

### 1. Database — Aiven
- Create a free MySQL service at [aiven.io](https://aiven.io)
- Run `database/schema.sql` to create the 8 tables
- Note the host, port, user, password, and database name

### 2. Web Service — Render
- Create a new **Web Service** at [render.com](https://render.com) and connect the GitHub repo
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Instance Type:** Free

### 3. Environment Variables on Render
```
MYSQL_HOST       = <your-aiven-host>.aivencloud.com
MYSQL_PORT       = <your-aiven-port>
MYSQL_USER       = avnadmin
MYSQL_PASSWORD   = <your-aiven-password>
MYSQL_DB         = <your-database-name>
MYSQL_SSL        = True
FLASK_SECRET_KEY = <random-secret-string>
FLASK_DEBUG      = False

### 4. Password Reset Email Configuration (Resend)
To enable production password-reset email delivery:
1. Verify your sender domain in [Resend](https://resend.com).
2. Generate an API Key in the Resend dashboard.
3. Configure the following environment variables in Render:
```env
RESEND_API_KEY   = <your-real-resend-api-key>
MAIL_FROM        = <verified-sender-email-address>
APP_BASE_URL     = https://talentai-recruitment-platform.onrender.com
```
*Note: The real `RESEND_API_KEY` must never be committed to GitHub or added to `.env.example`. Ensure `APP_BASE_URL` exactly matches your production URL.*

> Aiven requires an SSL connection, which is why `MYSQL_SSL=True` is needed in production.

---

## 🗺️ Roadmap

- [x] AI resume parsing & skill extraction
- [x] Smart scoring (Skill Match + TF-IDF)
- [x] Automatic candidate ranking
- [x] Job posting & management (edit / close / delete)
- [x] Application tracking & withdrawal
- [x] Real-time notifications
- [x] Analytics dashboard (5 charts)
- [x] Candidate profile page
- [x] AI job recommendations
- [x] Saved / bookmarked jobs
- [x] Bulk status actions
- [x] Export applicants to Excel
- [x] Forgot password (token-based)
- [x] Dark mode
- [x] Search & filter jobs
- [x] Admin-only recruiter access
- [x] Database connection pooling & indexes
- [x] Health-check endpoint
- [x] Deployed live on Render + Aiven
- [ ] Email notifications (SMTP)
- [ ] Full UI redesign with a unified design system
- [ ] Admin panel for user management
- [ ] Resume improvement AI suggestions

---

## 📬 Contact

<div align="center">

**Govind Turkar**

[![GitHub](https://img.shields.io/badge/GitHub-govindturkar69--crypto-181717?style=for-the-badge&logo=github)](https://github.com/govindturkar69-crypto)
[![Email](https://img.shields.io/badge/Email-govindturkar45@gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:govindturkar45@gmail.com)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/yourprofile)

</div>

---

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and distribute.

---

<div align="center">

### ⭐ If you found this project helpful, please give it a star!

<img src="https://capsule-render.vercel.app/api?type=waving&color=6366f1&height=120&section=footer&text=Thanks%20for%20visiting!&fontSize=24&fontColor=ffffff" width="100%" />

</div>

## 🛠️ Continuous Integration (CI)

This project uses **GitHub Actions** for Continuous Integration (CI). 

Whenever you push to the repository or open a Pull Request, the CI pipeline automatically runs:
1. **Syntax Validation**: Uses `compileall` to check all Python source files.
2. **Automated Tests**: Runs the `pytest` suite to verify business logic and workflows without connecting to a real database.


### Running CI Checks Locally

Before pushing your code, you can run the same validation steps locally:

**1. Install Development Dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**2. Run Ruff (Linter)**
```bash
ruff check .
# To automatically fix safe violations: ruff check --fix .
```

**3. Run Black (Formatter)**
```bash
black --check .
# To automatically format: black .
```

**4. Run Syntax Validation**
```bash
python -m compileall -q app.py core.py config.py routes/ services/ models/
```

**5. Run Pytest**
```bash
pytest -v tests/
```


## 5. Production Monitoring

This application supports optional error tracking via **Sentry**.

### Health Check
A lightweight health endpoint is available at `/healthz`. It performs a fast `SELECT 1` query to verify database connectivity.
- **Healthy:** HTTP `200 OK`
- **Unhealthy:** HTTP `503 Service Unavailable`

### Error Tracking
To enable Sentry error tracking in your deployed environment, configure the following environment variable:
```bash
# Provide your actual Sentry DSN from your Sentry project settings
SENTRY_DSN=https://your-dsn@sentry.io/project
```
- If `SENTRY_DSN` is empty or missing, error tracking remains completely disabled.
- Tracebacks and sensitive PII (like cookies/headers) are scrubbed automatically.

### Logs
Structured console logging includes request paths, methods, and user IDs (when available).

## 6. Production Database Backup & Recovery

The production database is hosted on **Aiven Cloud**. 

### Managed Automated Backups
Aiven provides native, fully automated daily backups and continuous Point-in-Time Recovery (PITR). 
> **Action Required**: The project maintainer must verify within the Aiven Console that automated backups and PITR are actively enabled and configured for the correct retention period.

### Recovery Strategy
To ensure production safety during a disaster recovery scenario:
1. **Never restore directly over the live production database.**
2. Use the Aiven Console to restore the backup to a **new, forked staging database**.
3. Verify data integrity and application compatibility against the staging database.
4. Only after successful verification, update the `MYSQL_HOST` environment variable in the production deployment (Render) to point to the newly restored database.

*Note: No manual backup scripts or backup endpoints are included in the application code to prevent unauthorized access and data exposure.*

## 7. Production Deployment Checklist

Before taking the application live, verify the following:

- [ ] **Environment Variables**: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `FLASK_SECRET_KEY` are all set.
- [ ] **Debug Mode Disabled**: `FLASK_DEBUG=False` is set.
- [ ] **Aiven Database Configuration**: Ensure the database is accessible and `MYSQL_SSL=True` is enabled.
- [ ] **Render Deployment**: Confirm `gunicorn app:app` is configured as the start command.
- [ ] **Health Check**: Verify `/healthz` returns HTTP 200 OK.
- [ ] **Sentry Configuration**: Ensure `SENTRY_DSN` is correctly configured in production for error tracking.
- [ ] **Admin Email**: `ADMIN_EMAIL` is configured to the correct recruiter email.
- [ ] **CI Status**: Verify all GitHub Actions (Ruff, Black, Pytest) are passing.
- [ ] **Backups**: Confirm in the Aiven Console that automated backups and PITR are actively running.
- [ ] **Security Smoke Test**: Manually verify that `/api/jobs` rejects anonymous users and candidate features function properly.

---
```