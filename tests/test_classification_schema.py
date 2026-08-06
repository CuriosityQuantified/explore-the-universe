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
    """Only detect_anomalies remains a stub after Plan 2; cross_match and classify are real."""
    from pipeline.tasks.detect_anomalies import detect_anomalies
    import pytest

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


# ---------------------------------------------------------------------------
# Plan 2: feature extraction module
# ---------------------------------------------------------------------------


def test_feature_extraction_importable():
    from pipeline.feature_extraction import extract_feature_vector  # noqa: F401


def test_extract_feature_vector_sep_fallback_for_maskless():
    """Maskless object (rle_mask=None) returns sep_fallback with ellipticity computed."""
    import numpy as np
    from pipeline.feature_extraction import extract_feature_vector

    sep_props = {"sep_a": 4.0, "sep_b": 2.0, "sep_flux": 500.0}
    fv = extract_feature_vector(None, None, sep_physical_properties=sep_props)

    assert fv["feature_source"] == "sep_fallback"
    assert abs(fv["ellipticity"] - 0.5) < 1e-9, f"Expected 0.5, got {fv['ellipticity']}"
    assert fv["concentration"] == -999.0, "statmorph features must be sentinel for SEP fallback"
    assert fv["sep_flux"] == 500.0


def test_extract_feature_vector_no_mask_no_sep_returns_sentinels():
    """No mask, no SEP props → all statmorph features are -999.0 sentinels."""
    from pipeline.feature_extraction import extract_feature_vector

    fv = extract_feature_vector(None, None, sep_physical_properties={})
    assert fv["feature_source"] == "sep_fallback"
    assert fv["concentration"] == -999.0
    assert fv["gini"] == -999.0


def test_extract_feature_vector_nan_replaced_by_sentinel():
    """NaN/Inf values in sep_props propagate as -999.0 sentinel."""
    import math
    from pipeline.feature_extraction import extract_feature_vector

    sep_props = {"sep_a": float("nan"), "sep_b": float("inf"), "sep_flux": -999.0}
    fv = extract_feature_vector(None, None, sep_physical_properties=sep_props)
    assert fv["sep_a"] == -999.0
    assert fv["sep_b"] == -999.0


# ---------------------------------------------------------------------------
# Plan 2: classifier module
# ---------------------------------------------------------------------------


def test_classifier_module_importable():
    from pipeline.ml_models.classifier import (  # noqa: F401
        FEATURE_COLUMNS,
        OBJECT_TYPE_LABELS,
        load_or_create_classifier,
        predict_object_types,
    )


def test_object_type_labels_include_required_types():
    from pipeline.ml_models.classifier import OBJECT_TYPE_LABELS

    required = {
        "star",
        "spiral_galaxy",
        "elliptical_galaxy",
        "planetary_nebula",
        "artifact",
        "unknown",
    }
    missing = required - set(OBJECT_TYPE_LABELS)
    assert not missing, f"OBJECT_TYPE_LABELS missing required types: {missing}"


def test_feature_columns_has_at_least_eight():
    from pipeline.ml_models.classifier import FEATURE_COLUMNS

    assert len(FEATURE_COLUMNS) >= 8, (
        f"Expected >= 8 feature columns, got {len(FEATURE_COLUMNS)}: {FEATURE_COLUMNS}"
    )


def test_load_or_create_classifier_returns_none_when_no_s3_model():
    """load_or_create_classifier returns None (not an exception) when S3 has no model."""
    from pipeline.ml_models.classifier import load_or_create_classifier

    mock_s3 = mock.MagicMock()
    mock_s3.download_file.side_effect = Exception("NoSuchKey")

    result = load_or_create_classifier(mock_s3, "models/missing.joblib", "models")
    assert result is None, f"Expected None, got {result}"


def test_predict_object_types_imputes_sentinels():
    """predict_object_types handles -999.0 sentinels without crashing."""
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from pipeline.ml_models.classifier import FEATURE_COLUMNS, predict_object_types

    n_features = len(FEATURE_COLUMNS)
    X_train = np.random.rand(20, n_features)
    y_train = ["star"] * 10 + ["unknown"] * 10
    clf = RandomForestClassifier(n_estimators=5, random_state=42)
    clf.fit(X_train, y_train)

    # Matrix with some sentinel values
    X_test = np.full((3, n_features), -999.0)
    X_test[0, 0] = 0.5  # one real value

    predictions, confidence_scores, probabilities = predict_object_types(clf, X_test)
    assert predictions.shape == (3,)
    assert confidence_scores.shape == (3,)
    assert all(0.0 <= c <= 1.0 for c in confidence_scores)


# ---------------------------------------------------------------------------
# Plan 2: cross_match_catalogs task — offline mock-session tests
# ---------------------------------------------------------------------------


def test_cross_match_catalogs_uses_thread_pool():
    import inspect
    from pipeline.tasks.cross_match_catalogs import cross_match_catalogs

    src = inspect.getsource(cross_match_catalogs)
    assert "ThreadPoolExecutor" in src, "cross_match_catalogs must use ThreadPoolExecutor"


def test_cross_match_catalogs_not_implemented_removed():
    import inspect
    from pipeline.tasks.cross_match_catalogs import cross_match_catalogs

    src = inspect.getsource(cross_match_catalogs)
    assert "NotImplementedError" not in src, (
        "cross_match_catalogs must be fully implemented (no NotImplementedError)"
    )


def test_cross_match_catalogs_creates_crossmatch_records_for_real_matches():
    """CatalogCrossMatch records are created for real catalog matches (mock session)."""
    import uuid as _uuid
    from pipeline.tasks import cross_match_catalogs as xm_mod
    from pipeline.tasks.cross_match_catalogs import cross_match_catalogs
    from shared.models import CatalogCrossMatch

    obs_uuid = _uuid.uuid4()
    obj = mock.MagicMock()
    obj.object_uuid = _uuid.uuid4()
    obj.sky_coordinate_ra_degrees = 10.0
    obj.sky_coordinate_dec_degrees = 20.0
    obj.bounding_box_pixels = {"xmin": 0, "xmax": 5, "ymin": 0, "ymax": 5}
    obj.catalog_object_name = None
    obj.classified_object_type = None
    obj.classification_source_catalog = None
    obj.catalog_magnitude = None
    obj.catalog_redshift = None

    added_records: list = []
    fake_session = mock.MagicMock()
    fake_session.query.return_value.filter.return_value.all.return_value = [obj]
    fake_session.query.return_value.filter.return_value.first.return_value = None
    fake_session.add.side_effect = added_records.append

    simbad_match = {
        "catalog": "simbad",
        "catalog_source_id": "NGC 1234",
        "object_type": "G",
        "angular_separation_arcsec": 1.2,
        "magnitude": 15.3,
        "redshift": 0.05,
    }
    no_match_fn = mock.MagicMock(return_value=[])
    simbad_fn = mock.MagicMock(return_value=[simbad_match])

    mock_catalog_fns = {
        "simbad": simbad_fn,
        "ned": no_match_fn,
        "sdss": no_match_fn,
        "gaia": no_match_fn,
    }

    with (
        mock.patch.object(xm_mod, "SessionLocal", return_value=fake_session),
        mock.patch.object(xm_mod, "_get_pixel_scale", return_value=0.031),
        mock.patch.dict(
            "pipeline.tasks.cross_match_catalogs.__dict__",
            {},
        ),
    ):
        # Patch catalog_fns inside the task by patching simbad_client etc.
        with (
            mock.patch.object(xm_mod.simbad_client, "query_simbad_region", simbad_fn),
            mock.patch.object(xm_mod.ned_client, "query_ned_region", no_match_fn),
            mock.patch.object(xm_mod.sdss_client, "query_sdss_region", no_match_fn),
            mock.patch.object(xm_mod.gaia_client, "query_gaia_region", no_match_fn),
        ):
            result = cross_match_catalogs.run({"observation_uuid": obs_uuid.hex})

    crossmatch_records = [r for r in added_records if isinstance(r, CatalogCrossMatch)]
    assert len(crossmatch_records) == 1, (
        f"Expected 1 CatalogCrossMatch, got {len(crossmatch_records)}"
    )
    assert crossmatch_records[0].catalog_name == "simbad"
    assert result["total_matches"] == 1
    # AstronomicalObject indexed fields updated from SIMBAD
    assert obj.catalog_object_name == "NGC 1234"
    assert obj.classified_object_type == "G"


def test_cross_match_catalogs_not_queried_on_catalog_failure():
    """Catalog failure → no CatalogCrossMatch, task continues without aborting."""
    import uuid as _uuid
    from pipeline.tasks import cross_match_catalogs as xm_mod
    from pipeline.tasks.cross_match_catalogs import cross_match_catalogs
    from shared.models import CatalogCrossMatch

    obs_uuid = _uuid.uuid4()
    obj = mock.MagicMock()
    obj.object_uuid = _uuid.uuid4()
    obj.sky_coordinate_ra_degrees = 10.0
    obj.sky_coordinate_dec_degrees = 20.0
    obj.bounding_box_pixels = {"xmin": 0, "xmax": 5, "ymin": 0, "ymax": 5}
    obj.catalog_object_name = None
    obj.classified_object_type = None
    obj.classification_source_catalog = None
    obj.catalog_magnitude = None
    obj.catalog_redshift = None

    added_records: list = []
    fake_session = mock.MagicMock()
    fake_session.query.return_value.filter.return_value.all.return_value = [obj]
    fake_session.query.return_value.filter.return_value.first.return_value = None
    fake_session.add.side_effect = added_records.append

    not_queried = [{"status": "not_queried", "catalog": "simbad", "error": "timeout"}]
    failed_fn = mock.MagicMock(return_value=not_queried)
    no_match_fn = mock.MagicMock(return_value=[])

    with (
        mock.patch.object(xm_mod, "SessionLocal", return_value=fake_session),
        mock.patch.object(xm_mod, "_get_pixel_scale", return_value=0.031),
        mock.patch.object(xm_mod.simbad_client, "query_simbad_region", failed_fn),
        mock.patch.object(xm_mod.ned_client, "query_ned_region", no_match_fn),
        mock.patch.object(xm_mod.sdss_client, "query_sdss_region", no_match_fn),
        mock.patch.object(xm_mod.gaia_client, "query_gaia_region", no_match_fn),
    ):
        result = cross_match_catalogs.run({"observation_uuid": obs_uuid.hex})

    crossmatch_records = [r for r in added_records if isinstance(r, CatalogCrossMatch)]
    assert len(crossmatch_records) == 0, "not_queried sentinel must NOT create a CatalogCrossMatch"
    assert result["total_matches"] == 0
    assert result["status"] == "completed", "Task must complete (not abort) on catalog failure"


# ---------------------------------------------------------------------------
# Plan 2: classify_objects task — offline mock-session tests
# ---------------------------------------------------------------------------


def test_classify_objects_not_implemented_removed():
    import inspect
    from pipeline.tasks.classify_objects import classify_objects

    src = inspect.getsource(classify_objects)
    assert "NotImplementedError" not in src


def test_classify_objects_creates_classification_for_maskless_object():
    """classify_objects creates ObjectClassification for objects without SAM masks."""
    import uuid as _uuid
    from pipeline.tasks import classify_objects as co_mod
    from pipeline.tasks.classify_objects import classify_objects
    from shared.models import ObjectClassification

    obs_uuid = _uuid.uuid4()
    # Object with NO segmentation mask (SEP-only)
    obj = mock.MagicMock()
    obj.object_uuid = _uuid.uuid4()
    obj.source_observation_uuid = obs_uuid
    obj.segmentation_mask_rle = None
    obj.cutout_s3_prefix = None
    obj.physical_properties = {"sep_a": 3.0, "sep_b": 2.0, "sep_flux": 100.0}
    obj.detection_signal_to_noise_ratio = 5.0

    added_records: list = []
    fake_session = mock.MagicMock()
    fake_session.query.return_value.filter.return_value.all.return_value = [obj]
    fake_session.query.return_value.filter.return_value.first.return_value = None
    fake_session.add.side_effect = added_records.append

    mock_s3 = mock.MagicMock()
    # No model in S3
    mock_s3.download_file.side_effect = Exception("NoSuchKey")

    with (
        mock.patch.object(co_mod, "SessionLocal", return_value=fake_session),
        mock.patch.object(co_mod, "get_s3_client", return_value=mock_s3),
    ):
        result = classify_objects.run({"observation_uuid": obs_uuid.hex})

    classifications = [r for r in added_records if isinstance(r, ObjectClassification)]
    assert len(classifications) == 1, (
        f"Expected 1 ObjectClassification, got {len(classifications)}"
    )
    assert result["objects_classified"] == 1
    # No model → classified as unknown
    assert classifications[0].predicted_object_type == "unknown"
    assert classifications[0].classification_confidence_score == 0.0
    assert "feature_source" in classifications[0].feature_vector


def test_classify_objects_no_model_classifies_as_unknown():
    """When no ML model exists in S3, all objects get predicted_type='unknown', confidence=0.0."""
    import uuid as _uuid
    from pipeline.tasks import classify_objects as co_mod
    from pipeline.tasks.classify_objects import classify_objects
    from shared.models import ObjectClassification

    obs_uuid = _uuid.uuid4()
    objects = []
    for _ in range(3):
        o = mock.MagicMock()
        o.object_uuid = _uuid.uuid4()
        o.segmentation_mask_rle = None
        o.cutout_s3_prefix = None
        o.physical_properties = {}
        o.detection_signal_to_noise_ratio = 1.0
        objects.append(o)

    added_records: list = []
    fake_session = mock.MagicMock()
    fake_session.query.return_value.filter.return_value.all.return_value = objects
    fake_session.query.return_value.filter.return_value.first.return_value = None
    fake_session.add.side_effect = added_records.append

    mock_s3 = mock.MagicMock()
    mock_s3.download_file.side_effect = Exception("NoSuchKey")

    with (
        mock.patch.object(co_mod, "SessionLocal", return_value=fake_session),
        mock.patch.object(co_mod, "get_s3_client", return_value=mock_s3),
    ):
        result = classify_objects.run({"observation_uuid": obs_uuid.hex})

    classifications = [r for r in added_records if isinstance(r, ObjectClassification)]
    assert len(classifications) == 3
    for c in classifications:
        assert c.predicted_object_type == "unknown"
        assert c.classification_confidence_score == 0.0
    assert result["model_version"] == "no_model"


def test_classify_objects_stores_feature_vector_jsonb():
    """ObjectClassification.feature_vector is a non-empty dict (JSONB payload)."""
    import uuid as _uuid
    from pipeline.tasks import classify_objects as co_mod
    from pipeline.tasks.classify_objects import classify_objects
    from shared.models import ObjectClassification

    obs_uuid = _uuid.uuid4()
    obj = mock.MagicMock()
    obj.object_uuid = _uuid.uuid4()
    obj.segmentation_mask_rle = None
    obj.cutout_s3_prefix = None
    obj.physical_properties = {"sep_a": 2.0, "sep_b": 1.5, "sep_flux": 200.0}
    obj.detection_signal_to_noise_ratio = 8.0

    added_records: list = []
    fake_session = mock.MagicMock()
    fake_session.query.return_value.filter.return_value.all.return_value = [obj]
    fake_session.query.return_value.filter.return_value.first.return_value = None
    fake_session.add.side_effect = added_records.append

    mock_s3 = mock.MagicMock()
    mock_s3.download_file.side_effect = Exception("NoSuchKey")

    with (
        mock.patch.object(co_mod, "SessionLocal", return_value=fake_session),
        mock.patch.object(co_mod, "get_s3_client", return_value=mock_s3),
    ):
        classify_objects.run({"observation_uuid": obs_uuid.hex})

    classifications = [r for r in added_records if isinstance(r, ObjectClassification)]
    assert len(classifications) == 1
    fv = classifications[0].feature_vector
    assert isinstance(fv, dict), f"feature_vector must be a dict, got {type(fv)}"
    assert len(fv) > 0, "feature_vector must not be empty"
    assert "feature_source" in fv
