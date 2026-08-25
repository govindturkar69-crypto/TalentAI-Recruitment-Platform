"""Centralized hiring workflow rules for application statuses."""

APPLICATION_STATUSES = {
    "applied",
    "shortlisted",
    "rejected",
    "hired",
    "withdrawn",
}

RECRUITER_TRANSITIONS = {
    "applied": {"shortlisted", "rejected"},
    "shortlisted": {"hired", "rejected"},
    "rejected": set(),
    "hired": set(),
    "withdrawn": set(),
}

CANDIDATE_TRANSITIONS = {
    "applied": {"withdrawn"},
    "shortlisted": {"withdrawn"},
    "rejected": set(),
    "hired": set(),
    "withdrawn": set(),
}
