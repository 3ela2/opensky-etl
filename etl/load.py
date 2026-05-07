# etl/load.py — Insert/merge transformed flight records into SQLite

import sqlite3
import logging

logger = logging.getLogger(__name__)

# On a conflict (same icao24 + first_seen), update every nullable column using
# COALESCE(excluded.col, col):
#   - If the incoming value is NOT NULL  → use the new value (fills a gap)
#   - If the incoming value IS NULL      → keep whatever is already in the DB
# Non-nullable identity columns (icao24, first_seen) and the original
# ingested_at timestamp are intentionally left unchanged on conflict.
UPSERT_FLIGHT = """
INSERT INTO flights (
    icao24,
    callsign,
    first_seen,
    last_seen,
    first_seen_utc,
    last_seen_utc,
    est_departure_airport,
    est_arrival_airport,
    est_departure_airport_horiz_dist,
    est_departure_airport_vert_dist,
    est_arrival_airport_horiz_dist,
    est_arrival_airport_vert_dist,
    departure_airport_candidates_count,
    arrival_airport_candidates_count,
    ingested_at
) VALUES (
    :icao24,
    :callsign,
    :first_seen,
    :last_seen,
    :first_seen_utc,
    :last_seen_utc,
    :est_departure_airport,
    :est_arrival_airport,
    :est_departure_airport_horiz_dist,
    :est_departure_airport_vert_dist,
    :est_arrival_airport_horiz_dist,
    :est_arrival_airport_vert_dist,
    :departure_airport_candidates_count,
    :arrival_airport_candidates_count,
    :ingested_at
)
ON CONFLICT(icao24, first_seen) DO UPDATE SET
    callsign                            = COALESCE(excluded.callsign,                            callsign),
    last_seen                           = COALESCE(excluded.last_seen,                           last_seen),
    last_seen_utc                       = COALESCE(excluded.last_seen_utc,                       last_seen_utc),
    est_departure_airport               = COALESCE(excluded.est_departure_airport,               est_departure_airport),
    est_arrival_airport                 = COALESCE(excluded.est_arrival_airport,                 est_arrival_airport),
    est_departure_airport_horiz_dist    = COALESCE(excluded.est_departure_airport_horiz_dist,    est_departure_airport_horiz_dist),
    est_departure_airport_vert_dist     = COALESCE(excluded.est_departure_airport_vert_dist,     est_departure_airport_vert_dist),
    est_arrival_airport_horiz_dist      = COALESCE(excluded.est_arrival_airport_horiz_dist,      est_arrival_airport_horiz_dist),
    est_arrival_airport_vert_dist       = COALESCE(excluded.est_arrival_airport_vert_dist,       est_arrival_airport_vert_dist),
    departure_airport_candidates_count  = COALESCE(excluded.departure_airport_candidates_count,  departure_airport_candidates_count),
    arrival_airport_candidates_count    = COALESCE(excluded.arrival_airport_candidates_count,    arrival_airport_candidates_count)
    -- ingested_at is intentionally NOT updated: we keep the original ingest timestamp
;
"""

LOG_ETL_RUN = """
INSERT INTO etl_runs (
    run_at, window_begin, window_end,
    flights_fetched, flights_inserted,
    status, error_message
) VALUES (
    :run_at, :window_begin, :window_end,
    :flights_fetched, :flights_inserted,
    :status, :error_message
);
"""

# Columns we can patch on an existing row (used for counting actual merges)
_NULLABLE_COLS = (
    "callsign",
    "est_departure_airport",
    "est_arrival_airport",
    "est_departure_airport_horiz_dist",
    "est_departure_airport_vert_dist",
    "est_arrival_airport_horiz_dist",
    "est_arrival_airport_vert_dist",
    "departure_airport_candidates_count",
    "arrival_airport_candidates_count",
)


def _count_mergeable_nulls(conn: sqlite3.Connection, records: list[dict]) -> int:
    """
    Count how many (record, column) pairs would patch a NULL in the DB.
    Used purely for informative logging — not part of the write path.
    """
    if not records:
        return 0

    keys = [(r["icao24"], r["first_seen"]) for r in records]
    placeholders = ",".join("(?,?)" for _ in keys)
    flat_params = [v for pair in keys for v in pair]

    rows = conn.execute(
        f"""
        SELECT icao24, first_seen, {", ".join(_NULLABLE_COLS)}
        FROM flights
        WHERE (icao24, first_seen) IN ({placeholders})
        """,
        flat_params,
    ).fetchall()

    col_indices = {col: i + 2 for i, col in enumerate(_NULLABLE_COLS)}
    existing = {(row[0], row[1]): row for row in rows}

    patches = 0
    for rec in records:
        key = (rec["icao24"], rec["first_seen"])
        if key not in existing:
            continue  # new row, not a merge
        db_row = existing[key]
        for col in _NULLABLE_COLS:
            if db_row[col_indices[col]] is None and rec.get(col) is not None:
                patches += 1
    return patches


def load_flights(
    conn: sqlite3.Connection,
    records: list[dict],
) -> int:
    """
    Upsert transformed flight records into the flights table.

    - New records are inserted normally.
    - Duplicate records (same icao24 + first_seen) are merged:
        any column that is NULL in the DB but NOT NULL in the incoming
        record is updated to the new value; existing non-null values
        are never overwritten.

    Returns the number of brand-new rows inserted (merges are not counted
    as insertions but are logged separately).
    """
    if not records:
        logger.info("No records to load.")
        return 0

    # Count patchable nulls before the write (for logging only)
    mergeable = _count_mergeable_nulls(conn, records)

    rows_before = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
    conn.executemany(UPSERT_FLIGHT, records)
    conn.commit()
    rows_after = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]

    inserted = rows_after - rows_before
    duplicates = len(records) - inserted

    logger.info(
        "Load complete — inserted: %d | duplicates seen: %d | null fields patched: %d",
        inserted,
        duplicates,
        mergeable,
    )
    return inserted


def log_etl_run(
    conn: sqlite3.Connection,
    run_at: str,
    window_begin: int,
    window_end: int,
    flights_fetched: int,
    flights_inserted: int,
    status: str,
    error_message: str | None = None,
) -> None:
    """Write a record of this ETL run to the etl_runs audit table."""
    conn.execute(LOG_ETL_RUN, {
        "run_at":            run_at,
        "window_begin":      window_begin,
        "window_end":        window_end,
        "flights_fetched":   flights_fetched,
        "flights_inserted":  flights_inserted,
        "status":            status,
        "error_message":     error_message,
    })
    conn.commit()
    logger.info("ETL run logged — status: %s", status)