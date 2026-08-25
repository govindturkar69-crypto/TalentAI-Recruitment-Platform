import json
import logging
from contextlib import closing

from core import get_db_connection

logger = logging.getLogger(__name__)

# Strict allowlist of safe audit metadata fields
AUDIT_ALLOWLIST = {
    "previous_role",
    "new_role",
    "reason",
    "result",
    "status",
    "user_agent",
    "ip_address",
    "is_active_before",
    "is_active_after",
    "company_name",
    "previous_company_id",
    "new_company_id",
    "previous_name",
    "new_name",
}


def log_audit_event(actor_user_id: int, action: str, target_type: str, target_id: int, details: dict):
    """
    Appends an audit log entry.
    Sanitizes `details` by keeping only keys present in AUDIT_ALLOWLIST.
    """
    safe_details_dict = {}
    if details:
        for k, v in details.items():
            if k in AUDIT_ALLOWLIST:
                safe_details_dict[k] = v
            else:
                logger.warning(f"Audit log dropped un-allowlisted key: {k}")

    safe_details_json = json.dumps(safe_details_dict) if safe_details_dict else None

    try:
        with closing(get_db_connection()) as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    INSERT INTO audit_logs (actor_user_id, action, target_type, target_id, safe_details)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (actor_user_id, action, target_type, target_id, safe_details_json),
                )
                conn.commit()
    except Exception as e:
        # Audit logging failure shouldn't necessarily crash the transaction,
        # but it must be logged.
        logger.error(f"Failed to write audit log: {e}")
