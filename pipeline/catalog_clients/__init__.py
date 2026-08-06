"""Catalog client package for cross-matching astronomical objects.

Exports the adaptive search-radius utility used by all four catalog clients
(SIMBAD, NED, SDSS, Gaia) and by tests.
"""

from pipeline.catalog_clients import gaia_client, ned_client, sdss_client, simbad_client


def compute_search_radius_arcsec(
    bounding_box_pixels: dict,
    pixel_scale_arcsec_per_pixel: float,
    compact_source_radius_arcsec: float = 2.0,
    extended_source_scale_factor: float = 1.5,
    compact_source_threshold_arcsec: float = 5.0,
) -> float:
    """Return an adaptive cross-match search radius in arcseconds.

    Compact sources (angular extent < threshold) get a floor of
    ``compact_source_radius_arcsec`` (~2 arcsec).  Extended sources scale
    proportionally: radius = angular_extent × extended_source_scale_factor.
    """
    bbox_width = bounding_box_pixels["xmax"] - bounding_box_pixels["xmin"]
    bbox_height = bounding_box_pixels["ymax"] - bounding_box_pixels["ymin"]
    angular_extent_arcsec = (
        max(bbox_width, bbox_height) * pixel_scale_arcsec_per_pixel
    )

    if angular_extent_arcsec < compact_source_threshold_arcsec:
        return max(compact_source_radius_arcsec, angular_extent_arcsec)
    return angular_extent_arcsec * extended_source_scale_factor


__all__ = [
    "compute_search_radius_arcsec",
    "simbad_client",
    "ned_client",
    "sdss_client",
    "gaia_client",
]
