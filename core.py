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
from flask import flash, redirect, session, url_for

from config import Config

ADMIN_EMAIL = Config.ADMIN_EMAIL

# Connection pool: reuse DB connections instead of opening one per request.
# Cloud databases such as Aiven require SSL, enabled via MYSQL_SSL=True.
_ssl_config = {"ssl": {"ssl": True}} if Config.MYSQL_SSL else {}

# During tests we don't have a real database, so don't open any connections
# at import time (mincached=0). In normal runs we keep a couple warm.
DB_POOL = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=0 if Config.TESTING else int(os.environ.get("DB_MIN_CACHED", 2)),
    maxcached=5,
    blocking=True,
    ping=1,
    host=Config.MYSQL_HOST,
    port=Config.MYSQL_PORT,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
    database=Config.MYSQL_DB,
    cursorclass=pymysql.cursors.DictCursor,
    **_ssl_config,
)


def get_db_connection():
    return DB_POOL.connection()


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
