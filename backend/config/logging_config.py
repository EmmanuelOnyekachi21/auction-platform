"""Logging configuration for the auction platform."""

import logging
import logging.config


class RequestIDFilter(logging.Filter):
    """Inject the current request_id context var into every log record.

    When a log statement is emitted outside a request context (e.g. in a
    Celery task or on startup) the value falls back to "-" so the field is
    always present in the formatted output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        from common.middleware import request_id_var

        record.request_id = request_id_var.get("-")
        return True


LOGGING_CONFIG_BASE = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "config.logging_config.RequestIDFilter",
        },
    },
    "formatters": {
        "default": {
            "format": (
                "%(asctime)s | %(levelname)s | %(name)s"
                " | request_id=%(request_id)s | %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["request_id"],
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# File handlers are used in all environments — on a VPS the filesystem
# persists across deployments, making file logs valuable in production too.
_FILE_HANDLERS = {
    "file": {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": "logs/app.log",
        "maxBytes": 1024 * 1024 * 10,  # 10MB
        "backupCount": 5,
        "formatter": "default",
        "filters": ["request_id"],
    },
    "error_file": {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": "logs/error.log",
        "maxBytes": 1024 * 1024 * 10,  # 10MB
        "backupCount": 5,
        "formatter": "default",
        "filters": ["request_id"],
        "level": "ERROR",
    },
}


def setup_logging(app_env: str = "development") -> None:
    """Configure logging for VPS deployment.

    All environments: stdout + rotating file handlers.
    stdout is captured by systemd/supervisor; files allow direct inspection.
    """
    config = dict(LOGGING_CONFIG_BASE)
    config["handlers"] = {**LOGGING_CONFIG_BASE["handlers"], **_FILE_HANDLERS}
    config["root"] = {
        "handlers": ["console", "file", "error_file"],
        "level": "INFO",
    }

    logging.config.dictConfig(config)
