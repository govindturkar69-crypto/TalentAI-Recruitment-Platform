"""Shared helpers used across the app and its blueprints.

Keeping the database pool, connection helper, and the auth decorator here
lets both app.py and the route blueprints import them without importing
each other (which would cause a circular import).
"""

import os
from functools import wraps

import pymysql
import pymysql.cursors
from dbutils.pooled_db import PooledDB
from flask import session, flash, redirect, url_for

ADMIN_EMAIL = "govindturkar45@gmail.com"

# Connection pool: reuse DB connections instead of opening one per request.
# Cloud databases such as Aiven require SSL, enabled via MYSQL_SSL=True.
_ssl_config = {"ssl": {"ssl": True}} if os.environ.get("MYSQL_SSL") == "True" else {}

# During tests we don't have a real database, so don't open any connections
# at import time (mincached=0). In normal runs we keep a couple warm.
_testing = os.environ.get("TESTING") == "True"

DB_POOL = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=0 if _testing else 2,
    maxcached=5,
    blocking=True,
    ping=1,
    host=os.environ.get("MYSQL_HOST", "localhost"),
    port=int(os.environ.get("MYSQL_PORT", 3306)),
    user=os.environ.get("MYSQL_USER", "root"),
    password=os.environ.get("MYSQL_PASSWORD", ""),
    database=os.environ.get("MYSQL_DB", "recruitment_db"),
    cursorclass=pymysql.cursors.DictCursor,
    **_ssl_config,
)


def get_db_connection():
    return DB_POOL.connection()


def create_notification(user_id, title, message, notif_type="system"):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notifications (user_id, title, message, type) VALUES (%s,%s,%s,%s)",
            (user_id, title, message, notif_type)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Notification error:", e)


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("auth.login"))
            if role and session.get("role") != role:
                flash("Access denied.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator
