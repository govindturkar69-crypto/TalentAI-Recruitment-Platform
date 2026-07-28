"""Authentication routes: register, login, logout, password reset."""

import secrets
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash

from core import get_db_connection, ADMIN_EMAIL

auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form["name"].strip()
        email    = request.form["email"].strip().lower()
        password = request.form["password"]

        if not all([name, email, password]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("register.html")

        role = "recruiter" if email == ADMIN_EMAIL else "candidate"

        hashed = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
                (name, email, hashed, role)
            )
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception:
            flash("This email is already registered.", "danger")
        finally:
            cur.close()
            conn.close()

    return render_template("register.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"]    = user["name"]
            session["role"]    = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")

            if user["role"] == "recruiter":
                return redirect(url_for("recruiter_dashboard"))
            return redirect(url_for("candidate_dashboard"))

        flash("Incorrect email or password.", "danger")

    return render_template("login.html")


@auth.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=1)
            cur.execute(
                "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s,%s,%s)",
                (user["id"], token, expires_at)
            )
            conn.commit()
            reset_link = url_for("auth.reset_password", token=token, _external=True)
            flash(f"Password reset link generated. Since email sending isn't configured, "
                  f"use this link now: {reset_link}", "info")
        else:
            flash("If that email is registered, a reset link has been generated.", "info")

        cur.close()
        conn.close()
        return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


@auth.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM password_resets WHERE token = %s AND used = FALSE", (token,)
    )
    reset_entry = cur.fetchone()

    if not reset_entry or reset_entry["expires_at"] < datetime.now():
        cur.close()
        conn.close()
        flash("This reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password     = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            cur.close()
            conn.close()
            return render_template("reset_password.html", token=token)

        if len(new_password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            cur.close()
            conn.close()
            return render_template("reset_password.html", token=token)

        hashed = generate_password_hash(new_password)
        cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, reset_entry["user_id"]))
        cur.execute("UPDATE password_resets SET used=TRUE WHERE id=%s", (reset_entry["id"],))
        conn.commit()
        cur.close()
        conn.close()
        flash("Password reset successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    cur.close()
    conn.close()
    return render_template("reset_password.html", token=token)
