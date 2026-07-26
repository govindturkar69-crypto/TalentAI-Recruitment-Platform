"""Resume parsing, skill extraction, and candidate scoring."""

import re

import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SKILLS_DB = [
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "php", "ruby",
    "swift", "kotlin", "go", "rust", "scala", "r",

    # Web frontend
    "html", "css", "react", "angular", "vue", "bootstrap", "tailwind",
    "jquery", "sass", "webpack", "next.js", "nuxt",

    # Web backend
    "flask", "django", "fastapi", "node", "express", "spring", "laravel",
    "rest api", "graphql", "microservices",

    # Databases
    "mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle",
    "sql", "nosql", "elasticsearch",

    # Data science / ML
    "machine learning", "deep learning", "neural network", "natural language processing",
    "computer vision", "pandas", "numpy", "matplotlib", "scikit-learn",
    "tensorflow", "keras", "pytorch", "statistics", "data analysis",
    "data visualization", "feature engineering",

    # DevOps / cloud
    "docker", "kubernetes", "aws", "azure", "gcp", "linux", "git",
    "ci/cd", "jenkins", "ansible", "terraform", "nginx",

    # Tools
    "excel", "power bi", "tableau", "jira", "figma", "postman",
]


def extract_text_from_pdf(pdf_path):
    """Extract and return the plain text from a PDF file."""
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


def extract_skills(text):
    """Return the skills from SKILLS_DB that appear in the given text."""
    text_lower = text.lower()
    found_skills = []

    for skill in SKILLS_DB:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            if skill not in found_skills:
                found_skills.append(skill)

    return found_skills


def score_candidate(candidate_skills, required_skills_str):
    """Compare candidate skills against a job's required skills.

    Returns a dict with the match score plus the matched and missing skills.
    """
    required = [s.strip().lower() for s in required_skills_str.split(",") if s.strip()]

    matched = [s for s in required if s in candidate_skills]
    missing = [s for s in required if s not in candidate_skills]

    score = (len(matched) / len(required) * 100) if required else 0

    return {
        "score": round(score, 2),
        "matched": matched,
        "missing": missing,
        "total_required": len(required),
        "total_matched": len(matched),
    }


def tfidf_similarity(resume_text, job_description):
    """Return a 0-100 similarity score between a resume and a job description."""
    if not resume_text or not job_description:
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return round(float(similarity[0][0]) * 100, 2)
    except Exception:
        return 0.0


def get_final_score(resume_text, candidate_skills, required_skills_str, job_description=""):
    """Weighted final score: 70% skill match, 30% TF-IDF text similarity.

    When no job description is available, the skill match score is used on its own.
    """
    skill_result = score_candidate(candidate_skills, required_skills_str)
    skill_score = skill_result["score"]

    tfidf_score = tfidf_similarity(resume_text, job_description)

    if job_description:
        final = (skill_score * 0.7) + (tfidf_score * 0.3)
    else:
        final = skill_score

    skill_result["final_score"] = round(final, 2)
    skill_result["tfidf_score"] = tfidf_score
    skill_result["skill_score"] = skill_score
    return skill_result
