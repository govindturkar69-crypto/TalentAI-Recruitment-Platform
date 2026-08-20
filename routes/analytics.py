from flask import Blueprint, render_template

from analytics.dashboard import (
    get_job_applicants_chart,
    get_score_distribution_chart,
    get_skill_distribution_chart,
    get_status_chart,
    get_top_candidates_chart,
)
from core import login_required
from services.analytics_service import get_recruiter_analytics

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/recruiter/analytics")
@login_required(role="recruiter")
def analytics():
    apps_data, stats = get_recruiter_analytics()
    return render_template(
        "analytics.html",
        chart1=get_skill_distribution_chart(apps_data),
        chart2=get_score_distribution_chart(apps_data),
        chart3=get_job_applicants_chart(apps_data),
        chart4=get_top_candidates_chart(apps_data),
        chart5=get_status_chart(apps_data),
        stats=stats,
    )
