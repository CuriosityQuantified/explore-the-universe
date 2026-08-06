"""NED (NASA/IPAC Extragalactic Database) catalog client.

NED has no vectorized/batch endpoint — queries are per-coordinate only.
A rate-limit delay is inserted between calls.  On final failure returns a
``not_queried`` sentinel so the pipeline can continue gracefully.
"""

import logging
import time

import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.ipac.ned import Ned

logger = logging.getLogger(__name__)


def query_ned_region(
    coordinate: SkyCoord,
    radius_arcsec: float,
    max_retries: int = 3,
    rate_limit_delay: float = 0.5,
) -> list[dict]:
    """Query NED for all objects within *radius_arcsec* of *coordinate*.

    Returns a list of match dicts on success.  On final failure returns a
    single-element list containing ``{"status": "not_queried", ...}``.

    Retries up to *max_retries* times with exponential back-off.
    *rate_limit_delay* seconds are slept after each successful call.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            result_table = Ned.query_region(
                coordinate, radius=radius_arcsec * u.arcsec
            )
            time.sleep(rate_limit_delay)
            if result_table is None:
                return []
            return _table_to_dicts(result_table, coordinate, "ned")
        except Exception as exc:
            last_exc = exc
            wait = 2**attempt
            logger.warning(
                "NED query attempt %d/%d failed (%s); retrying in %ds",
                attempt + 1,
                max_retries,
                exc,
                wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)

    logger.error("NED query failed after %d retries: %s", max_retries, last_exc)
    return [{"status": "not_queried", "catalog": "ned", "error": str(last_exc)}]


def _table_to_dicts(table, reference_coord: SkyCoord, catalog: str) -> list[dict]:
    rows: list[dict] = []
    for row in table:
        ra = float(row["RA"]) if "RA" in table.colnames else None
        dec = float(row["DEC"]) if "DEC" in table.colnames else None
        sep = None
        if ra is not None and dec is not None:
            obj_coord = SkyCoord(ra=ra, dec=dec, unit="deg")
            sep = float(reference_coord.separation(obj_coord).arcsec)
        rows.append(
            {
                "catalog": catalog,
                "catalog_source_id": str(row["Object Name"]) if "Object Name" in table.colnames else None,
                "object_type": str(row["Type"]) if "Type" in table.colnames else None,
                "ra_deg": ra,
                "dec_deg": dec,
                "angular_separation_arcsec": sep,
                "redshift": (
                    float(row["Redshift"])
                    if "Redshift" in table.colnames and row["Redshift"] is not None
                    else None
                ),
            }
        )
    return rows
