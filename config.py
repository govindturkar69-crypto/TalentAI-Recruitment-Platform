import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("FLASK_SECRET_KEY is not set. Refusing to start with an insecure key.")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_DEBUG", "False") != "True"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "recruitment_db")
    MYSQL_SSL = os.environ.get("MYSQL_SSL") == "True"

    TESTING = os.environ.get("TESTING") == "True"

    # Monitoring
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    APP_ENV = os.environ.get("APP_ENV", "development")

    # Admin email (recruiter role assignment)
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "govindturkar45@gmail.com")

    # Email Delivery
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    MAIL_FROM = os.environ.get("MAIL_FROM")
    APP_BASE_URL = os.environ.get("APP_BASE_URL")
