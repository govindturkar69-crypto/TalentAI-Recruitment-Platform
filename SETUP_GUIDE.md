# 🚀 TalentAI — Complete Setup Guide (Hindi + English)

---

## 📦 STEP 1: Python Virtual Environment Banao

```bash
# Project folder mein jao
cd Recruitment_Analytics

# Virtual environment banao
python -m venv venv

# Activate karo
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

---

## 📥 STEP 2: Libraries Install Karo

```bash
pip install -r requirements.txt
```

Agar koi error aaye:
```bash
pip install Flask Flask-MySQLdb Werkzeug PyPDF2 pandas plotly scikit-learn python-dotenv
```

---

## 🗃️ STEP 3: MySQL Database Setup

### MySQL mein login karo:
```bash
mysql -u root -p
```

### Schema run karo:
```sql
source database/schema.sql;
```

Ya copy-paste karo pura `schema.sql` content.

---

## ⚙️ STEP 4: app.py mein MySQL Password Set Karo

`app.py` file mein yeh line dhundho:
```python
app.config["MYSQL_PASSWORD"] = "your_mysql_password"
```

Apna actual MySQL password dalo.

---

## ▶️ STEP 5: App Run Karo

```bash
python app.py
```

Browser mein kholo: **http://localhost:5000**

---

## 👤 STEP 6: Accounts Banao

### Recruiter Account:
1. http://localhost:5000/register kholo
2. Role mein "Recruiter" select karo
3. Login karo → Jobs post karo → Candidates dekho → Analytics dekho

### Candidate Account:
1. Doosre browser mein register karo
2. Role mein "Candidate" select karo
3. Login karo → Resume upload karo → Jobs ke liye apply karo

---

## 📄 STEP 7: Resume PDF Test

Test ke liye ek sample PDF banao:

```
I am a Python developer with 3 years of experience.
Skills: Python, Flask, MySQL, JavaScript, HTML, CSS
I have worked on machine learning projects using pandas and scikit-learn.
Familiar with REST API, Git, Docker.
```

Ise PDF mein save karo aur upload karo — AI skills extract kar lega.

---

## 🗂️ Project Structure Summary

```
Recruitment_Analytics/
│
├── app.py                  ← Main Flask app (routes + logic)
├── requirements.txt        ← All Python packages
├── SETUP_GUIDE.md          ← Ye file
│
├── static/
│   ├── css/style.css       ← Custom styles
│   └── js/main.js          ← Frontend JavaScript
│
├── templates/
│   ├── base.html           ← Navbar + layout (baaki sab ise extend karte hain)
│   ├── index.html          ← Homepage
│   ├── login.html          ← Login page
│   ├── register.html       ← Registration page
│   ├── candidate_dashboard.html  ← Candidate portal
│   ├── upload_resume.html  ← PDF upload page
│   ├── recruiter_dashboard.html  ← Recruiter portal
│   ├── post_job.html       ← Job posting form
│   ├── view_applicants.html← Ranked candidates list
│   └── analytics.html      ← Plotly charts dashboard
│
├── uploads/                ← PDFs yahan save hote hain (auto created)
│
├── models/
│   └── resume_parser.py    ← PDF parsing + skill extraction + scoring
│
├── analytics/
│   └── dashboard.py        ← Plotly chart functions
│
└── database/
    └── schema.sql          ← MySQL tables + sample data
```

---

## 🔄 How It Works (Flow)

```
Candidate uploads PDF
        ↓
PyPDF2 se text extract
        ↓
SKILLS_DB se skills match karo (regex)
        ↓
Skills MySQL mein save karo
        ↓
Job apply karo → score calculate:
  • Skill match score (70%)
  • TF-IDF similarity score (30%)
        ↓
Recruiter dekhe → ranked list
  • 75%+ → Shortlist ✅
  • 50-74% → Review ⚠️
  • 0-49% → Reject ❌
        ↓
Analytics dashboard mein charts
```

---

## ❌ Common Errors & Solutions

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: flask` | `pip install Flask` run karo |
| `Access denied for user 'root'` | MySQL password check karo in app.py |
| `No module named 'MySQLdb'` | `pip install mysqlclient` ya `pip install PyMySQL` |
| `PDF read error` | PDF scan kiya hua na ho (text-based hona chahiye) |
| Port already in use | `app.run(port=5001)` try karo |

---

## 🚀 Deployment (Render pe Free Deploy)

1. GitHub par project push karo
2. render.com par account banao
3. "New Web Service" → GitHub repo connect karo
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. MySQL ke liye PlanetScale ya Railway use karo (free)

---

## 📞 Important Routes

| URL | Description |
|-----|-------------|
| `/` | Homepage |
| `/register` | New account |
| `/login` | Login |
| `/candidate/dashboard` | Candidate portal |
| `/candidate/upload_resume` | PDF upload |
| `/recruiter/dashboard` | Recruiter portal |
| `/recruiter/post_job` | Job post karo |
| `/recruiter/job/<id>/applicants` | Ranked candidates |
| `/recruiter/analytics` | Charts dashboard |
| `/api/jobs` | JSON API |
