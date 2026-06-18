# ============================================
# models/resume_parser.py
# Resume Parsing, Skill Extraction & Ranking
# ============================================

import PyPDF2
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Comprehensive Skills Database ──────────────────────────────────────────────
SKILLS_DB = [
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "php", "ruby",
    "swift", "kotlin", "go", "rust", "scala", "r",

    # Web Frontend
    "html", "css", "react", "angular", "vue", "bootstrap", "tailwind",
    "jquery", "sass", "webpack", "next.js", "nuxt",

    # Web Backend
    "flask", "django", "fastapi", "node", "express", "spring", "laravel",
    "rest api", "graphql", "microservices",

    # Databases
    "mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle",
    "sql", "nosql", "elasticsearch",

    # Data Science / ML
    "machine learning", "deep learning", "neural network", "natural language processing",
    "computer vision", "pandas", "numpy", "matplotlib", "scikit-learn",
    "tensorflow", "keras", "pytorch", "statistics", "data analysis",
    "data visualization", "feature engineering",

    # DevOps / Cloud
    "docker", "kubernetes", "aws", "azure", "gcp", "linux", "git",
    "ci/cd", "jenkins", "ansible", "terraform", "nginx",

    # Tools
    "excel", "power bi", "tableau", "jira", "figma", "postman",
]


# ── 1. PDF Text Extraction ──────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path):
    """
    PDF file se text extract karta hai.
    Return: extracted text string
    """
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"PDF read error: {e}")
    return text.strip()


# ── 2. Skill Extraction ─────────────────────────────────────────────────────────
def extract_skills(text):
    """
    Resume text se skills extract karta hai SKILLS_DB se match karke.
    Return: list of matched skills
    """
    text_lower = text.lower()
    found_skills = []

    for skill in SKILLS_DB:
        # Word boundary match for accuracy
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            if skill not in found_skills:
                found_skills.append(skill)

    return found_skills


# ── 3. Candidate Scoring ────────────────────────────────────────────────────────
def score_candidate(candidate_skills, required_skills_str):
    """
    Candidate skills ko required skills se compare karke score deta hai.

    Args:
        candidate_skills : list  — resume se extracted skills
        required_skills_str: str — comma-separated required skills

    Return: dict with score, matched, missing
    """
    required = [s.strip().lower() for s in required_skills_str.split(",") if s.strip()]

    matched = [s for s in required if s in candidate_skills]
    missing = [s for s in required if s not in candidate_skills]

    score = (len(matched) / len(required) * 100) if required else 0

    return {
        "score"  : round(score, 2),
        "matched": matched,
        "missing": missing,
        "total_required": len(required),
        "total_matched" : len(matched),
    }


# ── 4. TF-IDF Similarity (Advanced) ────────────────────────────────────────────
def tfidf_similarity(resume_text, job_description):
    """
    TF-IDF + Cosine Similarity se resume aur job description ka match score.
    Return: similarity score 0-100
    """
    if not resume_text or not job_description:
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return round(float(similarity[0][0]) * 100, 2)
    except Exception:
        return 0.0


# ── 5. Combined Final Score ─────────────────────────────────────────────────────
def get_final_score(resume_text, candidate_skills, required_skills_str, job_description=""):
    """
    Skill match (70%) + TF-IDF similarity (30%) ka weighted final score.
    """
    skill_result = score_candidate(candidate_skills, required_skills_str)
    skill_score  = skill_result["score"]

    tfidf_score  = tfidf_similarity(resume_text, job_description)

    # Weighted combination
    if job_description:
        final = (skill_score * 0.7) + (tfidf_score * 0.3)
    else:
        final = skill_score

    skill_result["final_score"]  = round(final, 2)
    skill_result["tfidf_score"]  = tfidf_score
    skill_result["skill_score"]  = skill_score
    return skill_result


# ── 6. Rank Multiple Candidates ────────────────────────────────────────────────
def rank_candidates(candidates_data):
    """
    Multiple candidates ko score ke basis par rank karta hai.

    Args:
        candidates_data: list of dicts:
            [{"name": ..., "skills": [...], "resume_text": ...}, ...]

    Return: sorted list with rank added
    """
    ranked = sorted(candidates_data, key=lambda x: x.get("score", 0), reverse=True)
    for i, c in enumerate(ranked):
        c["rank"] = i + 1
    return ranked
