# scheduler.py — Schedules the ETL pipeline using APScheduler

import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import SCHEDULE_INTERVAL_HOURS
from etl.pipeline import run_etl

logger = logging.getLogger(__name__)


def start_scheduler() -> None:
    """
    Start the blocking APScheduler.
    - Runs `run_etl()` immediately on startup.
    - Then repeats every SCHEDULE_INTERVAL_HOURS hours.
    - Blocks the main thread (Ctrl+C to stop).
    """
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        func=run_etl,
        trigger=IntervalTrigger(hours=SCHEDULE_INTERVAL_HOURS),
        id="opensky_etl",
        name="OpenSky Flight ETL",
        replace_existing=True,
        max_instances=1,        # prevent overlapping runs
        misfire_grace_time=300, # 5-minute grace if a run is slightly late
    )

    logger.info(
        "Scheduler configured — ETL will run every %d hour(s). Starting now...",
        SCHEDULE_INTERVAL_HOURS,
    )

    # Run once immediately so we don't wait a full hour on first start
    run_etl()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
        scheduler.shutdown(wait=False)
