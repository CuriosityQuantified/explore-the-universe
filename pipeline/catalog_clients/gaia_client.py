"""Gaia DR3 catalog client using astroquery.gaia cone-search.

On final failure returns a ``not_queried`` sentinel so the pipeline can
continue gracefully.
"""

import logging
import time

import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia

logger = logging.getLogger(__name__)

Gaia.MAIN_GAIA_TABLE = "gaiadr3.gaia_source"


def query_gaia_region(
    coordinate: SkyCoord,
    radius_arcsec: float,
    max_retries: int = 3,
    row_limit: int = 50,
) -> list[dict]:
    """Query Gaia DR3 for sources within *radius_arcsec* of *coordinate*.

    Returns a list of match dicts on success.  On final failure returns a
    single-element list containing ``{"status": "not_queried", ...}``.

    Retries up to *max_retries* times with exponential back-off.
    """
    Gaia.ROW_LIMIT = row_limit

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            job = Gaia.cone_search_async(
                coordinate, radius=radius_arcsec * u.arcsec
            )
            result_table = job.get_results()
            if result_table is None or len(result_table) == 0:
                return []
            return _table_to_dicts(result_table, coordinate, "gaia")
        except Exception as exc:
            last_exc = exc
            wait = 2**attempt
            logger.warning(
                "Gaia query attempt %d/%d failed (%s); retrying in %ds",
                attempt + 1,
                max_retries,
                exc,
                wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)

    logger.error("Gaia query failed after %d retries: %s", max_retries, last_exc)
    return [{"status": "not_queried", "catalog": "gaia", "error": str(last_exc)}]


def _table_to_dicts(table, reference_coord: SkyCoord, catalog: str) -> list[dict]:
    rows: list[dict] = []
    for row in table:
        ra = float(row["ra"]) if "ra" in table.colnames else None
        dec = float(row["dec"]) if "dec" in table.colnames else None
        sep = None
        if ra is not None and dec is not None:
            obj_coord = SkyCoord(ra=ra, dec=dec, unit="deg")
            sep = float(reference_coord.separation(obj_coord).arcsec)
        rows.append(
            {
                "catalog": catalog,
                "catalog_source_id": str(row["source_id"]) if "source_id" in table.colnames else None,
                "ra_deg": ra,
                "dec_deg": dec,
                "angular_separation_arcsec": sep,
                "magnitude": (
                    float(row["phot_g_mean_mag"])
                    if "phot_g_mean_mag" in table.colnames and row["phot_g_mean_mag"] is not None
                    else None
                ),
                "parallax": (
                    float(row["parallax"])
                    if "parallax" in table.colnames and row["parallax"] is not None
                    else None
                ),
                "proper_motion_ra": (
                    float(row["pmra"])
                    if "pmra" in table.colnames and row["pmra"] is not None
                    else None
                ),
                "proper_motion_dec": (
                    float(row["pmdec"])
                    if "pmdec" in table.colnames and row["pmdec"] is not None
                    else None
                ),
                "color_bp_rp": (
                    float(row["bp_rp"])
                    if "bp_rp" in table.colnames and row["bp_rp"] is not None
                    else None
                ),
            }
        )
    return rows
