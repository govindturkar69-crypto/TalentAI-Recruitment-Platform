from contextlib import closing

from core import get_db_connection
from services.notification_service import create_notification


def post_job_service(user_id, title, skills, description, location, experience):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                INSERT INTO jobs (recruiter_id, job_title, required_skills, description, location, experience)
                VALUES (%s,%s,%s,%s,%s,%s)
            """,
                (user_id, title, skills, description, location, experience),
            )
            conn.commit()


def update_job_service(user_id, job_id, title, skills, description, location, experience):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                UPDATE jobs SET job_title=%s, required_skills=%s, description=%s,
                location=%s, experience=%s WHERE id=%s AND recruiter_id=%s
            """,
                (title, skills, description, location, experience, job_id, user_id),
            )
            conn.commit()


def toggle_job_active_service(user_id, job_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT is_active, job_title FROM jobs WHERE id = %s AND recruiter_id = %s", (job_id, user_id))
            job = cur.fetchone()
            if not job:
                return {"success": False, "message": "Job not found.", "type": "danger"}

            new_state = not job["is_active"]
            cur.execute("UPDATE jobs SET is_active = %s WHERE id = %s", (new_state, job_id))
            conn.commit()

    return {
        "success": True,
        "message": f"Job '{job['job_title']}' has been {'reopened' if new_state else 'closed'}.",
        "type": "success",
    }


def delete_job_service(user_id, job_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT job_title FROM jobs WHERE id = %s AND recruiter_id = %s", (job_id, user_id))
            job = cur.fetchone()
            if not job:
                return {"success": False, "message": "Job not found.", "type": "danger"}

            cur.execute("DELETE FROM jobs WHERE id = %s AND recruiter_id = %s", (job_id, user_id))
            conn.commit()

    return {"success": True, "message": f"Job '{job['job_title']}' deleted.", "type": "info"}


def bulk_update_status_service(app_ids, new_status, recruiter_id):
    """H4: Verify every application belongs to a job owned by the recruiter."""
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            for app_id in app_ids:
                # Verify ownership before any update
                cur.execute(
                    """
                    SELECT a.id, a.candidate_id, j.job_title
                    FROM applications a
                    JOIN jobs j ON a.job_id = j.id
                    WHERE a.id = %s AND j.recruiter_id = %s
                    """,
                    (app_id, recruiter_id),
                )
                info = cur.fetchone()
                if not info:
                    # Unauthorized — skip silently to not leak information
                    continue
                cur.execute("UPDATE applications SET status=%s WHERE id=%s", (new_status, app_id))
                if new_status in ("shortlisted", "rejected", "hired"):
                    msgs = {
                        "shortlisted": f"Good news! You've been shortlisted for {info['job_title']}.",
                        "rejected": f"Your application for {info['job_title']} was not selected.",
                        "hired": f"Congratulations! You've been hired for {info['job_title']}!",
                    }
                    create_notification(
                        info["candidate_id"], f"Application {new_status.title()}", msgs[new_status], new_status
                    )
            conn.commit()


def update_status_service(app_id, new_status, recruiter_id):
    """H4: Verify the application belongs to a job owned by the recruiter."""
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            # Verify ownership before any update
            cur.execute(
                """
                SELECT a.id, a.candidate_id, j.job_title
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.id = %s AND j.recruiter_id = %s
                """,
                (app_id, recruiter_id),
            )
            info = cur.fetchone()
            if not info:
                return {"success": False, "message": "Application not found.", "type": "danger"}

            cur.execute("UPDATE applications SET status=%s WHERE id=%s", (new_status, app_id))
            conn.commit()

    if new_status in ("shortlisted", "rejected", "hired"):
        msgs = {
            "shortlisted": f"Good news! You've been shortlisted for {info['job_title']}.",
            "rejected": f"Your application for {info['job_title']} was not selected.",
            "hired": f"Congratulations! You've been hired for {info['job_title']}!",
        }
        create_notification(info["candidate_id"], f"Application {new_status.title()}", msgs[new_status], new_status)

    return {"success": True, "message": f"Status updated to: {new_status}", "type": "success"}
