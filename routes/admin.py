import logging
from contextlib import closing

from flask import Blueprint, flash, redirect, render_template, request, url_for

from core import admin_required, get_db_connection

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            # Metrics
            cur.execute("SELECT COUNT(*) AS total FROM users")
            total_users = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'candidate'")
            total_candidates = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'recruiter'")
            total_recruiters = cur.fetchone()["total"]

            # Users list (safe fields only)
            cur.execute("SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC")
            users = cur.fetchall()

    metrics = {
        "total_users": total_users,
        "total_candidates": total_candidates,
        "total_recruiters": total_recruiters,
    }

    return render_template("admin_dashboard.html", metrics=metrics, users=users)


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def update_role(user_id):
    from flask import session

    if user_id == session.get("user_id"):
        flash("You cannot change your own role.", "danger")
        return redirect(url_for("admin.dashboard"))

    new_role = request.form.get("role")
    if new_role not in ["candidate", "recruiter"]:
        flash("Invalid role specified.", "danger")
        return redirect(url_for("admin.dashboard"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                flash("User not found.", "danger")
                return redirect(url_for("admin.dashboard"))

            cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
            conn.commit()

    flash("User role updated successfully.", "success")
    return redirect(url_for("admin.dashboard"))
