# etl/transform.py — Clean and normalise raw FlightData objects

import logging
from datetime import datetime, timezone
from opensky_api import FlightData

logger = logging.getLogger(__name__)


def _unix_to_utc(ts: int | None) -> str | None:
    """Convert a Unix timestamp to an ISO-8601 UTC string, or None."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _clean_callsign(callsign: str | None) -> str | None:
    """Strip trailing whitespace that OpenSky sometimes pads callsigns with."""
    if callsign is None:
        return None
    stripped = callsign.strip()
    return stripped if stripped else None


def transform_flight(flight: FlightData, ingested_at: str) -> dict | None:
    """
    Transform a single FlightData object into a clean dict ready for insertion.

    Returns None and logs a warning if the record fails validation.
    """
    # ── Validation ────────────────────────────────────────────────────────────
    if not flight.icao24:
        logger.warning("Skipping record — missing icao24: %r", flight)
        return None

    if flight.firstSeen is None or flight.lastSeen is None:
        logger.warning("Skipping icao24=%s — missing firstSeen/lastSeen", flight.icao24)
        return None

    if flight.firstSeen > flight.lastSeen:
        logger.warning(
            "Skipping icao24=%s — firstSeen (%d) is after lastSeen (%d)",
            flight.icao24, flight.firstSeen, flight.lastSeen,
        )
        return None

    # ── Transformation ────────────────────────────────────────────────────────
    return {
        "icao24":                               flight.icao24.lower().strip(),
        "callsign":                             _clean_callsign(flight.callsign),
        "first_seen":                           flight.firstSeen,
        "last_seen":                            flight.lastSeen,
        "first_seen_utc":                       _unix_to_utc(flight.firstSeen),
        "last_seen_utc":                        _unix_to_utc(flight.lastSeen),
        "est_departure_airport":                flight.estDepartureAirport,
        "est_arrival_airport":                  flight.estArrivalAirport,
        "est_departure_airport_horiz_dist":     flight.estDepartureAirportHorizDistance,
        "est_departure_airport_vert_dist":      flight.estDepartureAirportVertDistance,
        "est_arrival_airport_horiz_dist":       flight.estArrivalAirportHorizDistance,
        "est_arrival_airport_vert_dist":        flight.estArrivalAirportVertDistance,
        "departure_airport_candidates_count":   flight.departureAirportCandidatesCount,
        "arrival_airport_candidates_count":     flight.arrivalAirportCandidatesCount,
        "ingested_at":                          ingested_at,
    }


def transform_flights(raw_flights: list[FlightData], ingested_at: str) -> list[dict]:
    """
    Transform a list of FlightData objects.

    Returns a list of clean dicts, skipping any records that fail validation.
    """
    results = []
    skipped = 0

    for flight in raw_flights:
        record = transform_flight(flight, ingested_at)
        if record is not None:
            results.append(record)
        else:
            skipped += 1

    logger.info(
        "Transform complete — valid: %d | skipped: %d", len(results), skipped
    )
    return results
