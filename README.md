# 🤖 TalentAI — AI-Powered Recruitment & Talent Analytics Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.3.3-black?style=for-the-badge&logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?style=for-the-badge&logo=mysql)
![Plotly](https://img.shields.io/badge/Plotly-5.17-purple?style=for-the-badge&logo=plotly)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-violet?style=for-the-badge&logo=bootstrap)

**HR team ke liye AI-powered recruitment system — resumes automatically parse karo, skills extract karo, candidates rank karo.**

</div>

---

## 📌 Problem Statement

Aaj kal HR teams ko **hundreds of resumes manually** check karne padte hain, jo:
- ⏳ Bahut time leta hai
- 😓 Human bias aata hai
- ❌ Best candidates miss ho jaate hain

**TalentAI** is samasya ka solution hai — ek fully automated, AI-driven recruitment platform.

---

## ✨ Features

### 👤 Candidate Side
- ✅ Register / Login
- ✅ PDF Resume Upload (drag & drop)
- ✅ Automatic skill extraction from resume
- ✅ Job listings dekho aur apply karo
- ✅ Application status track karo (Applied / Shortlisted / Hired / Rejected)

### 🏢 Recruiter Side
- ✅ Job postings create karo (required skills ke saath)
- ✅ Candidates automatically ranked milte hain (AI score ke basis par)
- ✅ One-click status update (Shortlist / Reject / Hire)
- ✅ Analytics dashboard with 5 interactive charts

### 🤖 AI / ML Module
- ✅ **PDF Parsing** — PyPDF2 se text extract
- ✅ **Skill Extraction** — 50+ skills ka database, regex matching
- ✅ **Skill Match Score** — required vs candidate skills (70% weight)
- ✅ **TF-IDF Similarity** — resume vs job description cosine similarity (30% weight)
- ✅ **Auto Ranking** — score ke basis par candidates rank

### 📊 Analytics Dashboard
- ✅ Top Skills in Demand (bar chart)
- ✅ Candidate Score Distribution (histogram)
- ✅ Applicants per Job Role (pie chart)
- ✅ Top Candidates by Score (bar chart)
- ✅ Application Status Overview (bar chart)

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python 3.10+, Flask 2.3 |
| **Database** | MySQL 8.0 |
| **AI / NLP** | scikit-learn (TF-IDF, Cosine Similarity) |
| **PDF Processing** | PyPDF2 |
| **Data Analysis** | Pandas |
| **Charts** | Plotly |
| **Frontend** | HTML5, CSS3, Bootstrap 5.3, JavaScript |
| **Auth** | Werkzeug (password hashing) |
| **Deployment** | Render / Railway (optional) |

---

## 📁 Project Structure

```
Recruitment_Analytics/
│
├── app.py                        ← Main Flask application (all routes)
├── requirements.txt              ← Python dependencies
├── SETUP_GUIDE.md                ← Detailed setup instructions
├── README.md                     ← Ye file
│
├── static/
│   ├── css/
│   │   └── style.css             ← Custom styles
│   └── js/
│       └── main.js               ← Frontend JavaScript
│
├── templates/
│   ├── base.html                 ← Navbar + layout (parent template)
│   ├── index.html                ← Homepage
│   ├── login.html                ← Login page
│   ├── register.html             ← Registration (Candidate / Recruiter)
│   ├── candidate_dashboard.html  ← Candidate portal
│   ├── upload_resume.html        ← PDF drag & drop upload
│   ├── recruiter_dashboard.html  ← Recruiter portal
│   ├── post_job.html             ← Create job posting
│   ├── view_applicants.html      ← Ranked candidates list
│   └── analytics.html           ← Plotly charts dashboard
│
├── uploads/                      ← Uploaded PDFs (auto-created)
│
├── models/
│   └── resume_parser.py          ← PDF parsing, skill extraction, scoring
│
├── analytics/
│   └── dashboard.py              ← Plotly chart generation functions
│
└── database/
    └── schema.sql                ← MySQL tables + sample data
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 ya usse upar
- MySQL 8.0
- pip

---

### Step 1 — Repository Clone Karo

```bash
git clone https://github.com/yourusername/TalentAI.git
cd TalentAI
```

---

### Step 2 — Virtual Environment Banao

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3 — Dependencies Install Karo

```bash
pip install -r requirements.txt
```

---

### Step 4 — MySQL Database Setup Karo

```bash
mysql -u root -p
```

MySQL prompt mein:

```sql
source database/schema.sql;
```

---

### Step 5 — app.py Configure Karo

`app.py` mein apna MySQL password dalo:

```python
app.config["MYSQL_PASSWORD"] = "apna_password_yahan"  # ← change karo
```

---

### Step 6 — App Run Karo

```bash
python app.py
```

Browser mein kholo: **http://localhost:5000** 🎉

---

## 🔄 System Flow

```
Candidate → PDF Upload
               ↓
         PyPDF2 Text Extraction
               ↓
         Skill Extraction (50+ skills regex match)
               ↓
         Skills saved in MySQL
               ↓
         Apply for Job
               ↓
    ┌──────────────────────────┐
    │  AI Scoring Algorithm    │
    │  • Skill Match  → 70%   │
    │  • TF-IDF Score → 30%   │
    └──────────────────────────┘
               ↓
    Recruiter → Ranked Candidates
    • Score ≥ 75% → ✅ Shortlist
    • Score 50–74% → ⚠️ Review
    • Score < 50%  → ❌ Reject
               ↓
    Analytics Dashboard (Charts)
```

---

## 📊 Scoring Algorithm

```python
# Skill Match Score (70% weight)
skill_score = matched_skills / required_skills * 100

# TF-IDF Cosine Similarity (30% weight)
tfidf_score = cosine_similarity(resume_text, job_description) * 100

# Final Score
final_score = (skill_score * 0.70) + (tfidf_score * 0.30)
```

**Example:**
```
Required Skills : python, flask, mysql, javascript, html  (5 total)
Candidate Skills: python, mysql, html, react              (3 matched)

Skill Score  = 3/5 × 100 = 60%
TF-IDF Score = 45%
Final Score  = (60 × 0.7) + (45 × 0.3) = 42 + 13.5 = 55.5%  → ⚠️ Review
```

---

## 🌐 API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/` | Homepage |
| GET/POST | `/register` | New account banao |
| GET/POST | `/login` | Login karo |
| GET | `/logout` | Logout |
| GET | `/candidate/dashboard` | Candidate portal |
| GET/POST | `/candidate/upload_resume` | PDF upload |
| POST | `/candidate/apply/<job_id>` | Job apply |
| GET | `/recruiter/dashboard` | Recruiter portal |
| GET/POST | `/recruiter/post_job` | Job post karo |
| GET | `/recruiter/job/<id>/applicants` | Ranked applicants |
| POST | `/recruiter/application/<id>/status` | Status update |
| GET | `/recruiter/analytics` | Charts dashboard |
| GET | `/api/jobs` | JSON — all jobs |
| GET | `/api/candidate/<id>/score` | JSON — candidate scores |

---

## 🖥️ Screenshots

> Register karo → Resume upload karo → Apply karo → Recruiter ranked list dekhe → Analytics charts

```
Homepage       →  /
Login          →  /login
Register       →  /register  (Candidate ya Recruiter)
PDF Upload     →  /candidate/upload_resume
Apply Job      →  /candidate/dashboard
Ranked List    →  /recruiter/job/<id>/applicants
Analytics      →  /recruiter/analytics
```

---

## ❌ Common Errors & Solutions

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError` | Library nahi hai | `pip install -r requirements.txt` |
| `Access denied for user 'root'` | Wrong MySQL password | `app.py` mein password check karo |
| `No module named 'MySQLdb'` | mysqlclient issue | `pip install PyMySQL` try karo |
| `PDF read error` | Scanned/image PDF | Text-based PDF use karo |
| Port 5000 in use | Port busy | `app.run(port=5001)` karo |

---

## 🚀 Deployment (Render — Free)

```bash
# 1. Gunicorn install karo
pip install gunicorn

# 2. requirements.txt update karo
echo "gunicorn" >> requirements.txt

# 3. GitHub par push karo
git add . && git commit -m "deploy" && git push

# 4. render.com → New Web Service → Connect GitHub repo
#    Build: pip install -r requirements.txt
#    Start: gunicorn app:app
#
# 5. MySQL ke liye PlanetScale (free) use karo
```

---

## 🗺️ Development Roadmap

- [x] Flask setup + MySQL connection
- [x] Login / Register (Candidate + Recruiter)
- [x] PDF resume upload
- [x] Skill extraction (50+ skills)
- [x] AI scoring (Skill Match + TF-IDF)
- [x] Candidate ranking
- [x] Job posting module
- [x] Application tracking
- [x] Analytics dashboard (5 charts)
- [ ] Email notifications
- [ ] Resume similarity recommendation
- [ ] Admin panel
- [ ] REST API (mobile app ke liye)

---

## 👨‍💻 Author

**Tumhara Naam**
- GitHub: [@yourusername](https://github.com/yourusername)
- LinkedIn: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)

---

## 📄 License

This project is open source — MIT License.

---

<div align="center">
  <strong>⭐ Agar project helpful laga toh GitHub par Star dena mat bhoolo!</strong>
</div>
