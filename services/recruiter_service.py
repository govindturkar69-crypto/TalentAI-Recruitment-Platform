from contextlib import closing

from core import get_db_connection
from services.audit_service import log_audit_event
from services.interview_service import cancel_future_scheduled_interviews_for_application
from services.notification_service import create_notification
from services.workflow import APPLICATION_STATUSES, RECRUITER_TRANSITIONS


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
    """H4: Verify every application belongs to a job owned by the recruiter.

    For shortlisted->rejected and shortlisted->hired transitions, auto-cancel
    future scheduled interviews inside the SAME transaction before commit.
    Audit and notifications only AFTER commit.
    """
    if new_status not in ["shortlisted", "rejected", "hired"]:
        return {
            "success_count": 0,
            "skipped_count": len(app_ids),
            "message": "Invalid bulk target status.",
            "type": "danger",
        }

    success_count = 0
    skipped_count = 0
    notifications_to_send = []
    audit_events_to_send = []
    interview_cancels_to_send = []

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            for app_id in app_ids:
                cur.execute(
                    """
                    SELECT a.id, a.candidate_id, a.status, j.job_title
                    FROM applications a
                    JOIN jobs j ON a.job_id = j.id
                    WHERE a.id = %s AND j.recruiter_id = %s
                    """,
                    (app_id, recruiter_id),
                )
                info = cur.fetchone()
                if not info:
                    skipped_count += 1
                    continue

                current_status = info["status"]
                if new_status not in RECRUITER_TRANSITIONS.get(current_status, set()):
                    skipped_count += 1
                    continue

                cur.execute(
                    "UPDATE applications SET status=%s WHERE id=%s AND status=%s", (new_status, app_id, current_status)
                )
                if cur.rowcount == 0:
                    skipped_count += 1
                    continue

                # Auto-cancel future scheduled interviews for rejected/hired transitions
                # (not for shortlisted — do not auto-cancel for shortlisted)
                cancelled_interviews = []
                if new_status in ("rejected", "hired"):
                    cancelled_interviews = cancel_future_scheduled_interviews_for_application(cur, app_id)

                success_count += 1

                audit_events_to_send.append((app_id, current_status, new_status))

                for ci in cancelled_interviews:
                    interview_cancels_to_send.append((ci["id"], app_id))

                if new_status in ("shortlisted", "rejected", "hired"):
                    msgs = {
                        "shortlisted": f"Good news! You've been shortlisted for {info['job_title']}.",
                        "rejected": f"Your application for {info['job_title']} was not selected.",
                        "hired": f"Congratulations! You've been hired for {info['job_title']}!",
                    }
                    title = f"Application {new_status.title()}"
                    body = msgs[new_status]
                    if cancelled_interviews and new_status in ("rejected", "hired"):
                        body += " Any future scheduled interviews have also been cancelled."
                    notifications_to_send.append((info["candidate_id"], title, body, new_status))

            # Primary DB commit first — application status updates AND interview cancellations
            conn.commit()

    # Audit and notifications only AFTER commit
    for aud_app_id, prev_status, n_status in audit_events_to_send:
        log_audit_event(
            recruiter_id,
            "application_status_changed",
            "application",
            aud_app_id,
            {"previous_status": prev_status, "new_status": n_status},
        )

    for inv_id, c_app_id in interview_cancels_to_send:
        log_audit_event(
            recruiter_id,
            "interview_cancelled",
            "interview",
            inv_id,
            {
                "application_id": c_app_id,
                "previous_interview_status": "scheduled",
                "new_interview_status": "cancelled",
            },
        )

    # Send notifications after successful commit
    for candidate_id, title, body, status in notifications_to_send:
        try:
            create_notification(candidate_id, title, body, status)
        except Exception:
            pass

    return {
        "success_count": success_count,
        "skipped_count": skipped_count,
        "message": f"Updated {success_count} application(s); skipped {skipped_count}.",
        "type": "success" if success_count > 0 else "warning",
    }


def update_status_service(app_id, new_status, recruiter_id):
    """H4: Verify the application belongs to a job owned by the recruiter.

    For shortlisted->rejected and shortlisted->hired transitions, auto-cancel
    future scheduled interviews inside the SAME transaction before commit.
    Audit and notifications only AFTER commit.
    """
    if new_status not in APPLICATION_STATUSES:
        return {"success": False, "message": "Invalid status.", "type": "danger"}

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT a.id, a.candidate_id, a.status, j.job_title
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.id = %s AND j.recruiter_id = %s
                """,
                (app_id, recruiter_id),
            )
            info = cur.fetchone()
            if not info:
                return {"success": False, "message": "Application not found.", "type": "danger"}

            current_status = info["status"]
            if new_status not in RECRUITER_TRANSITIONS.get(current_status, set()):
                return {"success": False, "message": "Invalid status transition.", "type": "danger"}

            cur.execute(
                "UPDATE applications SET status=%s WHERE id=%s AND status=%s", (new_status, app_id, current_status)
            )
            if cur.rowcount == 0:
                return {"success": False, "message": "Application state changed concurrently.", "type": "danger"}

            # Auto-cancel future scheduled interviews for rejected/hired transitions
            # (not for shortlisted — do not auto-cancel for shortlisted)
            cancelled_interviews = []
            if new_status in ("rejected", "hired"):
                cancelled_interviews = cancel_future_scheduled_interviews_for_application(cur, app_id)

            # Primary DB commit first
            conn.commit()

    # Audit and notifications only AFTER commit
    log_audit_event(
        recruiter_id,
        "application_status_changed",
        "application",
        app_id,
        {"previous_status": current_status, "new_status": new_status},
    )
    for ci in cancelled_interviews:
        log_audit_event(
            recruiter_id,
            "interview_cancelled",
            "interview",
            ci["id"],
            {
                "application_id": app_id,
                "previous_interview_status": "scheduled",
                "new_interview_status": "cancelled",
            },
        )

    try:
        if new_status in ("shortlisted", "rejected", "hired"):
            msgs = {
                "shortlisted": f"Good news! You've been shortlisted for {info['job_title']}.",
                "rejected": f"Your application for {info['job_title']} was not selected.",
                "hired": f"Congratulations! You've been hired for {info['job_title']}!",
            }
            body = msgs[new_status]
            if cancelled_interviews and new_status in ("rejected", "hired"):
                body += " Any future scheduled interviews have also been cancelled."
            create_notification(info["candidate_id"], f"Application {new_status.title()}", body, new_status)
    except Exception:
        pass

    return {"success": True, "message": f"Status updated to: {new_status}", "type": "success"}


def get_application_candidate_profile(app_id, recruiter_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            # 1. Authorization and Application Info
            cur.execute(
                """
                SELECT a.id as application_id, a.score, a.matched_skills, a.missing_skills, a.status, a.applied_at,
                       j.id as job_id, j.job_title, u.name, u.email, u.id as candidate_id
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                JOIN users u ON a.candidate_id = u.id
                WHERE a.id = %s AND j.recruiter_id = %s
            """,
                (app_id, recruiter_id),
            )
            app_data = cur.fetchone()
            if not app_data:
                return None, {"error": "Application not found.", "type": "danger"}

            candidate_id = app_data["candidate_id"]

            # 2. Profile Data
            cur.execute("SELECT * FROM candidate_profiles WHERE user_id = %s", (candidate_id,))
            profile = cur.fetchone()

            cur.execute(
                "SELECT * FROM candidate_education WHERE user_id = %s ORDER BY start_date DESC", (candidate_id,)
            )
            education = cur.fetchall()

            cur.execute(
                "SELECT * FROM candidate_experience WHERE user_id = %s ORDER BY start_date DESC", (candidate_id,)
            )
            experience = cur.fetchall()

            cur.execute("SELECT * FROM candidate_projects WHERE user_id = %s ORDER BY created_at DESC", (candidate_id,))
            projects = cur.fetchall()

            cur.execute(
                "SELECT * FROM candidate_certifications WHERE user_id = %s ORDER BY issue_date DESC", (candidate_id,)
            )
            certifications = cur.fetchall()

            cur.execute(
                "SELECT * FROM candidate_achievements WHERE user_id = %s ORDER BY achieved_date DESC", (candidate_id,)
            )
            achievements = cur.fetchall()

            return {
                "app_data": app_data,
                "profile": profile,
                "education": education,
                "experience": experience,
                "projects": projects,
                "certifications": certifications,
                "achievements": achievements,
            }, None


def get_application_resume(app_id, recruiter_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT r.resume_path
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                JOIN resumes r ON a.resume_id = r.id
                WHERE a.id = %s AND j.recruiter_id = %s AND r.user_id = a.candidate_id
            """,
                (app_id, recruiter_id),
            )
            resume = cur.fetchone()
            if not resume:
                return None, {"error": "Resume not found or unauthorized.", "type": "danger"}
            return resume["resume_path"], None
