import datetime
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def remove_file(path: str | os.PathLike) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove file %s", path)


def timestamped_filename(prefix: str = "events", ext: str = "json") -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.{ext}"
