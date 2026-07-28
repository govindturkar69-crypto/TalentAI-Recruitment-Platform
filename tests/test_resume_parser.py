from models.resume_parser import (
    extract_skills,
    score_candidate,
    tfidf_similarity,
    get_final_score,
)


def test_extract_skills_finds_known_skills():
    skills = extract_skills("I have experience with Python, Flask and MySQL.")
    assert "python" in skills
    assert "flask" in skills
    assert "mysql" in skills


def test_extract_skills_is_case_insensitive():
    assert "python" in extract_skills("PYTHON developer")


def test_extract_skills_ignores_unknown_words():
    assert extract_skills("I like pizza and cricket") == []


def test_extract_skills_has_no_duplicates():
    assert extract_skills("python python python").count("python") == 1


def test_score_is_100_when_all_skills_match():
    result = score_candidate(["python", "flask"], "python, flask")
    assert result["score"] == 100.0
    assert result["missing"] == []


def test_score_is_50_when_half_match():
    result = score_candidate(["python"], "python, flask")
    assert result["score"] == 50.0
    assert "flask" in result["missing"]


def test_score_is_zero_when_nothing_matches():
    result = score_candidate(["java"], "python, flask")
    assert result["score"] == 0
    assert result["matched"] == []


def test_score_handles_empty_requirements():
    result = score_candidate(["python"], "")
    assert result["score"] == 0


def test_tfidf_returns_zero_for_empty_input():
    assert tfidf_similarity("", "some job description") == 0.0
    assert tfidf_similarity("some resume", "") == 0.0


def test_tfidf_higher_for_similar_text():
    resume = "python flask backend developer with sql experience"
    close_job = "looking for a python flask backend developer"
    far_job = "senior graphic designer with photoshop skills"
    assert tfidf_similarity(resume, close_job) > tfidf_similarity(resume, far_job)


def test_final_score_uses_skill_score_when_no_job_description():
    result = get_final_score("resume text", ["python", "flask"], "python, flask")
    assert result["final_score"] == 100.0


def test_final_score_blends_skill_and_text_when_job_description_given():
    result = get_final_score(
        "python flask developer",
        ["python", "flask"],
        "python, flask",
        job_description="python flask developer wanted",
    )
    assert 0 <= result["final_score"] <= 100
    assert "skill_score" in result
    assert "tfidf_score" in result