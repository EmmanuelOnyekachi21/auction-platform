"""Logging configuration for the auction platform."""
import logging
import logging.config


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            'datefmt': "%Y-%m-%d %H:%M:%S"
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 1024*1024*10, # 10MB
            'backupCount': 5,
            'formatter': 'default'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/error.log',
            'maxBytes': 1024*1024*10, # 10MB
            'backupCount': 5,
            'formatter': 'default',
            'level': 'ERROR'
        },
    },

    'loggers': {
        'uvicorn': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        "sqlalchemy.engine": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'DEBUG',
    },
}


def setup_logging(app_env: str = "development") -> None:
    """Configure logging based on the application environment."""

    level = "DEBUG" if app_env == "development" else "INFO"
    LOGGING_CONFIG["root"]["level"] = level

    logging.config.dictConfig(LOGGING_CONFIG)
