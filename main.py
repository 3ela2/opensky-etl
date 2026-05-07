# main.py — Entry point for the OpenSky ETL pipeline

import logging
import sys
import os

# ── Make sure project root is on the path ────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from config import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT
from scheduler import start_scheduler


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("opensky_etl.log", encoding="utf-8"),
        ],
    )


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("OpenSky ETL — starting up")
    start_scheduler()
