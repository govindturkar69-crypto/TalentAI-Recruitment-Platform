import logging
import os
from contextlib import closing
from urllib.parse import urlparse

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect

from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

from config import Config
from core import get_db_connection, login_required
from routes.admin import admin_bp
from routes.analytics import analytics_bp

# Blueprints
from routes.auth import auth as auth_blueprint
from routes.candidate import candidate_bp
from routes.recruiter import recruiter_bp

app = Flask(__name__)
app.config.from_object(Config)

if Config.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=Config.SENTRY_DSN,
        integrations=[FlaskIntegration()],
        environment=Config.APP_ENV,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )

# Ensure UPLOAD_FOLDER exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# CSRF protection for all POST forms
csrf = CSRFProtect(app)

# Rate limiter — in-memory storage suitable for single-instance deployment.
# For distributed deployments, configure a shared backend (e.g. Redis).
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

app.register_blueprint(auth_blueprint)
app.register_blueprint(candidate_bp)
app.register_blueprint(recruiter_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(admin_bp)

# H6: Apply rate limits to auth endpoints
limiter.limit("5/minute")(app.view_functions["auth.login"])
limiter.limit("5/hour")(app.view_functions["auth.register"])
limiter.limit("3/hour")(app.view_functions["auth.forgot_password"])
limiter.limit("3/day")(app.view_functions["candidate.analyze_resume_api"])


# ---------------------------------------------------------------------------
# Security helper
# ---------------------------------------------------------------------------
def is_safe_redirect_url(target):
    """Return True only if *target* is a relative URL on the same host."""
    if not target:
        return False
    parsed = urlparse(target)
    # Relative URL (no scheme/host) is always safe
    if not parsed.scheme and not parsed.netloc:
        return True
    # Absolute URL must match our host
    host = urlparse(request.host_url)
    return parsed.scheme in ("http", "https") and parsed.netloc == host.netloc


def safe_redirect(fallback):
    """Redirect to request.referrer only if it is same-origin, else *fallback*."""
    ref = request.referrer
    if is_safe_redirect_url(ref):
        return redirect(ref)
    return redirect(fallback)


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# ---------------------------------------------------------------------------
# Context processor — unread notification count
# ---------------------------------------------------------------------------
@app.context_processor
def inject_unread_count():
    if "user_id" not in session:
        return {"unread_count": 0}
    # Cache the count on g so a template can read it multiple times per request.
    if "unread_count" in g:
        return {"unread_count": g.unread_count}
    try:
        with closing(get_db_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = FALSE",
                    (session["user_id"],),
                )
                count = int(cur.fetchone()["cnt"])
        g.unread_count = count
        return {"unread_count": count}
    except Exception:
        return {"unread_count": 0}


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("errors/500.html"), 500


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    try:
        with closing(get_db_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception:
        return jsonify({"status": "error", "database": "unreachable"}), 503


# ---------------------------------------------------------------------------
# Authenticated routes
# ---------------------------------------------------------------------------
@app.route("/notifications")
@login_required()
def notifications():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
                (session["user_id"],),
            )
            notifs = cur.fetchall()
    return render_template("notifications.html", notifications=notifs)


@app.route("/notifications/mark_all_read", methods=["POST"])
@login_required()
def mark_all_read():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE notifications SET is_read = TRUE WHERE user_id = %s", (session["user_id"],))
            conn.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications"))


# ---------------------------------------------------------------------------
# API endpoints — H2: require auth, filter active only
# ---------------------------------------------------------------------------
@app.route("/api/jobs")
@login_required()
def api_jobs():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id, job_title, required_skills, location, experience " "FROM jobs WHERE is_active = TRUE"
            )
            jobs = cur.fetchall()
    return jsonify(jobs)


# ---------------------------------------------------------------------------
# H1: require auth + ownership check for candidate score API
# ---------------------------------------------------------------------------
@app.route("/api/candidate/<int:user_id>/score")
@login_required()
def api_candidate_score(user_id):
    # Candidates may only view their own scores
    if session.get("role") == "candidate" and session["user_id"] != user_id:
        return jsonify({"error": "Not found"}), 404
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT a.score, j.job_title FROM applications a
                JOIN jobs j ON a.job_id = j.id WHERE a.candidate_id = %s
            """,
                (user_id,),
            )
            data = cur.fetchall()
    return jsonify(data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = app.config.get("FLASK_DEBUG", False)
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
