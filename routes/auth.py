"""Authentication routes: register, login, logout, password reset."""

import logging
import secrets
from contextlib import closing
from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():
    # Rate limiting is applied via the limiter in app.py
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not all([name, email, password]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("register.html")

        if email == current_app.config.get("ADMIN_EMAIL"):
            # L1: Generic message to prevent account enumeration, and securely block public admin registration.
            flash("Registration could not be completed. The email may already be in use.", "danger")
            return render_template("register.html")

        role = "candidate"

        hashed = generate_password_hash(password)
        with closing(get_db_connection()) as conn:
            with closing(conn.cursor()) as cur:
                try:
                    cur.execute(
                        "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
                        (name, email, hashed, role),
                    )
                    conn.commit()
                    flash("Registration successful! Please log in.", "success")
                    return redirect(url_for("auth.login"))
                except Exception:
                    # L1: Generic message to prevent account enumeration
                    flash(
                        "Registration could not be completed. The email may already be in use.",
                        "danger",
                    )

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        with closing(get_db_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cur.fetchone()

        if user and check_password_hash(user["password"], password):
            if not user.get("is_active", True):
                flash("Your account has been deactivated.", "danger")
                return render_template("login.html")

            session.clear()  # Prevent session fixation
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
            user_email = (user["email"] or "").strip().lower()
            session["is_admin"] = bool(admin_email and user_email == admin_email)

            session.permanent = True  # M4: Use PERMANENT_SESSION_LIFETIME
            flash(f"Welcome back, {user['name']}!", "success")

            if session.get("is_admin"):
                return redirect(url_for("admin.dashboard"))
            elif user["role"] == "recruiter":
                return redirect(url_for("recruiter.recruiter_dashboard"))
            else:
                return redirect(url_for("candidate.candidate_dashboard"))

        flash("Incorrect email or password.", "danger")

    return render_template("login.html")


@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        with closing(get_db_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                user = cur.fetchone()

                if user:
                    # L2: Invalidate any previous unused tokens for this user
                    cur.execute(
                        "UPDATE password_resets SET used = TRUE WHERE user_id = %s AND used = FALSE",
                        (user["id"],),
                    )
                    token = secrets.token_urlsafe(32)
                    expires_at = datetime.now() + timedelta(hours=1)
                    cur.execute(
                        "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s,%s,%s)",
                        (user["id"], token, expires_at),
                    )
                    conn.commit()
                    # Generate reset URL and send email
                    app_base_url = Config.APP_BASE_URL
                    if Config.APP_ENV == "production" and not app_base_url:
                        logger.error(
                            "Configuration error: APP_BASE_URL is missing in production. "
                            "Cannot send password reset email."
                        )
                    else:
                        if not app_base_url:
                            app_base_url = request.host_url.rstrip("/")
                        else:
                            app_base_url = app_base_url.rstrip("/")

                        reset_url = f"{app_base_url}{url_for('auth.reset_password', token=token)}"
                        send_password_reset_email(user["email"], reset_url)

        # Always show the same message regardless of whether the email exists
        flash(
            "If that email is registered, a password reset link has been sent.",
            "info",
        )
        return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


@auth.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT * FROM password_resets WHERE token = %s AND used = FALSE", (token,))
            reset_entry = cur.fetchone()

            if not reset_entry or reset_entry["expires_at"] < datetime.now():
                flash("This reset link is invalid or has expired.", "danger")
                return redirect(url_for("auth.forgot_password"))

            if request.method == "POST":
                new_password = request.form["password"]
                confirm_password = request.form["confirm_password"]

                if new_password != confirm_password:
                    flash("Passwords do not match.", "danger")
                    return render_template("reset_password.html", token=token)

                if len(new_password) < 8:
                    flash("Password must be at least 8 characters long.", "danger")
                    return render_template("reset_password.html", token=token)

                hashed = generate_password_hash(new_password)
                cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, reset_entry["user_id"]))
                cur.execute("UPDATE password_resets SET used=TRUE WHERE id=%s", (reset_entry["id"],))
                conn.commit()

                # M3: Clear the current session so any stolen session is invalidated
                # for this browser. Note: Flask signed-cookie sessions on other
                # browsers cannot be server-side invalidated without schema changes.
                session.clear()

                flash("Password reset successful! Please log in.", "success")
                return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)


@auth.route("/settings", methods=["GET", "POST"])
def settings():
    # Defer import to avoid circular dependency
    from core import login_required
    
    @login_required()
    def _settings():
        if request.method == "POST":
            current_password = request.form.get("current_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")

            if not current_password or not new_password or not confirm_password:
                flash("All fields are required.", "danger")
                return redirect(url_for("auth.settings"))

            if new_password != confirm_password:
                flash("New passwords do not match.", "danger")
                return redirect(url_for("auth.settings"))

            if len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "danger")
                return redirect(url_for("auth.settings"))

            with closing(get_db_connection()) as conn:
                with closing(conn.cursor()) as cur:
                    cur.execute("SELECT password FROM users WHERE id = %s", (session["user_id"],))
                    user = cur.fetchone()

                    if not user or not check_password_hash(user["password"], current_password):
                        flash("Incorrect current password.", "danger")
                        return redirect(url_for("auth.settings"))

                    hashed = generate_password_hash(new_password)
                    cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, session["user_id"]))
                    conn.commit()

            session.clear()
            flash("Password updated successfully. Please log in again.", "success")
            return redirect(url_for("auth.login"))

        return render_template("settings.html")
    
    return _settings()


# Deferred import to avoid circular dependency
from core import get_db_connection  # noqa: E402
