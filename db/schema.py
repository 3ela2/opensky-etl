# db/schema.py — Creates the SQLite database and flights table

import sqlite3
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

CREATE_FLIGHTS_TABLE = """
CREATE TABLE IF NOT EXISTS flights (
    id                                  INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Aircraft identity
    icao24                              TEXT    NOT NULL,
    callsign                            TEXT,

    -- Timestamps (stored as Unix epoch seconds)
    first_seen                          INTEGER NOT NULL,
    last_seen                           INTEGER NOT NULL,

    -- Human-readable UTC timestamps (derived during transform)
    first_seen_utc                      TEXT,
    last_seen_utc                       TEXT,

    -- Airports (ICAO codes)
    est_departure_airport               TEXT,
    est_arrival_airport                 TEXT,

    -- Distance metrics (metres)
    est_departure_airport_horiz_dist    INTEGER,
    est_departure_airport_vert_dist     INTEGER,
    est_arrival_airport_horiz_dist      INTEGER,
    est_arrival_airport_vert_dist       INTEGER,

    -- Candidate airport counts
    departure_airport_candidates_count  INTEGER,
    arrival_airport_candidates_count    INTEGER,

    -- ETL metadata
    ingested_at                         TEXT    NOT NULL,

    -- Deduplication: one record per aircraft per departure
    UNIQUE (icao24, first_seen)
);
"""

CREATE_ETL_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS etl_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at          TEXT    NOT NULL,       -- UTC timestamp of the run
    window_begin    INTEGER NOT NULL,       -- Unix epoch start of fetch window
    window_end      INTEGER NOT NULL,       -- Unix epoch end of fetch window
    flights_fetched INTEGER NOT NULL,       -- Raw count returned by API
    flights_inserted INTEGER NOT NULL,      -- New rows actually inserted
    status          TEXT    NOT NULL,       -- 'success' | 'error'
    error_message   TEXT                    -- NULL on success
);
"""


def init_db() -> sqlite3.Connection:
    """
    Initialise the SQLite database, create tables if they don't exist,
    and return an open connection with foreign keys enabled.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")   # safer concurrent writes
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.executescript(CREATE_FLIGHTS_TABLE + CREATE_ETL_RUNS_TABLE)
    conn.commit()
    logger.info("Database initialised at '%s'", DB_PATH)
    return conn
