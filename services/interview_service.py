import datetime
from contextlib import closing
from urllib.parse import urlparse

from core import get_db_connection
from services.audit_service import log_audit_event
from services.notification_service import create_notification

INTERVIEW_STATUSES = {"scheduled", "completed", "cancelled"}
INTERVIEW_MODES = {"online", "in_person", "phone"}
INTERVIEW_TRANSITIONS = {
    "scheduled": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def parse_local_datetime(dt_str):
    if not dt_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(dt_str)
        if dt.tzinfo is not None:
            return None
        return dt
    except ValueError:
        return None


def validate_interview_fields(duration_minutes, mode, location_or_link, notes):
    try:
        duration = int(duration_minutes)
    except (ValueError, TypeError):
        return False, "Duration must be an integer."

    if duration < 5 or duration > 480:
        return False, "Duration must be between 5 and 480 minutes."

    if mode not in INTERVIEW_MODES:
        return False, "Invalid mode."

    clean_location = None
    if mode == "online":
        if not location_or_link:
            return False, "Online mode requires a meeting link."
        link = location_or_link.strip()
        if len(link) > 500:
            return False, "Link must be 500 characters or less."
        try:
            parsed = urlparse(link)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                return False, "Online mode requires a valid http or https URL."
        except Exception:
            return False, "Invalid URL."
        clean_location = link

    elif mode == "in_person":
        if not location_or_link or not location_or_link.strip():
            return False, "In-person mode requires a location."
        loc = location_or_link.strip()
        if len(loc) > 500:
            return False, "Location must be 500 characters or less."
        clean_location = loc

    elif mode == "phone":
        if location_or_link and location_or_link.strip():
            return False, "Phone mode cannot have a location or link. Phone number should be from candidate profile."
        clean_location = None

    clean_notes = None
    if notes:
        n = notes.strip()
        if n:
            if len(n) > 2000:
                return False, "Notes must be 2000 characters or less."
            clean_notes = n

    return True, (duration, mode, clean_location, clean_notes)


def _authorize_recruiter_application(cur, application_id, recruiter_id, for_update=False):
    query = """
        SELECT a.id, a.candidate_id, a.status, j.id as job_id, j.job_title
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = %s AND j.recruiter_id = %s
    """
    if for_update:
        query += " FOR UPDATE"
    cur.execute(query, (application_id, recruiter_id))
    return cur.fetchone()


def schedule_interview_service(
    application_id,
    recruiter_id,
    scheduled_at_str,
    duration_minutes,
    mode,
    location_or_link,
    notes,
):
    dt = parse_local_datetime(scheduled_at_str)
    if not dt:
        return {"success": False, "message": "Invalid scheduled time.", "type": "danger"}

    valid, result = validate_interview_fields(duration_minutes, mode, location_or_link, notes)
    if not valid:
        return {"success": False, "message": result, "type": "danger"}

    clean_duration, clean_mode, clean_location, clean_notes = result

    new_id = None
    candidate_id = None
    job_title = None

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            app_info = _authorize_recruiter_application(cur, application_id, recruiter_id, for_update=True)
            if not app_info:
                return {"success": False, "message": "Application not found or access denied.", "type": "danger"}

            if app_info["status"] != "shortlisted":
                return {
                    "success": False,
                    "message": "Application must be shortlisted to schedule an interview.",
                    "type": "danger",
                }

            cur.execute("SELECT NOW() as db_now")
            db_now = cur.fetchone()["db_now"]

            if dt <= db_now:
                return {"success": False, "message": "Scheduled time must be in the future.", "type": "danger"}

            cur.execute(
                """
                INSERT INTO interviews (
                    application_id, scheduled_at, duration_minutes,
                    mode, location_or_link, notes, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'scheduled')
                """,
                (application_id, dt, clean_duration, clean_mode, clean_location, clean_notes),
            )
            new_id = cur.lastrowid
            candidate_id = app_info["candidate_id"]
            job_title = app_info["job_title"]
            conn.commit()

    log_audit_event(
        recruiter_id,
        "interview_scheduled",
        "interview",
        new_id,
        {
            "application_id": application_id,
            "interview_status": "scheduled",
            "scheduled_at": str(dt),
            "duration_minutes": clean_duration,
            "mode": clean_mode,
        },
    )

    try:
        create_notification(
            candidate_id,
            "Interview Scheduled",
            f"An interview for {job_title} has been scheduled on {dt.strftime('%Y-%m-%d %H:%M')}.",
            "system",
        )
    except Exception:
        pass

    return {"success": True, "message": "Interview scheduled successfully.", "type": "success"}


def get_recruiter_interviews_for_application(application_id, recruiter_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            app_info = _authorize_recruiter_application(cur, application_id, recruiter_id)
            if not app_info:
                return {"success": False, "message": "Access denied.", "type": "danger", "data": None}

            cur.execute(
                "SELECT * FROM interviews WHERE application_id = %s ORDER BY scheduled_at ASC", (application_id,)
            )
            interviews = cur.fetchall()
            return {"success": True, "message": "", "type": "success", "data": interviews}


def get_candidate_interviews(candidate_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT i.*, j.job_title, a.status as application_status
                FROM interviews i
                JOIN applications a ON i.application_id = a.id
                JOIN jobs j ON a.job_id = j.id
                WHERE a.candidate_id = %s
                ORDER BY i.scheduled_at ASC
                """,
                (candidate_id,),
            )
            return cur.fetchall()


def update_interview_service(
    interview_id,
    recruiter_id,
    scheduled_at_str,
    duration_minutes,
    mode,
    location_or_link,
    notes,
):
    dt = parse_local_datetime(scheduled_at_str)
    if not dt:
        return {"success": False, "message": "Invalid scheduled time.", "type": "danger"}

    valid, result = validate_interview_fields(duration_minutes, mode, location_or_link, notes)
    if not valid:
        return {"success": False, "message": result, "type": "danger"}

    clean_duration, clean_mode, clean_location, clean_notes = result

    candidate_id = None
    job_title = None
    app_id = None
    prev_time = None

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT i.id, i.application_id, i.status, i.scheduled_at,
                       a.candidate_id, a.status as app_status, j.job_title
                FROM interviews i
                JOIN applications a ON i.application_id = a.id
                JOIN jobs j ON a.job_id = j.id
                WHERE i.id = %s AND j.recruiter_id = %s
                FOR UPDATE
                """,
                (interview_id, recruiter_id),
            )
            interview = cur.fetchone()

            if not interview:
                return {"success": False, "message": "Interview not found or access denied.", "type": "danger"}

            if interview["status"] != "scheduled":
                return {"success": False, "message": "Only scheduled interviews can be edited.", "type": "danger"}

            if interview["app_status"] != "shortlisted":
                return {"success": False, "message": "Application is no longer shortlisted.", "type": "danger"}

            cur.execute("SELECT NOW() as db_now")
            db_now = cur.fetchone()["db_now"]

            if dt <= db_now:
                return {"success": False, "message": "Scheduled time must be in the future.", "type": "danger"}

            app_id = interview["application_id"]
            prev_time = interview["scheduled_at"]
            candidate_id = interview["candidate_id"]
            job_title = interview["job_title"]

            cur.execute(
                """
                UPDATE interviews
                SET scheduled_at = %s, duration_minutes = %s, mode = %s, location_or_link = %s, notes = %s
                WHERE id = %s AND status = 'scheduled'
                """,
                (dt, clean_duration, clean_mode, clean_location, clean_notes, interview_id),
            )

            if cur.rowcount == 0:
                return {"success": False, "message": "Interview state changed concurrently.", "type": "danger"}

            conn.commit()

    log_audit_event(
        recruiter_id,
        "interview_updated",
        "interview",
        interview_id,
        {
            "application_id": app_id,
            "previous_scheduled_at": str(prev_time),
            "new_scheduled_at": str(dt),
            "duration_minutes": clean_duration,
            "mode": clean_mode,
            "interview_status": "scheduled",
        },
    )

    try:
        create_notification(
            candidate_id,
            "Interview Rescheduled",
            f"Your interview for {job_title} has been rescheduled to {dt.strftime('%Y-%m-%d %H:%M')}.",
            "system",
        )
    except Exception:
        pass

    return {"success": True, "message": "Interview updated successfully.", "type": "success"}


def cancel_interview_service(interview_id, recruiter_id):
    app_id = None
    candidate_id = None
    job_title = None

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT i.id, i.application_id, i.status, a.candidate_id, j.job_title
                FROM interviews i
                JOIN applications a ON i.application_id = a.id
                JOIN jobs j ON a.job_id = j.id
                WHERE i.id = %s AND j.recruiter_id = %s
                """,
                (interview_id, recruiter_id),
            )
            interview = cur.fetchone()

            if not interview:
                return {"success": False, "message": "Interview not found or access denied.", "type": "danger"}

            if interview["status"] != "scheduled":
                return {"success": False, "message": "Only scheduled interviews can be cancelled.", "type": "danger"}

            app_id = interview["application_id"]
            candidate_id = interview["candidate_id"]
            job_title = interview["job_title"]

            cur.execute(
                "UPDATE interviews SET status = 'cancelled' WHERE id = %s AND status = 'scheduled'", (interview_id,)
            )

            if cur.rowcount == 0:
                return {"success": False, "message": "Interview state changed concurrently.", "type": "danger"}

            conn.commit()

    log_audit_event(
        recruiter_id,
        "interview_cancelled",
        "interview",
        interview_id,
        {
            "application_id": app_id,
            "previous_interview_status": "scheduled",
            "new_interview_status": "cancelled",
        },
    )

    try:
        create_notification(
            candidate_id, "Interview Cancelled", f"Your interview for {job_title} has been cancelled.", "system"
        )
    except Exception:
        pass

    return {"success": True, "message": "Interview cancelled successfully.", "type": "info"}


def complete_interview_service(interview_id, recruiter_id):
    app_id = None

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT i.id, i.application_id, i.status, i.scheduled_at, a.candidate_id, j.job_title
                FROM interviews i
                JOIN applications a ON i.application_id = a.id
                JOIN jobs j ON a.job_id = j.id
                WHERE i.id = %s AND j.recruiter_id = %s
                """,
                (interview_id, recruiter_id),
            )
            interview = cur.fetchone()

            if not interview:
                return {"success": False, "message": "Interview not found or access denied.", "type": "danger"}

            if interview["status"] != "scheduled":
                return {"success": False, "message": "Only scheduled interviews can be completed.", "type": "danger"}

            cur.execute("SELECT NOW() as db_now")
            db_now = cur.fetchone()["db_now"]

            if interview["scheduled_at"] > db_now:
                return {
                    "success": False,
                    "message": "Cannot complete an interview before it happens.",
                    "type": "danger",
                }

            app_id = interview["application_id"]

            cur.execute(
                "UPDATE interviews SET status = 'completed' WHERE id = %s AND status = 'scheduled'", (interview_id,)
            )

            if cur.rowcount == 0:
                return {"success": False, "message": "Interview state changed concurrently.", "type": "danger"}

            conn.commit()

    log_audit_event(
        recruiter_id,
        "interview_completed",
        "interview",
        interview_id,
        {
            "application_id": app_id,
            "previous_interview_status": "scheduled",
            "new_interview_status": "completed",
        },
    )

    return {"success": True, "message": "Interview marked as completed.", "type": "success"}
