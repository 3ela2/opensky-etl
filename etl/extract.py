# etl/extract.py — Pull raw flight data from the OpenSky Network API

import time
import logging
from opensky_api import OpenSkyApi
from config import OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET, USE_CREDENTIALS

logger = logging.getLogger(__name__)


def extract_flights(window_seconds: int = 7200) -> tuple[list, int, int]:
    """
    Fetch flights for the last `window_seconds` seconds (max 7200 = 2 hours).

    Uses client_id/client_secret from environment variables if available,
    otherwise falls back to anonymous access.

    Returns:
        (flights, begin, end)
        - flights : list of FlightData objects (may be empty)
        - begin   : Unix timestamp — start of the fetch window
        - end     : Unix timestamp — end of the fetch window
    """
    end   = int(time.time())
    begin = end - window_seconds

    if USE_CREDENTIALS:
        logger.info(
            "Extracting flights with credentials (client_id='%s') | window: %ds | begin=%d end=%d",
            OPENSKY_CLIENT_ID, window_seconds, begin, end,
        )
        api = OpenSkyApi(client_id=OPENSKY_CLIENT_ID, client_secret=OPENSKY_CLIENT_SECRET)
    else:
        logger.info(
            "Extracting flights anonymously | window: %ds | begin=%d end=%d",
            window_seconds, begin, end,
        )
        api = OpenSkyApi()

    try:
        with api:
            flights = api.get_flights_from_interval(begin, end)
    except Exception as exc:
        logger.error("API call failed: %s", exc, exc_info=True)
        raise

    if flights is None:
        logger.warning("API returned None — possibly rate-limited or no data in window.")
        return [], begin, end

    logger.info("Extracted %d flight record(s) from OpenSky.", len(flights))
    return flights, begin, end