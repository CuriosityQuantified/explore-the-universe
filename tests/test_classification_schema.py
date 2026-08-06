"""Unit tests for Phase 5 Plan 1: classification schema, catalog clients, and 9-task chain.

All tests are offline — no network, no live DB, no running services required.
"""

import inspect
import unittest.mock as mock


# ---------------------------------------------------------------------------
# Task 1: Schema / model acceptance criteria
# ---------------------------------------------------------------------------


def test_object_classification_importable():
    from shared.models import ObjectClassification  # noqa: F401


def test_object_classification_has_feature_vector():
    from shared.models import ObjectClassification

    col_names = [c.name for c in ObjectClassification.__table__.columns]
    assert "feature_vector" in col_names, f"feature_vector missing; got {col_names}"


def test_object_classification_has_anomaly_explanation():
    from shared.models import ObjectClassification

    col_names = [c.name for c in ObjectClassification.__table__.columns]
    assert "anomaly_explanation" in col_names, (
        f"anomaly_explanation missing; got {col_names}"
    )


def test_object_classification_has_all_required_columns():
    from shared.models import ObjectClassification

    col_names = {c.name for c in ObjectClassification.__table__.columns}
    required = {
        "classification_uuid",
        "object_uuid",
        "predicted_object_type",
        "classification_confidence_score",
        "ml_model_version",
        "feature_extractor_version",
        "feature_vector",
        "is_anomaly_flagged",
        "anomaly_score",
        "anomaly_explanation",
        "classified_at",
    }
    missing = required - col_names
    assert not missing, f"ObjectClassification missing columns: {missing}"


def test_astronomical_object_has_catalog_object_name():
    from shared.models import AstronomicalObject

    col_names = [c.name for c in AstronomicalObject.__table__.columns]
    assert "catalog_object_name" in col_names


def test_astronomical_object_catalog_object_name_is_indexed():
    from shared.models import AstronomicalObject

    indexed_cols = {
        col.name
        for idx in AstronomicalObject.__table__.indexes
        for col in idx.columns
    }
    assert "catalog_object_name" in indexed_cols, (
        "catalog_object_name is not indexed"
    )


def test_astronomical_object_has_catalog_magnitude():
    from shared.models import AstronomicalObject

    col_names = [c.name for c in AstronomicalObject.__table__.columns]
    assert "catalog_magnitude" in col_names


def test_astronomical_object_has_catalog_redshift():
    from shared.models import AstronomicalObject

    col_names = [c.name for c in AstronomicalObject.__table__.columns]
    assert "catalog_redshift" in col_names


# ---------------------------------------------------------------------------
# Task 2: Catalog client modules — import-only (offline)
# ---------------------------------------------------------------------------


def test_simbad_client_importable():
    from pipeline.catalog_clients import simbad_client  # noqa: F401


def test_ned_client_importable():
    from pipeline.catalog_clients import ned_client  # noqa: F401


def test_sdss_client_importable():
    from pipeline.catalog_clients import sdss_client  # noqa: F401


def test_gaia_client_importable():
    from pipeline.catalog_clients import gaia_client  # noqa: F401


def test_simbad_client_has_query_region():
    from pipeline.catalog_clients import simbad_client

    assert hasattr(simbad_client, "query_simbad_region"), (
        "simbad_client missing query_simbad_region"
    )


def test_ned_client_has_query_region():
    from pipeline.catalog_clients import ned_client

    assert hasattr(ned_client, "query_ned_region"), (
        "ned_client missing query_ned_region"
    )


def test_sdss_client_has_query_region():
    from pipeline.catalog_clients import sdss_client

    assert hasattr(sdss_client, "query_sdss_region"), (
        "sdss_client missing query_sdss_region"
    )


def test_gaia_client_has_query_region():
    from pipeline.catalog_clients import gaia_client

    assert hasattr(gaia_client, "query_gaia_region"), (
        "gaia_client missing query_gaia_region"
    )


# ---------------------------------------------------------------------------
# Task 2: compute_search_radius_arcsec
# ---------------------------------------------------------------------------


def test_compute_search_radius_compact_source_returns_approx_2_arcsec():
    """Compact source (1 pixel × 0.1 arcsec/px = 0.1 arcsec extent) → ~2 arcsec."""
    from pipeline.catalog_clients import compute_search_radius_arcsec

    radius = compute_search_radius_arcsec(
        bounding_box_pixels={"xmin": 0, "xmax": 1, "ymin": 0, "ymax": 1},
        pixel_scale_arcsec_per_pixel=0.1,
    )
    assert 1.8 <= radius <= 3.0, f"Expected ~2 arcsec for compact source, got {radius}"


def test_compute_search_radius_extended_source_scales_up():
    """Extended source (200 px × 0.1 arcsec/px = 20 arcsec extent) → scales up."""
    from pipeline.catalog_clients import compute_search_radius_arcsec

    compact_radius = compute_search_radius_arcsec(
        bounding_box_pixels={"xmin": 0, "xmax": 1, "ymin": 0, "ymax": 1},
        pixel_scale_arcsec_per_pixel=0.1,
    )
    extended_radius = compute_search_radius_arcsec(
        bounding_box_pixels={"xmin": 0, "xmax": 200, "ymin": 0, "ymax": 200},
        pixel_scale_arcsec_per_pixel=0.1,
    )
    assert extended_radius > compact_radius, (
        f"Extended radius ({extended_radius}) should exceed compact ({compact_radius})"
    )
    assert extended_radius >= 5.0, f"Extended radius too small: {extended_radius}"


# ---------------------------------------------------------------------------
# Task 2: Catalog clients return not_queried on final failure (offline mock)
# ---------------------------------------------------------------------------


def test_simbad_client_returns_not_queried_on_failure():
    """On repeated failure, query_simbad_region must return a not_queried sentinel."""
    from astropy.coordinates import SkyCoord
    from pipeline.catalog_clients.simbad_client import query_simbad_region

    coord = SkyCoord(ra=10.0, dec=20.0, unit="deg")
    # Patch the Simbad constructor so any instance's query_region raises.
    # astroquery uses @class_or_instance descriptors that resist class-level
    # attribute patching — mocking the constructor is reliable.
    mock_instance = mock.MagicMock()
    mock_instance.query_region.side_effect = Exception("network error")
    with mock.patch(
        "pipeline.catalog_clients.simbad_client.Simbad",
        return_value=mock_instance,
    ):
        result = query_simbad_region(coord, radius_arcsec=2.0)

    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0].get("status") == "not_queried", (
        f"Expected not_queried sentinel, got {result[0]}"
    )


def test_ned_client_returns_not_queried_on_failure():
    from astropy.coordinates import SkyCoord
    from pipeline.catalog_clients.ned_client import query_ned_region

    coord = SkyCoord(ra=10.0, dec=20.0, unit="deg")
    with mock.patch(
        "pipeline.catalog_clients.ned_client.Ned.query_region",
        side_effect=Exception("network error"),
    ):
        result = query_ned_region(coord, radius_arcsec=2.0)

    assert isinstance(result, list)
    assert result[0].get("status") == "not_queried"


def test_sdss_client_returns_not_queried_on_failure():
    from astropy.coordinates import SkyCoord
    from pipeline.catalog_clients.sdss_client import query_sdss_region

    coord = SkyCoord(ra=10.0, dec=20.0, unit="deg")
    with mock.patch(
        "pipeline.catalog_clients.sdss_client.SDSS.query_region",
        side_effect=Exception("network error"),
    ):
        result = query_sdss_region(coord, radius_arcsec=2.0)

    assert isinstance(result, list)
    assert result[0].get("status") == "not_queried"


def test_gaia_client_returns_not_queried_on_failure():
    from astropy.coordinates import SkyCoord
    from pipeline.catalog_clients.gaia_client import query_gaia_region

    coord = SkyCoord(ra=10.0, dec=20.0, unit="deg")
    with mock.patch(
        "pipeline.catalog_clients.gaia_client.Gaia.cone_search_async",
        side_effect=Exception("network error"),
    ):
        result = query_gaia_region(coord, radius_arcsec=2.0)

    assert isinstance(result, list)
    assert result[0].get("status") == "not_queried"


# ---------------------------------------------------------------------------
# Task 3: 9-task chain and pipeline status ownership
# ---------------------------------------------------------------------------


def test_ingest_observation_chain_has_9_tasks():
    from pipeline.tasks.ingest import ingest_observation

    src = inspect.getsource(ingest_observation)
    # download_fits.s() is called with args on separate lines, so check without ')'
    assert "download_fits.s(" in src, "Missing download_fits.s( in ingest chain"
    for task_name in (
        "validate_wcs.s()",
        "generate_tiles.s()",
        "detect_sources.s()",
        "segment_sam.s()",
        "generate_cutouts.s()",
        "cross_match_catalogs.s()",
        "classify_objects.s()",
        "detect_anomalies.s()",
    ):
        assert task_name in src, f"Missing {task_name!r} in ingest_observation chain"


def test_generate_cutouts_does_not_set_pipeline_completed():
    """generate_cutouts must NOT assign pipeline_status = PipelineStatus.completed."""
    import pipeline.tasks.generate_cutouts as gc_module

    src = inspect.getsource(gc_module)
    # Reject the actual DB assignment, not merely a mention in comments/docstrings.
    assert "pipeline_status = PipelineStatus.completed" not in src, (
        "generate_cutouts still assigns pipeline_status = PipelineStatus.completed — "
        "ownership must be in detect_anomalies"
    )


def test_stub_tasks_raise_not_implemented():
    from pipeline.tasks.cross_match_catalogs import cross_match_catalogs
    from pipeline.tasks.classify_objects import classify_objects
    from pipeline.tasks.detect_anomalies import detect_anomalies
    import pytest

    with pytest.raises(NotImplementedError):
        cross_match_catalogs.run({})
    with pytest.raises(NotImplementedError):
        classify_objects.run({})
    with pytest.raises(NotImplementedError):
        detect_anomalies.run({})


# ---------------------------------------------------------------------------
# Task 4: pyproject.toml declares scikit-learn and statmorph
# ---------------------------------------------------------------------------


def test_pyproject_declares_scikit_learn():
    import tomllib
    from pathlib import Path

    data = tomllib.loads(
        (Path(__file__).parent.parent / "pyproject.toml").read_text()
    )
    deps = data["project"]["dependencies"]
    assert any("scikit-learn" in d for d in deps), (
        f"scikit-learn not in dependencies: {deps}"
    )


def test_pyproject_declares_statmorph():
    import tomllib
    from pathlib import Path

    data = tomllib.loads(
        (Path(__file__).parent.parent / "pyproject.toml").read_text()
    )
    deps = data["project"]["dependencies"]
    assert any("statmorph" in d for d in deps), (
        f"statmorph not in dependencies: {deps}"
    )
