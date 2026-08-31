from contextlib import closing

from core import get_db_connection


def get_recruiter_analytics():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("""
                SELECT a.*, u.name AS candidate_name, j.job_title
                FROM applications a
                JOIN users u ON a.candidate_id = u.id
                JOIN jobs  j ON a.job_id = j.id
            """)
            applications = cur.fetchall()

    apps_data = [dict(a) for a in applications]
    stats = {
        "total": len(apps_data),
        "avg_score": round(sum(a.get("score", 0) for a in apps_data) / max(len(apps_data), 1), 1),
        "shortlisted": sum(1 for a in apps_data if a.get("status") == "shortlisted"),
        "hired": sum(1 for a in apps_data if a.get("status") == "hired"),
    }
    return apps_data, stats
