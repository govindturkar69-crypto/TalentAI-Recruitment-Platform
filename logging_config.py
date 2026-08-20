import logging
import logging.config


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        from flask import has_request_context, request, session

        if has_request_context():
            record.req_path = request.path
            record.req_method = request.method
            user_id = session.get("user_id")
            record.user_info = f" | User: {user_id}" if user_id else ""
            record.ctx = f" [{record.req_method} {record.req_path}{record.user_info}]"
        else:
            record.ctx = ""
        return True


def setup_logging():
    # Only configure if no handlers exist to prevent duplicate logging on reload
    if logging.getLogger().hasHandlers():
        return

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": RequestContextFilter,
            }
        },
        "formatters": {
            "standard": {
                "format": "[%(asctime)s] %(levelname)s in %(name)s%(ctx)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["request_context"],
                "level": "INFO",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }
    logging.config.dictConfig(logging_config)
