import os
from contextlib import closing

import pymysql
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from core import get_db_connection, login_required
from models.resume_parser import get_final_score
from services.ai_resume_service import analyze_resume
from services.candidate_service import (
    apply_for_job_service,
    get_job_recommendations_service,
    process_resume_upload,
    withdraw_application_service,
)

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
            cur.execute("SELECT id FROM jobs WHERE id = %s", (job_id,))
            if not cur.fetchone():
                flash("Job not found.", "danger")
                return redirect(url_for("candidate.candidate_dashboard"))

            try:
                cur.execute(
                    "INSERT INTO saved_jobs (candidate_id, job_id) VALUES (%s,%s)", (session["user_id"], job_id)
                )
                conn.commit()
                flash("Job saved for later.", "success")
            except pymysql.err.IntegrityError:
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

                # L4: Validate profile URLs — allow only valid http(s) schemes
                for url_val in (linkedin_url, github_url, portfolio_url):
                    if not validate_url(url_val):
                        flash("Profile URLs must be valid http(s) links.", "danger")
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

            cur.execute(
                "SELECT * FROM candidate_education WHERE user_id = %s ORDER BY start_date DESC", (session["user_id"],)
            )
            education_list = cur.fetchall()

            cur.execute(
                "SELECT * FROM candidate_experience WHERE user_id = %s ORDER BY start_date DESC", (session["user_id"],)
            )
            experience_list = cur.fetchall()

            cur.execute(
                "SELECT * FROM candidate_projects WHERE user_id = %s ORDER BY created_at DESC", (session["user_id"],)
            )
            projects_list = cur.fetchall()

            cur.execute(
                "SELECT * FROM candidate_certifications WHERE user_id = %s ORDER BY issue_date DESC",
                (session["user_id"],),
            )
            certifications_list = cur.fetchall()

            cur.execute(
                "SELECT * FROM candidate_achievements WHERE user_id = %s ORDER BY achieved_date DESC",
                (session["user_id"],),
            )
            achievements_list = cur.fetchall()

    # Profile Completion Formula
    core = 0
    fields = ["bio", "phone", "location", "linkedin_url", "github_url", "portfolio_url"]
    filled = sum(1 for f in fields if profile and profile.get(f)) if profile else 0
    core += int((filled / len(fields)) * 30)

    if resume:
        core += 20

    # Skills resolution: Curated > Resume
    has_skills = False
    resolved_skills = ""
    if profile and profile.get("skills"):
        resolved_skills = profile.get("skills")
        has_skills = True
    elif resume and resume.get("skills"):
        resolved_skills = resume.get("skills")
        has_skills = True

    if has_skills:
        core += 15

    if education_list:
        core += 15

    optional = 0
    if experience_list:
        optional += 10
    if projects_list:
        optional += 10
    if certifications_list:
        optional += 5
    if achievements_list:
        optional += 5

    optional = min(optional, 20)
    profile_completion = min(core + optional, 100)

    return render_template(
        "candidate_profile.html",
        profile=profile,
        resume=resume,
        application_count=application_count,
        profile_completion=profile_completion,
        education_list=education_list,
        experience_list=experience_list,
        projects_list=projects_list,
        certifications_list=certifications_list,
        achievements_list=achievements_list,
        resolved_skills=resolved_skills,
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


def _build_local_resume_analysis(user_id, target_job_id):
    """
    Helper to reconstruct the local analysis safely server-side.
    Returns (error_tuple, data_tuple)
    error_tuple: (json_dict, status_code)
    data_tuple: (local_analysis_dict, raw_resume_text, job_record)
    """
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT raw_text, skills FROM resumes WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            )
            resume_record = cur.fetchone()

            if not resume_record:
                return ({"error": "No resume found. Please upload a resume first."}, 400), None

            raw_skills = resume_record.get("skills")
            candidate_skills = [s.strip() for s in raw_skills.split(",") if s.strip()] if raw_skills else []
            if target_job_id:
                try:
                    job_id_int = int(target_job_id)
                except ValueError:
                    return ({"error": "Invalid job ID provided."}, 400), None

                cur.execute(
                    "SELECT id, job_title, required_skills, description FROM jobs WHERE id = %s AND is_active = TRUE",
                    (job_id_int,),
                )
                job_record = cur.fetchone()

                if not job_record:
                    return ({"error": "Selected target job not found or inactive."}, 400), None

                result = get_final_score(
                    resume_record["raw_text"],
                    candidate_skills,
                    job_record["required_skills"],
                    job_record["description"] or "",
                )

                local_analysis = {
                    "mode": "job_specific",
                    "match_score": result["final_score"],
                    "matched_skills": result["matched"],
                    "missing_skills": result["missing"],
                }
                return None, (local_analysis, resume_record["raw_text"], job_record)

            else:
                local_analysis = {"mode": "general", "detected_skills": candidate_skills}
                return None, (local_analysis, resume_record["raw_text"], None)


@candidate_bp.route("/api/resume/score_local", methods=["POST"])
@login_required(role="candidate")
def score_local_api():
    req_data = request.get_json(silent=True) or {}
    target_job_id = req_data.get("job_id")

    err, data = _build_local_resume_analysis(session["user_id"], target_job_id)
    if err:
        return jsonify(err[0]), err[1]

    local_analysis, _, _ = data
    response_data = dict(local_analysis)
    response_data["success"] = True
    return jsonify(response_data)


@candidate_bp.route("/api/resume/analyze", methods=["POST"])
@login_required(role="candidate")
def analyze_resume_api():
    req_data = request.get_json(silent=True) or {}
    target_job_id = req_data.get("job_id")

    err, data = _build_local_resume_analysis(session["user_id"], target_job_id)
    if err:
        return jsonify(err[0]), err[1]

    local_analysis, raw_resume_text, job_record = data

    job_context = None
    if job_record:
        job_context = {
            "title": job_record["job_title"],
            "required_skills": job_record["required_skills"],
            "description": job_record["description"],
        }

    # Generate analysis via AI Service using the local context
    result = analyze_resume(raw_resume_text, local_analysis, job_context)

    if "error" in result:
        status_code = result.get("status_code", 500)
        return jsonify({"error": result["error"]}), status_code

    return jsonify(result)


def normalize_skills(skills_str):
    if not skills_str:
        return ""
    skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]

    seen = set()
    normalized = []
    for skill in skills_list:
        lower = skill.lower()
        if lower not in seen:
            seen.add(lower)
            normalized.append(skill)  # Keep original casing of first appearance

    # Cap at reasonable limit, e.g., 100 skills
    return ",".join(normalized[:100])


@candidate_bp.route("/candidate/skills/edit", methods=["POST"])
@login_required(role="candidate")
def edit_skills():
    skills_input = request.form.get("skills", "")
    normalized_skills = normalize_skills(skills_input)

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM candidate_profiles WHERE user_id = %s", (session["user_id"],))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE candidate_profiles SET skills = %s WHERE user_id = %s",
                    (normalized_skills, session["user_id"]),
                )
            else:
                cur.execute(
                    "INSERT INTO candidate_profiles (user_id, skills) VALUES (%s, %s)",
                    (session["user_id"], normalized_skills),
                )
            conn.commit()

    flash("Skills updated successfully.", "success")
    return redirect(url_for("candidate.candidate_profile"))


from urllib.parse import urlparse


def validate_url(url):
    if not url:
        return True
    try:
        parsed = urlparse(url)
        # Require http or https scheme and a valid non-empty hostname/netloc
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.netloc:
            return False
        return True
    except Exception:
        return False


def validate_dates(start, end):
    if not start or not end:
        return True
    return start <= end


@candidate_bp.route("/candidate/education/add", methods=["POST"])
@login_required(role="candidate")
def add_education():
    institution = request.form.get("institution", "").strip()
    degree = request.form.get("degree", "").strip()
    field_of_study = request.form.get("field_of_study", "").strip()
    start_date = request.form.get("start_date") or None
    end_date = request.form.get("end_date") or None

    if not institution:
        flash("Institution is required.", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    if not validate_dates(start_date, end_date):
        flash("End date cannot precede start date.", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO candidate_education (user_id, institution, degree, field_of_study, start_date, end_date) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session["user_id"], institution[:255], degree[:255], field_of_study[:255], start_date, end_date),
            )
            conn.commit()
    flash("Education added.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/education/<int:id>/edit", methods=["POST"])
@login_required(role="candidate")
def edit_education(id):
    institution = request.form.get("institution", "").strip()
    degree = request.form.get("degree", "").strip()
    field_of_study = request.form.get("field_of_study", "").strip()
    start_date = request.form.get("start_date") or None
    end_date = request.form.get("end_date") or None

    if not validate_dates(start_date, end_date):
        flash("End date cannot precede start date.", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM candidate_education WHERE id = %s AND user_id = %s", (id, session["user_id"]))
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403

            cur.execute(
                "UPDATE candidate_education SET institution=%s, degree=%s, field_of_study=%s, "
                "start_date=%s, end_date=%s WHERE id=%s",
                (institution[:255], degree[:255], field_of_study[:255], start_date, end_date, id),
            )
            conn.commit()
    flash("Education updated.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/education/<int:id>/delete", methods=["POST"])
@login_required(role="candidate")
def delete_education(id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM candidate_education WHERE id = %s AND user_id = %s", (id, session["user_id"]))
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403
            cur.execute("DELETE FROM candidate_education WHERE id=%s", (id,))
            conn.commit()
    flash("Education deleted.", "info")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/experience/add", methods=["POST"])
@login_required(role="candidate")
def add_experience():
    company = request.form.get("company", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    start_date = request.form.get("start_date") or None
    end_date = request.form.get("end_date") or None
    is_current = request.form.get("is_current") == "on"

    if is_current:
        end_date = None
    elif not validate_dates(start_date, end_date):
        flash("End date cannot precede start date.", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO candidate_experience (user_id, company, title, description, "
                "start_date, end_date, is_current) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (session["user_id"], company[:255], title[:255], description, start_date, end_date, is_current),
            )
            conn.commit()
    flash("Experience added.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/experience/<int:id>/edit", methods=["POST"])
@login_required(role="candidate")
def edit_experience(id):
    company = request.form.get("company", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    start_date = request.form.get("start_date") or None
    end_date = request.form.get("end_date") or None
    is_current = request.form.get("is_current") == "on"

    if is_current:
        end_date = None
    elif not validate_dates(start_date, end_date):
        flash("End date cannot precede start date.", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM candidate_experience WHERE id = %s AND user_id = %s", (id, session["user_id"]))
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403

            cur.execute(
                "UPDATE candidate_experience SET company=%s, title=%s, description=%s, "
                "start_date=%s, end_date=%s, is_current=%s WHERE id=%s",
                (company[:255], title[:255], description, start_date, end_date, is_current, id),
            )
            conn.commit()
    flash("Experience updated.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/experience/<int:id>/delete", methods=["POST"])
@login_required(role="candidate")
def delete_experience(id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM candidate_experience WHERE id = %s AND user_id = %s", (id, session["user_id"]))
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403
            cur.execute("DELETE FROM candidate_experience WHERE id=%s", (id,))
            conn.commit()
    flash("Experience deleted.", "info")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/projects/add", methods=["POST"])
@login_required(role="candidate")
def add_project():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    url = request.form.get("url", "").strip()
    technologies = request.form.get("technologies", "").strip()

    if not validate_url(url):
        flash("Project URL must start with http:// or https://", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO candidate_projects (user_id, title, description, url, technologies) "
                "VALUES (%s, %s, %s, %s, %s)",
                (session["user_id"], title[:255], description, url[:500], technologies),
            )
            conn.commit()
    flash("Project added.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/projects/<int:id>/edit", methods=["POST"])
@login_required(role="candidate")
def edit_project(id):
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    url = request.form.get("url", "").strip()
    technologies = request.form.get("technologies", "").strip()

    if not validate_url(url):
        flash("Project URL must start with http:// or https://", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM candidate_projects WHERE id = %s AND user_id = %s", (id, session["user_id"]))
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403

            cur.execute(
                "UPDATE candidate_projects SET title=%s, description=%s, url=%s, technologies=%s WHERE id=%s",
                (title[:255], description, url[:500], technologies, id),
            )
            conn.commit()
    flash("Project updated.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/projects/<int:id>/delete", methods=["POST"])
@login_required(role="candidate")
def delete_project(id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT id FROM candidate_projects WHERE id = %s AND user_id = %s", (id, session["user_id"]))
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403
            cur.execute("DELETE FROM candidate_projects WHERE id=%s", (id,))
            conn.commit()
    flash("Project deleted.", "info")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/certifications/add", methods=["POST"])
@login_required(role="candidate")
def add_certification():
    name = request.form.get("name", "").strip()
    issuer = request.form.get("issuer", "").strip()
    issue_date = request.form.get("issue_date") or None
    credential_url = request.form.get("credential_url", "").strip()

    if not validate_url(credential_url):
        flash("Credential URL must start with http:// or https://", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO candidate_certifications (user_id, name, issuer, issue_date, credential_url) "
                "VALUES (%s, %s, %s, %s, %s)",
                (session["user_id"], name[:255], issuer[:255], issue_date, credential_url[:500]),
            )
            conn.commit()
    flash("Certification added.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/certifications/<int:id>/edit", methods=["POST"])
@login_required(role="candidate")
def edit_certification(id):
    name = request.form.get("name", "").strip()
    issuer = request.form.get("issuer", "").strip()
    issue_date = request.form.get("issue_date") or None
    credential_url = request.form.get("credential_url", "").strip()

    if not validate_url(credential_url):
        flash("Credential URL must start with http:// or https://", "danger")
        return redirect(url_for("candidate.candidate_profile"))

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id FROM candidate_certifications WHERE id = %s AND user_id = %s", (id, session["user_id"])
            )
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403

            cur.execute(
                "UPDATE candidate_certifications SET name=%s, issuer=%s, issue_date=%s, credential_url=%s WHERE id=%s",
                (name[:255], issuer[:255], issue_date, credential_url[:500], id),
            )
            conn.commit()
    flash("Certification updated.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/certifications/<int:id>/delete", methods=["POST"])
@login_required(role="candidate")
def delete_certification(id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id FROM candidate_certifications WHERE id = %s AND user_id = %s", (id, session["user_id"])
            )
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403
            cur.execute("DELETE FROM candidate_certifications WHERE id=%s", (id,))
            conn.commit()
    flash("Certification deleted.", "info")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/achievements/add", methods=["POST"])
@login_required(role="candidate")
def add_achievement():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    achieved_date = request.form.get("achieved_date") or None

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO candidate_achievements (user_id, title, description, achieved_date) "
                "VALUES (%s, %s, %s, %s)",
                (session["user_id"], title[:255], description, achieved_date),
            )
            conn.commit()
    flash("Achievement added.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/achievements/<int:id>/edit", methods=["POST"])
@login_required(role="candidate")
def edit_achievement(id):
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    achieved_date = request.form.get("achieved_date") or None

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id FROM candidate_achievements WHERE id = %s AND user_id = %s", (id, session["user_id"])
            )
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403

            cur.execute(
                "UPDATE candidate_achievements SET title=%s, description=%s, achieved_date=%s WHERE id=%s",
                (title[:255], description, achieved_date, id),
            )
            conn.commit()
    flash("Achievement updated.", "success")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/achievements/<int:id>/delete", methods=["POST"])
@login_required(role="candidate")
def delete_achievement(id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id FROM candidate_achievements WHERE id = %s AND user_id = %s", (id, session["user_id"])
            )
            if not cur.fetchone():
                return jsonify({"error": "Access denied"}), 403
            cur.execute("DELETE FROM candidate_achievements WHERE id=%s", (id,))
            conn.commit()
    flash("Achievement deleted.", "info")
    return redirect(url_for("candidate.candidate_profile"))


@candidate_bp.route("/candidate/jobs")
@login_required(role="candidate")
def candidate_jobs():
    keyword = request.args.get("keyword", "").strip()
    location = request.args.get("location", "").strip()

    query = "SELECT * FROM jobs WHERE is_active = TRUE"
    params = []

    if keyword:
        query += " AND (job_title LIKE %s OR description LIKE %s)"
        like_kw = f"%{keyword[:100]}%"
        params.extend([like_kw, like_kw])

    if location:
        query += " AND location LIKE %s"
        params.append(f"%{location[:100]}%")

    query += " ORDER BY created_at DESC LIMIT 100"

    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(query, tuple(params))
            jobs = cur.fetchall()

            cur.execute("SELECT job_id FROM saved_jobs WHERE candidate_id = %s", (session["user_id"],))
            saved_job_ids = {row["job_id"] for row in cur.fetchall()}

            cur.execute("SELECT job_id FROM applications WHERE candidate_id = %s", (session["user_id"],))
            applied_job_ids = {row["job_id"] for row in cur.fetchall()}

    return render_template(
        "candidate_jobs.html",
        jobs=jobs,
        saved_job_ids=saved_job_ids,
        applied_job_ids=applied_job_ids,
        keyword=keyword,
        location=location,
    )


@candidate_bp.route("/candidate/job/<int:job_id>")
@login_required(role="candidate")
def candidate_job_details(job_id):
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            # First check if applied
            cur.execute(
                "SELECT * FROM applications WHERE candidate_id = %s AND job_id = %s", (session["user_id"], job_id)
            )
            application = cur.fetchone()

            cur.execute(
                "SELECT j.*, COALESCE(c.name, 'Company not specified') as company_name "
                "FROM jobs j "
                "JOIN users u ON j.recruiter_id = u.id "
                "LEFT JOIN companies c ON u.company_id = c.id "
                "WHERE j.id = %s",
                (job_id,),
            )
            job = cur.fetchone()

            if not job:
                flash("Job not found.", "danger")
                return redirect(url_for("candidate.candidate_jobs"))

            # Policy: if inactive and not applied -> deny
            if not job["is_active"] and not application:
                flash("This job is no longer available.", "warning")
                return redirect(url_for("candidate.candidate_jobs"))

            cur.execute(
                "SELECT 1 FROM saved_jobs WHERE candidate_id = %s AND job_id = %s", (session["user_id"], job_id)
            )
            is_saved = cur.fetchone() is not None

            # Get match score if available
            from services.candidate_service import get_resolved_candidate_skills

            candidate_skills = get_resolved_candidate_skills(session["user_id"], cur)

            match_data = None
            if candidate_skills:
                from models.resume_parser import score_candidate

                match_data = score_candidate(candidate_skills, job["required_skills"])

    return render_template(
        "candidate_job_details.html",
        job=job,
        application=application,
        is_saved=is_saved,
        match_data=match_data,
        has_skills=bool(candidate_skills),
    )


@candidate_bp.route("/candidate/applications")
@login_required(role="candidate")
def candidate_applications():
    with closing(get_db_connection()) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                """
                SELECT a.*, j.job_title, j.location, j.experience, j.is_active,
                       COALESCE(c.name, 'Company not specified') as company_name
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                JOIN users u ON j.recruiter_id = u.id
                LEFT JOIN companies c ON u.company_id = c.id
                WHERE a.candidate_id = %s
                ORDER BY a.applied_at DESC
            """,
                (session["user_id"],),
            )
            applications = cur.fetchall()

    return render_template("candidate_applications.html", applications=applications)
