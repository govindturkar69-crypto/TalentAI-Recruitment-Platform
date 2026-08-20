import logging
from contextlib import closing

from core import get_db_connection

logger = logging.getLogger(__name__)


def create_notification(user_id, title, message, notif_type="system"):
    try:
        with closing(get_db_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    "INSERT INTO notifications (user_id, title, message, type) VALUES (%s,%s,%s,%s)",
                    (user_id, title, message, notif_type),
                )
                conn.commit()
    except Exception:
        logger.exception("Notification error")
