---
phase: 05-classification-cross-matching
plan: 02
type: summary
completed_at: 2026-08-06
issue: "#4"
branch: feat/phase5-plan2-crossmatch-classify
---

# Plan 02 Summary — Cross-match & ML Classification

## What was built

### `pipeline/feature_extraction.py` (160 lines)
- `extract_feature_vector(cutout_data, rle_mask, sep_physical_properties, gain)` — dual-path extractor
- **Path A (statmorph)**: decodes COCO RLE mask via pycocotools, runs `statmorph.source_morphology`, returns 10 morphological features (concentration, asymmetry, smoothness, Gini, M20, Sérsic n/rhalf, ellipticity + flags)
- **Path B (SEP fallback)**: activated when `rle_mask is None` or `morph.flag >= 2`; computes ellipticity from `sep_a/sep_b`, sets statmorph features to -999.0 sentinel
- All NaN/Inf replaced with -999.0 sentinel throughout; `feature_source` key documents which path ran

### `pipeline/ml_models/__init__.py` + `pipeline/ml_models/classifier.py` (131 lines)
- `FEATURE_COLUMNS` — 10-element ordered list used for training and prediction
- `OBJECT_TYPE_LABELS` — 16 detailed subtypes including all required (star, spiral_galaxy, elliptical_galaxy, planetary_nebula, artifact, unknown)
- `load_or_create_classifier(s3_client, key, bucket)` — downloads joblib model from S3; returns **None** (not an exception) when no model exists
- `predict_object_types(clf, feature_matrix)` — imputes -999.0 sentinels with column medians before `predict`/`predict_proba`; returns `(predictions, confidence_scores, probabilities)`
- `save_classifier(clf, s3_client, key, bucket)` — joblib serialise + S3 upload

### `pipeline/tasks/cross_match_catalogs.py` (361 lines)
- Replaces Plan 1 stub; fully implements the seventh pipeline step
- `_get_pixel_scale()` — downloads first FITS, derives arcsec/px from `wcs.pixel_scale_matrix`; falls back to 0.063 arcsec/px (JWST default) on any error
- `ThreadPoolExecutor(max_workers=4)` — all 4 catalogs queried in parallel per object
- Stores ALL matches as `CatalogCrossMatch` records with `angular_separation_arcseconds` and `match_probability_score = 1/(1+sep)`
- `not_queried` sentinel from catalog clients → logged, catalog added to `catalogs_failed` set, no CatalogCrossMatch created; task continues
- Updates `AstronomicalObject` indexed fields (catalog_object_name, classified_object_type, classification_source_catalog, catalog_magnitude, catalog_redshift) using priority SIMBAD > NED > SDSS > Gaia — only fills fields not yet set
- Flushes every 50 objects; full ProcessingStep lifecycle (running → completed/failed)

### `pipeline/tasks/classify_objects.py` (281 lines)
- Replaces Plan 1 stub; fully implements the eighth pipeline step
- Queries ALL AstronomicalObjects — no filter on `segmentation_mask_rle` (ML runs on every object)
- Objects with mask+cutout: downloads `{cutout_s3_prefix}cutout.fits` from segmentation bucket → statmorph path
- Objects without mask: SEP-only path directly
- `detection_signal_to_noise_ratio` merged from AstronomicalObject column into `sep_physical_properties` dict
- `load_or_create_classifier` → None when no model: classifies all as "unknown", confidence 0.0, logs warning; pipeline does NOT crash
- Creates append-only `ObjectClassification` records with full `feature_vector` JSONB, `ml_model_version`, `feature_extractor_version="statmorph_0.7+sep"`, `is_anomaly_flagged=False`

### `tests/test_classification_schema.py` (updated)
- Narrowed `test_stub_tasks_raise_not_implemented` to test only `detect_anomalies` (cross_match and classify are now real)
- Added 18 new offline tests in pure-mock style:
  - 4 feature extraction tests (sep_fallback, no-props sentinels, NaN/Inf handling)
  - 5 classifier module tests (labels, feature count, no-S3-model → None, sentinel imputation)
  - 4 cross_match_catalogs tests (ThreadPoolExecutor usage, implementation check, real matches → CatalogCrossMatch, not_queried → no record)
  - 4 classify_objects tests (maskless object classification, no-model → unknown/0.0, feature_vector JSONB stored)

## Test results

```
54 passed in 14.04s
```
All three offline suites green: test_classification_schema.py (44), test_celery.py (2), test_knowledge_graph.py (8).

## Deviations from plan

None. All `must_haves` truths and artifact `min_lines` constraints satisfied.

## Remaining work (Plan 3 — issue #5)

- `pipeline/tasks/detect_anomalies.py` — implement Isolation Forest anomaly detection, set `PipelineStatus.completed`
