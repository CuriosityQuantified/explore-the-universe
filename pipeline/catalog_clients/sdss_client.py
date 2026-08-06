"""SDSS (Sloan Digital Sky Survey) catalog client.

Radius is hard-capped at 180 arcsec (3 arcmin) per SDSS API limits.
On final failure returns a ``not_queried`` sentinel.
"""

import logging
import time

import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.sdss import SDSS

logger = logging.getLogger(__name__)

_SDSS_MAX_RADIUS_ARCSEC = 180.0  # 3 arcmin hard cap

_PHOTO_FIELDS = ["objid", "ra", "dec", "type", "petroMag_r", "petroMag_g", "petroMag_i"]
_SPEC_FIELDS = ["class", "subclass", "z", "zErr"]


def query_sdss_region(
    coordinate: SkyCoord,
    radius_arcsec: float,
    max_retries: int = 3,
) -> list[dict]:
    """Query SDSS for all objects within *radius_arcsec* of *coordinate*.

    Returns a list of match dicts on success.  On final failure returns a
    single-element list containing ``{"status": "not_queried", ...}``.

    Retries up to *max_retries* times with exponential back-off.
    Radius is capped at 180 arcsec per SDSS hard limit.
    """
    capped_radius = min(radius_arcsec, _SDSS_MAX_RADIUS_ARCSEC)

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            result_table = SDSS.query_region(
                coordinate,
                radius=capped_radius * u.arcsec,
                spectro=True,
                photoobj_fields=_PHOTO_FIELDS,
                specobj_fields=_SPEC_FIELDS,
            )
            if result_table is None:
                return []
            return _table_to_dicts(result_table, coordinate, "sdss")
        except Exception as exc:
            last_exc = exc
            wait = 2**attempt
            logger.warning(
                "SDSS query attempt %d/%d failed (%s); retrying in %ds",
                attempt + 1,
                max_retries,
                exc,
                wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)

    logger.error("SDSS query failed after %d retries: %s", max_retries, last_exc)
    return [{"status": "not_queried", "catalog": "sdss", "error": str(last_exc)}]


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
                "catalog_source_id": str(row["objid"]) if "objid" in table.colnames else None,
                "object_type": str(row["type"]) if "type" in table.colnames else None,
                "spectral_class": str(row["class"]) if "class" in table.colnames else None,
                "spectral_subclass": str(row["subclass"]) if "subclass" in table.colnames else None,
                "ra_deg": ra,
                "dec_deg": dec,
                "angular_separation_arcsec": sep,
                "magnitude": (
                    float(row["petroMag_r"])
                    if "petroMag_r" in table.colnames and row["petroMag_r"] is not None
                    else None
                ),
                "redshift": (
                    float(row["z"])
                    if "z" in table.colnames and row["z"] is not None
                    else None
                ),
            }
        )
    return rows
