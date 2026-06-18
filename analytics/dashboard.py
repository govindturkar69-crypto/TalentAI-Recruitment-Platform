# ============================================
# analytics/dashboard.py
# Analytics Charts using Plotly
# ============================================

import json
import plotly
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def get_skill_distribution_chart(applications):
    """
    Sabse zyada demand mein kaunsi skills hain — bar chart.
    applications: list of dicts with 'matched_skills' key
    """
    skill_count = {}
    for app in applications:
        skills = app.get("matched_skills", "")
        if skills:
            for skill in skills.split(","):
                s = skill.strip()
                if s:
                    skill_count[s] = skill_count.get(s, 0) + 1

    if not skill_count:
        return None

    df = pd.DataFrame(list(skill_count.items()), columns=["Skill", "Count"])
    df = df.sort_values("Count", ascending=False).head(12)

    fig = px.bar(
        df, x="Count", y="Skill", orientation="h",
        title="Top Skills in Demand",
        color="Count",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        font=dict(family="Segoe UI", size=12),
        title_font_size=16,
        showlegend=False,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def get_score_distribution_chart(applications):
    """
    Candidate scores ka distribution — histogram.
    """
    scores = [app.get("score", 0) for app in applications]
    if not scores:
        return None

    fig = px.histogram(
        x=scores, nbins=10,
        title="Candidate Score Distribution",
        labels={"x": "Score (%)", "y": "Number of Candidates"},
        color_discrete_sequence=["#6366f1"],
    )
    fig.update_layout(
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        font=dict(family="Segoe UI", size=12),
        title_font_size=16,
        bargap=0.1,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def get_job_applicants_chart(applications):
    """
    Har job mein kitne applicants hain — pie chart.
    """
    job_count = {}
    for app in applications:
        job = app.get("job_title", "Unknown")
        job_count[job] = job_count.get(job, 0) + 1

    if not job_count:
        return None

    fig = go.Figure(data=[go.Pie(
        labels=list(job_count.keys()),
        values=list(job_count.values()),
        hole=0.4,
        marker=dict(colors=["#6366f1", "#0ea5e9", "#22c55e", "#f59e0b", "#ef4444"]),
    )])
    fig.update_layout(
        title="Applicants per Job Role",
        font=dict(family="Segoe UI", size=12),
        title_font_size=16,
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def get_top_candidates_chart(applications, top_n=10):
    """
    Top N candidates ka score bar chart.
    """
    if not applications:
        return None

    sorted_apps = sorted(applications, key=lambda x: x.get("score", 0), reverse=True)[:top_n]

    names  = [a.get("candidate_name", "Unknown") for a in sorted_apps]
    scores = [a.get("score", 0) for a in sorted_apps]

    colors = []
    for s in scores:
        if s >= 75:
            colors.append("#22c55e")
        elif s >= 50:
            colors.append("#f59e0b")
        else:
            colors.append("#ef4444")

    fig = go.Figure(go.Bar(
        x=names, y=scores,
        marker_color=colors,
        text=[f"{s:.1f}%" for s in scores],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Top {top_n} Candidates by Score",
        xaxis_title="Candidate",
        yaxis_title="Score (%)",
        yaxis=dict(range=[0, 110]),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        font=dict(family="Segoe UI", size=12),
        title_font_size=16,
        margin=dict(l=20, r=20, t=50, b=60),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def get_status_chart(applications):
    """
    Application status breakdown — shortlisted / rejected / applied / hired.
    """
    status_count = {}
    for app in applications:
        status = app.get("status", "applied")
        status_count[status] = status_count.get(status, 0) + 1

    if not status_count:
        return None

    color_map = {
        "applied"    : "#6366f1",
        "shortlisted": "#22c55e",
        "rejected"   : "#ef4444",
        "hired"      : "#f59e0b",
    }

    fig = go.Figure(data=[go.Bar(
        x=list(status_count.keys()),
        y=list(status_count.values()),
        marker_color=[color_map.get(k, "#64748b") for k in status_count.keys()],
        text=list(status_count.values()),
        textposition="outside",
    )])
    fig.update_layout(
        title="Application Status Overview",
        xaxis_title="Status",
        yaxis_title="Count",
        plot_bgcolor="#f8fafc",
        paper_bgcolor="#ffffff",
        font=dict(family="Segoe UI", size=12),
        title_font_size=16,
        margin=dict(l=20, r=20, t=50, b=40),
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
