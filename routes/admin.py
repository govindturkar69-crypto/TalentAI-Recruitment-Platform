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
            # Global Metrics
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

    metrics = {
        "total_users": total_users,
        "total_candidates": total_candidates,
        "total_recruiters": total_recruiters,
        "total_jobs": total_jobs,
        "total_applications": total_applications,
    }

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
        metrics=metrics,
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
