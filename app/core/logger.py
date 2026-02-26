# pc/app/core/logger.py
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(log_path: str = "server.log") -> logging.Logger:
    """
    Create a single rotating file logger for the whole app.

    Note:
    - Werkzeug access logs are disabled in the Flask app.
    - This function must be idempotent (avoid duplicate handlers).
    """
    logger = logging.getLogger("server_logger")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger