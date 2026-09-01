from contextlib import closing

from core import get_db_connection
from models.resume_parser import extract_skills, extract_text_from_pdf, get_final_score, score_candidate
from services.audit_service import log_audit_event
from services.interview_service import cancel_future_scheduled_interviews_for_application
from services.notification_service import create_notification
from services.workflow import CANDIDATE_TRANSITIONS


def get_resolved_candidate_skills(user_id, cur):
    """
    Preferred skill resolution:
    1. Candidate curated Profile Skills
    2. Otherwise latest resumes.skills
    3. Otherwise empty list
    """
    cur.execute("SELECT skills FROM candidate_profiles WHERE user_id = %s", (user_id,))
    profile = cur.fetchone()
    if profile and profile.get("skills"):
        return [s.strip() for s in profile["skills"].split(",") if s.strip()]

    cur.execute("SELECT skills FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (user_id,))
    resume = cur.fetchone()
    if resume and resume.get("skills"):
        return [s.strip() for s in resume["skills"].split(",") if s.strip()]

    return []


def process_resume_upload(user_id, save_path, filename):
    raw_text = extract_text_from_pdf(save_path)
    skills = extract_skills(raw_text)
    skills_str = ",".join(skills)

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO resumes (user_id, resume_path, skills, raw_text) VALUES (%s,%s,%s,%s)",
                (user_id, filename, skills_str, raw_text),
            )
            conn.commit()

    return skills, skills_str


def apply_for_job_service(user_id, user_name, job_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT * FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (user_id,))
            resume = cur.fetchone()
            if not resume:
                return {"success": False, "message": "Please upload your resume first.", "type": "warning"}

            cur.execute("SELECT id FROM applications WHERE candidate_id=%s AND job_id=%s", (user_id, job_id))
            if cur.fetchone():
                return {"success": False, "message": "You have already applied for this job.", "type": "warning"}

            cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            job = cur.fetchone()
            if not job:
                return {"success": False, "message": "Job not found.", "type": "danger"}
            if not job.get("is_active"):
                return {"success": False, "message": "This job is no longer active.", "type": "warning"}

            candidate_skills = get_resolved_candidate_skills(user_id, cur)
            result = get_final_score(
                resume["raw_text"], candidate_skills, job["required_skills"], job["description"] or ""
            )

            cur.execute(
                """
                INSERT INTO applications
                    (candidate_id, job_id, resume_id, score, matched_skills, missing_skills)
                VALUES (%s,%s,%s,%s,%s,%s)
            """,
                (
                    user_id,
                    job_id,
                    resume["id"],
                    result["final_score"],
                    ",".join(result["matched"]),
                    ",".join(result["missing"]),
                ),
            )
            conn.commit()

    create_notification(
        user_id,
        "Application Submitted",
        f"You applied for {job['job_title']} with a score of {result['final_score']:.1f}%.",
        "applied",
    )
    create_notification(
        job["recruiter_id"],
        "New Application Received",
        f"{user_name} applied for {job['job_title']} with a score of {result['final_score']:.1f}%.",
        "applied",
    )

    return {
        "success": True,
        "message": f"Application submitted! Your score: {result['final_score']:.1f}%",
        "type": "success",
    }


def withdraw_application_service(app_id, user_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT a.*, j.job_title FROM applications a JOIN jobs j ON a.job_id = j.id "
                "WHERE a.id = %s AND a.candidate_id = %s",
                (app_id, user_id),
            )
            app_row = cur.fetchone()

            if not app_row:
                return {"success": False, "message": "Application not found.", "type": "danger"}

            current_status = app_row["status"]
            if "withdrawn" not in CANDIDATE_TRANSITIONS.get(current_status, set()):
                return {
                    "success": False,
                    "message": "You cannot withdraw an application in this state.",
                    "type": "warning",
                }

            cur.execute(
                "UPDATE applications SET status='withdrawn' WHERE id=%s AND status=%s",
                (app_id, current_status),
            )
            if cur.rowcount == 0:
                return {"success": False, "message": "Application state changed concurrently.", "type": "danger"}

            cancelled_interviews = cancel_future_scheduled_interviews_for_application(cur, app_id)

            conn.commit()

    log_audit_event(
        user_id,
        "application_withdrawn",
        "application",
        app_id,
        {"previous_status": current_status, "new_status": "withdrawn"},
    )

    for iv in cancelled_interviews:
        log_audit_event(
            user_id,
            "interview_cancelled",
            "interview",
            iv["id"],
            {
                "application_id": app_id,
                "previous_interview_status": "scheduled",
                "new_interview_status": "cancelled",
            },
        )

    return {"success": True, "message": f"Application for {app_row['job_title']} has been withdrawn.", "type": "info"}


def get_job_recommendations_service(user_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT * FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (user_id,))
            resume = cur.fetchone()

            candidate_skills = get_resolved_candidate_skills(user_id, cur)
            if not candidate_skills:
                return resume, []

            cur.execute("SELECT * FROM jobs WHERE is_active = TRUE ORDER BY created_at DESC")
            jobs = cur.fetchall()
            cur.execute("SELECT job_id FROM applications WHERE candidate_id = %s", (user_id,))
            applied_job_ids = {row["job_id"] for row in cur.fetchall()}

    recommendations = []
    for job in jobs:
        result = score_candidate(candidate_skills, job["required_skills"])
        if result["score"] > 0:
            recommendations.append(
                {
                    "job": job,
                    "match_score": round(result["score"], 1),
                    "matched": result["matched"],
                    "already_applied": job["id"] in applied_job_ids,
                }
            )
    recommendations.sort(key=lambda r: r["match_score"], reverse=True)
    return resume, recommendations
