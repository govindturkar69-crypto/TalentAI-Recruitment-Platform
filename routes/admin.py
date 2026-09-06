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


def _escape_like(val: str, escape_char: str = "=") -> str:
    """Escapes LIKE special characters in order: escape_char, %, _."""
    return (
        val.replace(escape_char, escape_char + escape_char)
        .replace("%", escape_char + "%")
        .replace("_", escape_char + "_")
    )


def _get_safe_dashboard_params():
    """Extract and normalize whitelisted dashboard parameters for safe redirection."""
    params = {}
    q = request.args.get("q", "").strip()[:100]
    if q:
        params["q"] = q

    role = request.args.get("role", "").strip().lower()
    if role in ("candidate", "recruiter"):
        params["role"] = role

    status = request.args.get("status", "").strip().lower()
    if status in ("active", "inactive"):
        params["status"] = status

    company_id_str = request.args.get("company_id", "").strip()
    try:
        cid = int(company_id_str)
        if cid > 0:
            params["company_id"] = cid
    except (TypeError, ValueError):
        pass

    page_str = request.args.get("page", "").strip()
    try:
        p = int(page_str)
        if p > 0:
            params["page"] = p
    except (TypeError, ValueError):
        pass

    per_page_str = request.args.get("per_page", "").strip()
    try:
        pp = int(per_page_str)
        if pp > 100:
            params["per_page"] = 100
        elif pp > 0:
            params["per_page"] = pp
    except (TypeError, ValueError):
        pass

    return params


def _safe_redirect_dashboard():
    """Redirect safely to admin.dashboard preserving whitelisted filter/pagination state."""
    return redirect(url_for("admin.dashboard", **_get_safe_dashboard_params()))


def _get_platform_analytics(cur):
    """Fetch aggregate platform metrics across users, jobs, applications, interviews, and companies.

    Uses isolated single-table conditional aggregations with COALESCE to ensure
    null/zero safety. Caller provides open cursor; read-only; no commit or write.
    """
    # 1. Users Aggregation
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_users,
            COALESCE(SUM(role = 'candidate'), 0) AS candidates,
            COALESCE(SUM(role = 'recruiter'), 0) AS recruiters,
            COALESCE(SUM(is_active = 1), 0) AS active_users,
            COALESCE(SUM(is_active = 0), 0) AS inactive_users,
            COALESCE(SUM(role = 'recruiter' AND company_id IS NULL), 0) AS unassigned_recruiters
        FROM users
    """
    )
    u_row = cur.fetchone() or {}

    # 2. Jobs Aggregation
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_jobs,
            COALESCE(SUM(is_active = 1), 0) AS active_jobs,
            COALESCE(SUM(is_active = 0), 0) AS inactive_jobs
        FROM jobs
    """
    )
    j_row = cur.fetchone() or {}

    # 3. Applications Pipeline Aggregation
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_applications,
            COALESCE(SUM(status = 'applied'), 0) AS applied,
            COALESCE(SUM(status = 'shortlisted'), 0) AS shortlisted,
            COALESCE(SUM(status = 'rejected'), 0) AS rejected,
            COALESCE(SUM(status = 'hired'), 0) AS hired,
            COALESCE(SUM(status = 'withdrawn'), 0) AS withdrawn
        FROM applications
    """
    )
    a_row = cur.fetchone() or {}

    # 4. Interviews Aggregation
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_interviews,
            COALESCE(SUM(status = 'scheduled'), 0) AS scheduled,
            COALESCE(SUM(status = 'completed'), 0) AS completed,
            COALESCE(SUM(status = 'cancelled'), 0) AS cancelled,
            COALESCE(SUM(status = 'scheduled' AND scheduled_at > NOW()), 0) AS upcoming
        FROM interviews
    """
    )
    i_row = cur.fetchone() or {}

    # 5. Companies Aggregation
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_companies,
            COALESCE(SUM(is_active = 1), 0) AS active_companies,
            COALESCE(SUM(is_active = 0), 0) AS inactive_companies
        FROM companies
    """
    )
    c_row = cur.fetchone() or {}

    # Normalize returned values to plain integers, with fallback to 'total' if mock returns it
    total_users = int(u_row.get("total_users") or u_row.get("total") or 0)
    candidates = int(u_row.get("candidates") or 0)
    recruiters = int(u_row.get("recruiters") or 0)
    active_users = int(u_row.get("active_users") or 0)
    inactive_users = int(u_row.get("inactive_users") or 0)
    unassigned_recruiters = int(u_row.get("unassigned_recruiters") or 0)

    total_jobs = int(j_row.get("total_jobs") or j_row.get("total") or 0)
    active_jobs = int(j_row.get("active_jobs") or 0)
    inactive_jobs = int(j_row.get("inactive_jobs") or 0)

    total_applications = int(a_row.get("total_applications") or a_row.get("total") or 0)
    applied = int(a_row.get("applied") or 0)
    shortlisted = int(a_row.get("shortlisted") or 0)
    rejected = int(a_row.get("rejected") or 0)
    hired = int(a_row.get("hired") or 0)
    withdrawn = int(a_row.get("withdrawn") or 0)

    total_interviews = int(i_row.get("total_interviews") or i_row.get("total") or 0)
    scheduled_interviews = int(i_row.get("scheduled") or 0)
    completed_interviews = int(i_row.get("completed") or 0)
    cancelled_interviews = int(i_row.get("cancelled") or 0)
    upcoming_interviews = int(i_row.get("upcoming") or 0)

    total_companies = int(c_row.get("total_companies") or c_row.get("total") or 0)
    active_companies = int(c_row.get("active_companies") or 0)
    inactive_companies = int(c_row.get("inactive_companies") or 0)

    # Safe percentage calculation (zero-division rule)
    def _calc_pct(count, total):
        if not total or total <= 0:
            return 0.0
        return round((count / total) * 100, 1)

    pipeline_percentages = {
        "applied": _calc_pct(applied, total_applications),
        "shortlisted": _calc_pct(shortlisted, total_applications),
        "hired": _calc_pct(hired, total_applications),
        "rejected": _calc_pct(rejected, total_applications),
        "withdrawn": _calc_pct(withdrawn, total_applications),
    }

    platform_metrics = {
        "total_users": total_users,
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "total_interviews": total_interviews,
        "active_companies": active_companies,
        "total_candidates": candidates,
        "total_recruiters": recruiters,
    }

    application_metrics = {
        "total": total_applications,
        "applied": applied,
        "shortlisted": shortlisted,
        "hired": hired,
        "rejected": rejected,
        "withdrawn": withdrawn,
        "percentages": pipeline_percentages,
    }

    interview_metrics = {
        "total": total_interviews,
        "scheduled": scheduled_interviews,
        "upcoming": upcoming_interviews,
        "completed": completed_interviews,
        "cancelled": cancelled_interviews,
    }

    operational_metrics = {
        "active_users": active_users,
        "inactive_users": inactive_users,
        "total_candidates": candidates,
        "total_recruiters": recruiters,
        "unassigned_recruiters": unassigned_recruiters,
        "active_jobs": active_jobs,
        "inactive_jobs": inactive_jobs,
        "total_companies": total_companies,
        "active_companies": active_companies,
        "inactive_companies": inactive_companies,
    }

    return {
        "platform_metrics": platform_metrics,
        "application_metrics": application_metrics,
        "interview_metrics": interview_metrics,
        "operational_metrics": operational_metrics,
    }


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    # 1. Parse and normalize query parameters
    raw_q = request.args.get("q", "").strip()
    q = raw_q[:100]

    raw_role = request.args.get("role", "").strip().lower()
    role = raw_role if raw_role in ("candidate", "recruiter") else ""

    raw_status = request.args.get("status", "").strip().lower()
    status = raw_status if raw_status in ("active", "inactive") else ""

    company_id = None
    company_id_str = request.args.get("company_id", "").strip()
    try:
        cid = int(company_id_str)
        if cid > 0:
            company_id = cid
    except (TypeError, ValueError):
        company_id = None

    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = int(request.args.get("per_page", 20))
        if per_page < 1:
            per_page = 20
        elif per_page > 100:
            per_page = 100
    except (TypeError, ValueError):
        per_page = 20

    # 2. Build WHERE clauses and parameters safely
    where_clauses = []
    params = []

    if q:
        escaped_q = _escape_like(q, "=")
        pattern = f"%{escaped_q}%"
        where_clauses.append("(u.name LIKE %s ESCAPE '=' OR u.email LIKE %s ESCAPE '=')")
        params.extend([pattern, pattern])

    if role:
        where_clauses.append("u.role = %s")
        params.append(role)

    if status == "active":
        where_clauses.append("u.is_active = %s")
        params.append(True)
    elif status == "inactive":
        where_clauses.append("u.is_active = %s")
        params.append(False)

    if company_id:
        where_clauses.append("u.company_id = %s")
        params.append(company_id)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            # Platform Analytics
            analytics = _get_platform_analytics(cur)
            platform_metrics = analytics["platform_metrics"]
            application_metrics = analytics["application_metrics"]
            interview_metrics = analytics["interview_metrics"]
            operational_metrics = analytics["operational_metrics"]

            # Filtered User Count
            count_query = f"SELECT COUNT(*) AS total FROM users u {where_sql}".strip()
            cur.execute(count_query, tuple(params))
            filtered_total = cur.fetchone()["total"]

            # Page normalization
            if filtered_total == 0:
                page = 1
                total_pages = 1
                offset = 0
                users = []
            else:
                total_pages = (filtered_total + per_page - 1) // per_page
                if page > total_pages:
                    page = total_pages
                offset = (page - 1) * per_page

                # Fetch paginated users (safe fields only, stable ordering)
                select_query = f"""
                    SELECT u.id, u.name, u.email, u.role, u.is_active, u.created_at,
                           u.company_id, c.name as company_name
                    FROM users u
                    LEFT JOIN companies c ON u.company_id = c.id
                    {where_sql}
                    ORDER BY u.created_at DESC, u.id DESC
                    LIMIT %s OFFSET %s
                """.strip()
                cur.execute(select_query, tuple(params + [per_page, offset]))
                users = cur.fetchall()

            # Company metadata for filter & recruiter assignment
            cur.execute("SELECT id, name, is_active FROM companies ORDER BY name ASC")
            companies = cur.fetchall()

            # Recent registrations (safe fields only)
            cur.execute("SELECT name, email, role, created_at FROM users ORDER BY created_at DESC LIMIT 5")
            recent_users = cur.fetchall()

    window_start = max(1, page - 2)
    window_end = min(total_pages, page + 2)
    page_numbers = list(range(window_start, window_end + 1))

    pagination = {
        "page": page,
        "per_page": per_page,
        "total": filtered_total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
        "start_idx": offset + 1 if filtered_total > 0 else 0,
        "end_idx": min(offset + per_page, filtered_total) if filtered_total > 0 else 0,
        "page_numbers": page_numbers,
    }

    filters = {
        "q": q,
        "role": role,
        "status": status,
        "company_id": company_id if company_id else "",
        "per_page": per_page,
    }

    active_filters = {}
    if q:
        active_filters["q"] = q
    if role:
        active_filters["role"] = role
    if status:
        active_filters["status"] = status
    if company_id:
        active_filters["company_id"] = company_id
    if per_page != 20 or "per_page" in request.args:
        active_filters["per_page"] = per_page

    return render_template(
        "admin_dashboard.html",
        metrics=platform_metrics,
        platform_metrics=platform_metrics,
        application_metrics=application_metrics,
        interview_metrics=interview_metrics,
        operational_metrics=operational_metrics,
        users=users,
        recent_users=recent_users,
        companies=companies,
        pagination=pagination,
        filters=filters,
        active_filters=active_filters,
    )


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def update_role(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot change your own role.", "danger")
        return _safe_redirect_dashboard()

    new_role = request.form.get("role")
    if new_role not in ["candidate", "recruiter"]:
        flash("Invalid role specified.", "danger")
        return _safe_redirect_dashboard()

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                flash("User not found.", "danger")
                return _safe_redirect_dashboard()

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
    return _safe_redirect_dashboard()


@admin_bp.route("/users/<int:user_id>/status", methods=["POST"])
@admin_required
def update_status(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot deactivate your own account.", "danger")
        return _safe_redirect_dashboard()

    new_status = request.form.get("status")
    if new_status not in ["active", "inactive"]:
        flash("Invalid status specified.", "danger")
        return _safe_redirect_dashboard()

    is_active_val = new_status == "active"

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, email, is_active FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                flash("User not found.", "danger")
                return _safe_redirect_dashboard()

            admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
            if admin_email and user["email"].strip().lower() == admin_email and not is_active_val:
                flash("The primary admin account cannot be deactivated.", "danger")
                return _safe_redirect_dashboard()

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
    return _safe_redirect_dashboard()


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
            return _safe_redirect_dashboard()

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id, role, company_id FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                flash("User not found.", "danger")
                return _safe_redirect_dashboard()

            if user["role"] != "recruiter":
                flash("Company assignment is only allowed for recruiters.", "danger")
                return _safe_redirect_dashboard()

            if company_id is not None:
                cur.execute("SELECT id, is_active FROM companies WHERE id = %s", (company_id,))
                company = cur.fetchone()
                if not company:
                    flash("Company not found.", "danger")
                    return _safe_redirect_dashboard()
                if not company.get("is_active", True):
                    flash("Cannot assign inactive company.", "danger")
                    return _safe_redirect_dashboard()

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
    return _safe_redirect_dashboard()


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
