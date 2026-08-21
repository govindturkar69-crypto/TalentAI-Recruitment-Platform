import os
from contextlib import closing

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from core import get_db_connection, login_required
from services.ai_resume_service import analyze_resume
from services.candidate_service import (
    apply_for_job_service,
    get_job_recommendations_service,
    process_resume_upload,
    withdraw_application_service,
)
from models.resume_parser import get_final_score

candidate_bp = Blueprint("candidate", __name__)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"pdf"}


@candidate_bp.route("/candidate/dashboard")
@login_required(role="candidate")
def candidate_dashboard():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT a.*, j.job_title, j.location, j.experience
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.candidate_id = %s
                ORDER BY a.applied_at DESC
            """,
                (session["user_id"],),
            )
            applications = cur.fetchall()

            cur.execute("SELECT * FROM jobs WHERE is_active = TRUE ORDER BY created_at DESC")
            jobs = cur.fetchall()

            cur.execute(
                "SELECT * FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (session["user_id"],)
            )
            resume = cur.fetchone()

            cur.execute("SELECT job_id FROM saved_jobs WHERE candidate_id = %s", (session["user_id"],))
            saved_job_ids = {row["job_id"] for row in cur.fetchall()}

    return render_template(
        "candidate_dashboard.html", applications=applications, jobs=jobs, resume=resume, saved_job_ids=saved_job_ids
    )


@candidate_bp.route("/candidate/upload_resume", methods=["GET", "POST"])
@login_required(role="candidate")
def upload_resume():
    if request.method == "POST":
        if "resume" not in request.files:
            flash("Please select a file.", "danger")
            return redirect(request.url)

        file = request.files["resume"]
        if file.filename == "" or not allowed_file(file.filename):
            flash("Only PDF files are allowed.", "danger")
            return redirect(request.url)

        filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
        save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        skills, skills_str = process_resume_upload(session["user_id"], save_path, filename)

        flash(f"Resume uploaded! {len(skills)} skills found: {skills_str}", "success")
        return redirect(url_for("candidate.candidate_dashboard"))

    return render_template("upload_resume.html")


@candidate_bp.route("/candidate/apply/<int:job_id>", methods=["POST"])
@login_required(role="candidate")
def apply_job(job_id):
    result = apply_for_job_service(session["user_id"], session["name"], job_id)
    flash(result["message"], result["type"])
    return redirect(url_for("candidate.candidate_dashboard"))


@candidate_bp.route("/candidate/withdraw/<int:app_id>", methods=["POST"])
@login_required(role="candidate")
def withdraw_application(app_id):
    result = withdraw_application_service(app_id, session["user_id"])
    flash(result["message"], result["type"])
    return redirect(url_for("candidate.candidate_dashboard"))


@candidate_bp.route("/candidate/save_job/<int:job_id>", methods=["POST"])
@login_required(role="candidate")
def save_job(job_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            try:
                cur.execute(
                    "INSERT INTO saved_jobs (candidate_id, job_id) VALUES (%s,%s)", (session["user_id"], job_id)
                )
                conn.commit()
                flash("Job saved for later.", "success")
            except Exception:
                flash("This job is already in your saved list.", "info")

    from app import safe_redirect

    return safe_redirect(url_for("candidate.candidate_dashboard"))


@candidate_bp.route("/candidate/unsave_job/<int:job_id>", methods=["POST"])
@login_required(role="candidate")
def unsave_job(job_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("DELETE FROM saved_jobs WHERE candidate_id=%s AND job_id=%s", (session["user_id"], job_id))
            conn.commit()

    from app import safe_redirect

    flash("Job removed from saved list.", "info")
    return safe_redirect(url_for("candidate.saved_jobs_page"))


@candidate_bp.route("/candidate/saved_jobs")
@login_required(role="candidate")
def saved_jobs_page():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT j.*, s.saved_at FROM saved_jobs s
                JOIN jobs j ON s.job_id = j.id
                WHERE s.candidate_id = %s ORDER BY s.saved_at DESC
            """,
                (session["user_id"],),
            )
            saved = cur.fetchall()

    return render_template("saved_jobs.html", saved_jobs=saved)


@candidate_bp.route("/candidate/profile", methods=["GET", "POST"])
@login_required(role="candidate")
def candidate_profile():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            if request.method == "POST":
                bio = request.form.get("bio", "").strip()
                phone = request.form.get("phone", "").strip()
                location = request.form.get("location", "").strip()
                experience_years = request.form.get("experience_years", "").strip()
                linkedin_url = request.form.get("linkedin_url", "").strip()
                github_url = request.form.get("github_url", "").strip()
                portfolio_url = request.form.get("portfolio_url", "").strip()

                # L4: Validate profile URLs — allow only http(s) schemes
                for url_val in (linkedin_url, github_url, portfolio_url):
                    if url_val and not url_val.startswith(("https://", "http://")):
                        flash("Profile URLs must start with https:// or http://.", "danger")
                        return redirect(url_for("candidate.candidate_profile"))

                cur.execute("SELECT id FROM candidate_profiles WHERE user_id = %s", (session["user_id"],))
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE candidate_profiles SET bio=%s, phone=%s, location=%s,
                        experience_years=%s, linkedin_url=%s, github_url=%s, portfolio_url=%s
                        WHERE user_id=%s
                    """,
                        (
                            bio,
                            phone,
                            location,
                            experience_years,
                            linkedin_url,
                            github_url,
                            portfolio_url,
                            session["user_id"],
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO candidate_profiles
                        (user_id, bio, phone, location, experience_years, linkedin_url, github_url, portfolio_url)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                        (
                            session["user_id"],
                            bio,
                            phone,
                            location,
                            experience_years,
                            linkedin_url,
                            github_url,
                            portfolio_url,
                        ),
                    )
                conn.commit()
                flash("Profile updated successfully!", "success")
                return redirect(url_for("candidate.candidate_profile"))

            cur.execute("SELECT * FROM candidate_profiles WHERE user_id = %s", (session["user_id"],))
            profile = cur.fetchone()
            cur.execute(
                "SELECT * FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (session["user_id"],)
            )
            resume = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS cnt FROM applications WHERE candidate_id = %s", (session["user_id"],))
            application_count = cur.fetchone()["cnt"]

    fields = ["bio", "phone", "location", "experience_years", "linkedin_url"]
    filled = sum(1 for f in fields if profile and profile.get(f)) if profile else 0
    profile_completion = int(((filled + (1 if resume else 0)) / (len(fields) + 1)) * 100)

    return render_template(
        "candidate_profile.html",
        profile=profile,
        resume=resume,
        application_count=application_count,
        profile_completion=profile_completion,
    )


@candidate_bp.route("/candidate/recommendations")
@login_required(role="candidate")
def job_recommendations():
    resume, recommendations = get_job_recommendations_service(session["user_id"])
    return render_template("job_recommendations.html", resume=resume, recommendations=recommendations)


@candidate_bp.route("/resume/suggestions")
@login_required(role="candidate")
def resume_suggestions():
    has_resume = False
    jobs = []

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", (session["user_id"],)
            )
            if cur.fetchone():
                has_resume = True

            # Fetch active jobs for target selection
            cur.execute(
                "SELECT id, job_title, location FROM jobs WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 50"
            )
            jobs = cur.fetchall()

    return render_template("resume_suggestions.html", has_resume=has_resume, jobs=jobs)


@candidate_bp.route("/api/resume/score_local", methods=["POST"])
@login_required(role="candidate")
def score_local_api():
    req_data = request.get_json(silent=True) or {}
    target_job_id = req_data.get("job_id")

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT raw_text, skills FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                (session["user_id"],),
            )
            resume_record = cur.fetchone()

            if not resume_record:
                return jsonify({"error": "No resume found. Please upload a resume first."}), 400

            candidate_skills = resume_record["skills"].split(",") if resume_record["skills"] else []

            if target_job_id:
                try:
                    job_id_int = int(target_job_id)
                except ValueError:
                    return jsonify({"error": "Invalid job ID provided."}), 400

                cur.execute(
                    "SELECT job_title, required_skills, description FROM jobs WHERE id = %s AND is_active = TRUE",
                    (job_id_int,),
                )
                job_record = cur.fetchone()
                
                if not job_record:
                    return jsonify({"error": "Selected target job not found or inactive."}), 400
                
                result = get_final_score(
                    resume_record["raw_text"], candidate_skills, job_record["required_skills"], job_record["description"] or ""
                )
                
                return jsonify({
                    "success": True,
                    "mode": "job_specific",
                    "match_score": result["final_score"],
                    "matched_skills": result["matched"],
                    "missing_skills": result["missing"]
                })
            
            else:
                return jsonify({
                    "success": True,
                    "mode": "general",
                    "skills": candidate_skills
                })


@candidate_bp.route("/api/resume/analyze", methods=["POST"])
@login_required(role="candidate")
def analyze_resume_api():
    req_data = request.get_json(silent=True) or {}
    target_job_id = req_data.get("job_id")

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT raw_text FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                (session["user_id"],),
            )
            resume_record = cur.fetchone()

            if not resume_record or not resume_record["raw_text"]:
                return jsonify({"error": "No resume found. Please upload a resume first."}), 400

            job_text = None
            if target_job_id:
                cur.execute(
                    "SELECT job_title, required_skills, description FROM jobs WHERE id = %s AND is_active = TRUE",
                    (target_job_id,),
                )
                job_record = cur.fetchone()
                if job_record:
                    job_text = (
                        f"Title: {job_record['job_title']}\n"
                        f"Skills Required: {job_record['required_skills']}\n"
                        f"Description: {job_record['description']}"
                    )
                else:
                    return jsonify({"error": "Selected target job not found or inactive."}), 400

    # Generate analysis via AI Service
    result = analyze_resume(resume_record["raw_text"], job_text)

    # AI service returns a dictionary matching the schema, or a dict with "error"
    if "error" in result:
        return jsonify({"error": result["error"]}), 500

    return jsonify(result)
