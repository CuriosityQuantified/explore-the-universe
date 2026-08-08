"""SIMBAD catalog client with exponential-backoff retry.

Implements vectorized cone-search via astroquery.simbad.  On final failure
the function returns a ``not_queried`` sentinel list so the pipeline can
continue without a hard crash.
"""

import logging
import time

import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.simbad import Simbad

logger = logging.getLogger(__name__)

# Extra VOTable fields requested from SIMBAD.
_SIMBAD_FIELDS = ["otype", "flux(V)", "rvz_redshift", "rvz_type"]


def query_simbad_region(
    coordinate: SkyCoord,
    radius_arcsec: float,
    max_retries: int = 3,
    timeout: int = 60,
) -> list[dict]:
    """Query SIMBAD for all objects within *radius_arcsec* of *coordinate*.

    Returns a list of match dicts on success.  On final failure returns a
    single-element list containing ``{"status": "not_queried", ...}``.

    Retries up to *max_retries* times with exponential back-off (1 s, 2 s, 4 s).
    """
    simbad = Simbad()
    simbad.TIMEOUT = timeout
    for field in _SIMBAD_FIELDS:
        simbad.add_votable_fields(field)

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            result_table = simbad.query_region(
                coordinate, radius=radius_arcsec * u.arcsec
            )
            if result_table is None:
                return []
            return _table_to_dicts(result_table, coordinate, "simbad")
        except Exception as exc:
            last_exc = exc
            wait = 2**attempt
            logger.warning(
                "SIMBAD query attempt %d/%d failed (%s); retrying in %ds",
                attempt + 1,
                max_retries,
                exc,
                wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)

    logger.error("SIMBAD query failed after %d retries: %s", max_retries, last_exc)
    return [{"status": "not_queried", "catalog": "simbad", "error": str(last_exc)}]


def resolve_object_name(
    name: str,
    max_retries: int = 3,
    timeout: int = 30,
) -> tuple[float, float, str] | None:
    """Resolve an object name to (ra_deg, dec_deg, canonical_name) via SIMBAD.

    Returns None if the name is not found in SIMBAD.
    Raises RuntimeError if SIMBAD is unreachable after all retries.
    """
    simbad = Simbad()
    simbad.TIMEOUT = timeout

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            result = simbad.query_object(name)
            if result is None:
                return None
            row = result[0]
            # SIMBAD returns RA/Dec as sexagesimal strings (e.g. "49 53 22.12")
            coord = SkyCoord(
                ra=str(row["RA"]),
                dec=str(row["DEC"]),
                unit=(u.hourangle, u.deg),
            )
            canonical = str(row["MAIN_ID"])
            return (float(coord.ra.deg), float(coord.dec.deg), canonical)
        except Exception as exc:
            last_exc = exc
            wait = 2 ** attempt
            logger.warning(
                "SIMBAD name resolve attempt %d/%d failed (%s); retrying in %ds",
                attempt + 1,
                max_retries,
                exc,
                wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)

    raise RuntimeError(
        f"SIMBAD unreachable after {max_retries} retries: {last_exc}"
    )


def _table_to_dicts(table, reference_coord: SkyCoord, catalog: str) -> list[dict]:
    rows: list[dict] = []
    for row in table:
        ra = float(row["RA_d"]) if "RA_d" in table.colnames else None
        dec = float(row["DEC_d"]) if "DEC_d" in table.colnames else None
        sep = None
        if ra is not None and dec is not None:
            obj_coord = SkyCoord(ra=ra, dec=dec, unit="deg")
            sep = float(reference_coord.separation(obj_coord).arcsec)
        rows.append(
            {
                "catalog": catalog,
                "catalog_source_id": str(row["MAIN_ID"]),
                "object_type": str(row["OTYPE"]) if "OTYPE" in table.colnames else None,
                "ra_deg": ra,
                "dec_deg": dec,
                "angular_separation_arcsec": sep,
                "magnitude": (
                    float(row["FLUX_V"])
                    if "FLUX_V" in table.colnames and row["FLUX_V"] is not None
                    else None
                ),
                "redshift": (
                    float(row["rvz_redshift"])
                    if "rvz_redshift" in table.colnames and row["rvz_redshift"] is not None
                    else None
                ),
            }
        )
    return rows
