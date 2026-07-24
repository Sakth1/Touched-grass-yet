import logging
import os
from logging.handlers import RotatingFileHandler

from core.paths import get_data_dir

LOG_DIR = "logs"
LOG_FILE = "app.log"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3

_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def setup_file_logging() -> str | None:
    log_dir = os.path.join(get_data_dir(), LOG_DIR)
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        logging.warning("Cannot create log directory %s: %s", log_dir, e)
        return None

    log_path = os.path.join(log_dir, LOG_FILE)
    try:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(_formatter)
        logging.getLogger().addHandler(handler)
        logging.getLogger().info("File logging initialized: %s", log_path)
        return log_path
    except OSError as e:
        logging.warning("Cannot create log file %s: %s", log_path, e)
        return None


def get_log_path() -> str | None:
    log_path = os.path.join(get_data_dir(), LOG_DIR, LOG_FILE)
    if os.path.isfile(log_path):
        return log_path
    return None


def read_log_lines(max_lines: int = 500) -> list[str]:
    path = get_log_path()
    if not path:
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return lines[-max_lines:]
    except OSError as e:
        logging.warning("Cannot read log file %s: %s", path, e)
        return []
