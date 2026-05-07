# config.py — Central configuration for OpenSky ETL

import os
from dotenv import load_dotenv

# Load variables from .env into the environment (silently ignored if .env
# doesn't exist, e.g. on a cloud server where vars are set directly).
load_dotenv()

# ── Credentials ───────────────────────────────────────────────────────────────
# Read from environment — never hardcode these values here.
# Locally:  set them in your .env file (see .env.example)
# On server: set them as environment variables in your hosting platform
OPENSKY_CLIENT_ID: str | None = os.getenv("OPENSKY_CLIENT_ID")
OPENSKY_CLIENT_SECRET: str | None = os.getenv("OPENSKY_CLIENT_SECRET")

# If both are missing, the ETL falls back to anonymous access automatically.
USE_CREDENTIALS: bool = bool(OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET)

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = "db/flights.db"

# ── Extraction window ─────────────────────────────────────────────────────────
# OpenSky enforces a hard max of 7200 seconds (2 hours) per request.
# We always fetch the last FETCH_WINDOW_SECONDS seconds on every run.
FETCH_WINDOW_SECONDS = 7200  # 2 hours

# ── Scheduler ─────────────────────────────────────────────────────────────────
# Run the ETL job every SCHEDULE_INTERVAL_HOURS hours.
# Windows overlap intentionally — duplicates are handled via upsert-merge.
SCHEDULE_INTERVAL_HOURS = 1

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"