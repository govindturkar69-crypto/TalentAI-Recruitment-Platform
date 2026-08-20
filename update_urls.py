import glob
import re

mappings = {
    "candidate_dashboard": "candidate.candidate_dashboard",
    "upload_resume": "candidate.upload_resume",
    "apply_job": "candidate.apply_job",
    "withdraw_application": "candidate.withdraw_application",
    "save_job": "candidate.save_job",
    "unsave_job": "candidate.unsave_job",
    "saved_jobs_page": "candidate.saved_jobs_page",
    "candidate_profile": "candidate.candidate_profile",
    "job_recommendations": "candidate.job_recommendations",
    "recruiter_dashboard": "recruiter.recruiter_dashboard",
    "post_job": "recruiter.post_job",
    "edit_job": "recruiter.edit_job",
    "toggle_job_active": "recruiter.toggle_job_active",
    "delete_job": "recruiter.delete_job",
    "view_applicants": "recruiter.view_applicants",
    "bulk_update_status": "recruiter.bulk_update_status",
    "export_applicants": "recruiter.export_applicants",
    "update_status": "recruiter.update_status",
    "analytics": "analytics.analytics",
}

files_to_check = glob.glob("templates/**/*.html", recursive=True) + glob.glob("routes/*.py") + glob.glob("*.py")

for filepath in files_to_check:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    for old_ep, new_ep in mappings.items():
        # Match url_for('old_ep' or url_for("old_ep"
        content = re.sub(r"url_for\(\s*['\"]" + old_ep + r"['\"]\s*([,)])", r"url_for('" + new_ep + r"'\g<1>", content)

    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {filepath}")
