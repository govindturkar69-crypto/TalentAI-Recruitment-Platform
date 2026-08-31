import logging
import urllib.parse
from contextlib import closing

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from core import admin_required, get_db_connection
from services.audit_service import log_audit_event

logger = logging.getLogger(__name__)


def is_valid_url(url_str):
    if not url_str:
        return True
    try:
        parsed = urllib.parse.urlparse(url_str)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname)
    except (TypeError, ValueError):
        return False


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
            cur.execute(
                """
                SELECT u.id, u.name, u.email, u.role, u.is_active, u.created_at,
                       u.company_id, c.name as company_name
                FROM users u
                LEFT JOIN companies c ON u.company_id = c.id
                ORDER BY u.created_at DESC
            """
            )
            users = cur.fetchall()

            # Fetch active companies for recruiter assignment dropdown
            cur.execute("SELECT id, name FROM companies WHERE is_active = TRUE ORDER BY name ASC")
            companies = cur.fetchall()

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

    return render_template(
        "admin_dashboard.html",
        metrics=metrics,
        users=users,
        recent_users=recent_users,
        companies=companies,
    )


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
                details={"previous_role": user["role"], "new_role": new_role},
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

    is_active_val = new_status == "active"

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
                details={"is_active_before": user["is_active"], "is_active_after": is_active_val},
            )

    flash(f"User account {'activated' if is_active_val else 'deactivated'} successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/company", methods=["POST"])
@admin_required
def assign_company(user_id):
    company_id_str = request.form.get("company_id")
    if not company_id_str or not company_id_str.strip():
        company_id = None
    else:
        try:
            company_id = int(company_id_str)
            if company_id <= 0:
                raise ValueError("Invalid ID")
        except (TypeError, ValueError):
            flash("Invalid company selection.", "danger")
            return redirect(url_for("admin.dashboard"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, role, company_id FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("admin.dashboard"))

            if user["role"] != "recruiter":
                flash("Company assignment is only allowed for recruiters.", "danger")
                return redirect(url_for("admin.dashboard"))

            if company_id is not None:
                cur.execute("SELECT id, is_active FROM companies WHERE id = %s", (company_id,))
                company = cur.fetchone()
                if not company:
                    flash("Company not found.", "danger")
                    return redirect(url_for("admin.dashboard"))
                if not company.get("is_active", True):
                    flash("Cannot assign inactive company.", "danger")
                    return redirect(url_for("admin.dashboard"))

            cur.execute("UPDATE users SET company_id = %s WHERE id = %s", (company_id, user_id))
            conn.commit()

            log_audit_event(
                actor_user_id=session.get("user_id"),
                action="assign_recruiter_company",
                target_type="user",
                target_id=user_id,
                details={"previous_company_id": user["company_id"], "new_company_id": company_id},
            )

    flash("Recruiter company assigned successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/companies")
@admin_required
def list_companies():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT c.id, c.name, c.description, c.website, c.is_active, c.created_at, c.updated_at,
                       (SELECT COUNT(*) FROM users u
                        WHERE u.company_id = c.id AND u.role = 'recruiter') as recruiter_count
                FROM companies c
                ORDER BY c.name ASC
            """
            )
            companies = cur.fetchall()
    return render_template("admin_companies.html", companies=companies)


@admin_bp.route("/companies/create", methods=["POST"])
@admin_required
def create_company():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    website = request.form.get("website", "").strip()

    if not name or len(name) > 255:
        flash("Valid company name is required.", "danger")
        return redirect(url_for("admin.list_companies"))

    if not is_valid_url(website):
        flash("Website must be a valid http:// or https:// URL.", "danger")
        return redirect(url_for("admin.list_companies"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO companies (name, description, website, is_active) VALUES (%s, %s, %s, TRUE)",
                (name, description, website),
            )
            company_id = cur.lastrowid
            conn.commit()

            log_audit_event(
                actor_user_id=session.get("user_id"),
                action="create_company",
                target_type="company",
                target_id=company_id,
                details={"company_name": name},
            )

    flash("Company created successfully.", "success")
    return redirect(url_for("admin.list_companies"))


@admin_bp.route("/companies/<int:company_id>/edit", methods=["POST"])
@admin_required
def edit_company(company_id):
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    website = request.form.get("website", "").strip()

    if not name or len(name) > 255:
        flash("Valid company name is required.", "danger")
        return redirect(url_for("admin.list_companies"))

    if not is_valid_url(website):
        flash("Website must be a valid http:// or https:// URL.", "danger")
        return redirect(url_for("admin.list_companies"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, name FROM companies WHERE id = %s", (company_id,))
            company = cur.fetchone()
            if not company:
                flash("Company not found.", "danger")
                return redirect(url_for("admin.list_companies"))

            cur.execute(
                "UPDATE companies SET name = %s, description = %s, website = %s WHERE id = %s",
                (name, description, website, company_id),
            )
            conn.commit()

            log_audit_event(
                actor_user_id=session.get("user_id"),
                action="update_company",
                target_type="company",
                target_id=company_id,
                details={"previous_name": company["name"], "new_name": name},
            )

    flash("Company updated successfully.", "success")
    return redirect(url_for("admin.list_companies"))
