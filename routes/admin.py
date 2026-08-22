import logging
from contextlib import closing

from flask import Blueprint, flash, redirect, render_template, request, url_for, session, current_app

from core import admin_required, get_db_connection
from services.audit_service import log_audit_event

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

            cur.execute("SELECT COUNT(*) AS total FROM jobs")
            total_jobs = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS total FROM applications")
            total_applications = cur.fetchone()["total"]

            # Users list (safe fields only)
            cur.execute("SELECT id, name, email, role, is_active, created_at FROM users ORDER BY created_at DESC")
            users = cur.fetchall()

            # Recent registrations (safe fields only)
            cur.execute("SELECT name, email, role, created_at FROM users ORDER BY created_at DESC LIMIT 5")
            recent_users = cur.fetchall()

    metrics = {
        "total_users": total_users,
        "total_candidates": total_candidates,
        "total_recruiters": total_recruiters,
        "total_jobs": total_jobs,
        "total_applications": total_applications,
    }

    return render_template("admin_dashboard.html", metrics=metrics, users=users, recent_users=recent_users)


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
            cur.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("admin.dashboard"))

            cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
            conn.commit()
            
            log_audit_event(
                actor_user_id=session.get("user_id"),
                action="update_user_role",
                target_type="user",
                target_id=user_id,
                details={
                    "previous_role": user["role"],
                    "new_role": new_role
                }
            )

    flash("User role updated successfully.", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/users/<int:user_id>/status", methods=["POST"])
@admin_required
def update_status(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("admin.dashboard"))

    new_status = request.form.get("status")
    if new_status not in ["active", "inactive"]:
        flash("Invalid status specified.", "danger")
        return redirect(url_for("admin.dashboard"))

    is_active_val = (new_status == "active")

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, email, is_active FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("admin.dashboard"))

            admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
            if admin_email and user["email"].strip().lower() == admin_email and not is_active_val:
                flash("The primary admin account cannot be deactivated.", "danger")
                return redirect(url_for("admin.dashboard"))

            cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (is_active_val, user_id))
            conn.commit()

            log_audit_event(
                actor_user_id=session.get("user_id"),
                action="update_user_status",
                target_type="user",
                target_id=user_id,
                details={
                    "is_active_before": user["is_active"],
                    "is_active_after": is_active_val
                }
            )

    flash(f"User account {'activated' if is_active_val else 'deactivated'} successfully.", "success")
    return redirect(url_for("admin.dashboard"))
