# etl/pipeline.py — Orchestrates the full Extract → Transform → Load cycle

import logging
from datetime import datetime, timezone

from config import FETCH_WINDOW_SECONDS
from db.schema import init_db
from etl.extract import extract_flights
from etl.transform import transform_flights
from etl.load import load_flights, log_etl_run

logger = logging.getLogger(__name__)


def run_etl() -> None:
    """
    Execute one full ETL cycle:
      1. Extract  — fetch flights from OpenSky for the last 2 hours
      2. Transform — validate and normalise each FlightData record
      3. Load     — insert new records into SQLite, skip duplicates
      4. Audit    — write a row to etl_runs regardless of success/failure
    """
    run_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    logger.info("═" * 60)
    logger.info("ETL run started at %s UTC", run_at)

    conn = init_db()
    flights_fetched  = 0
    flights_inserted = 0
    window_begin     = 0
    window_end       = 0

    try:
        # ── Extract ───────────────────────────────────────────────────────────
        raw_flights, window_begin, window_end = extract_flights(FETCH_WINDOW_SECONDS)
        flights_fetched = len(raw_flights)

        # ── Transform ─────────────────────────────────────────────────────────
        clean_records = transform_flights(raw_flights, ingested_at=run_at)

        # ── Load (upsert-merge) ───────────────────────────────────────────────
        flights_inserted = load_flights(conn, clean_records)

        # ── Audit ─────────────────────────────────────────────────────────────
        log_etl_run(
            conn,
            run_at=run_at,
            window_begin=window_begin,
            window_end=window_end,
            flights_fetched=flights_fetched,
            flights_inserted=flights_inserted,
            status="success",
        )
        logger.info("ETL run finished successfully.")

    except Exception as exc:
        logger.error("ETL run failed: %s", exc, exc_info=True)
        log_etl_run(
            conn,
            run_at=run_at,
            window_begin=window_begin,
            window_end=window_end,
            flights_fetched=flights_fetched,
            flights_inserted=flights_inserted,
            status="error",
            error_message=str(exc),
        )

    finally:
        conn.close()