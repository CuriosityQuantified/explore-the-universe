---
phase: 05-classification-cross-matching
plan: 03
type: summary
completed_at: 2026-08-06
issue: "#5"
branch: feat/phase5-anomaly-detection
---

# Plan 03 Summary — Anomaly Detection + Classification API

## What was built

### `pipeline/tasks/detect_anomalies.py` (260 lines, replacing 23-line stub)

- `detect_anomalies(self, classification_result)` — ninth (final) Celery task in the pipeline chain
- **IsolationForest scoring**: fits `IsolationForest(n_estimators=200, contamination=settings.classification_anomaly_contamination, random_state=42, n_jobs=-1)` on the full feature matrix when ≥ 10 objects exist; skips gracefully (all scores=0.0, predictions=normal) for smaller sets with a logged warning
- **5 independent signals** checked per object:
  1. Feature vector outlier (IF prediction == -1)
  2. ML↔catalog type disagreement (both non-unknown, non-artifact, and differ)
  3. Zero CatalogCrossMatch records (group-by query)
  4. Statmorph flag ≥ 2 (from `feature_vector["flag"]`)
  5. ML confidence < 0.3
- **Artifact exclusion**: `predicted_object_type == "artifact"` → never flagged, regardless of signals
- **Human-readable explanations**: semicolon-joined string of every triggered signal (e.g. `"ML type 'spiral_galaxy' disagrees with catalog type 'star'; ML confidence below threshold (0.15)"`)
- **S3 model persistence**: `_save_model_to_s3()` serializes fitted IsolationForest with joblib → `settings.s3_bucket_models / settings.classification_anomaly_model_s3_key`
- **Pipeline finalization**: sets `Observation.pipeline_status = PipelineStatus.completed`; creates completed `ProcessingStep` with `signals_distribution` metadata
- **Batch flush**: every 50 objects; full ProcessingStep lifecycle (running → completed/failed); on failure marks Observation as `PipelineStatus.failed` then re-raises

### `api/routers/objects.py` (new, 160 lines)

Three endpoints with Pydantic response models:

- `GET /api/objects/{object_uuid}/classifications` → `list[ClassificationResponse]`
  - Full append-only history, `ORDER BY classified_at DESC`
  - 404 if object_uuid not in `AstronomicalObject`
- `GET /api/objects/{object_uuid}/cross-matches` → `list[CrossMatchResponse]`
  - All `CatalogCrossMatch` records, `ORDER BY angular_separation_arcseconds ASC`
  - 404 if object not found
- `GET /api/observations/{observation_uuid}/anomalies` → `list[AnomalyResponse]`
  - All `AstronomicalObject` where `is_anomaly_flagged=True` for the observation
  - Joins latest flagged `ObjectClassification` per object for anomaly score/explanation
  - Returns `[]` (not 404) when no anomalies exist

### `api/main.py` (updated)

Added `from api.routers.objects import router as objects_router` + `app.include_router(objects_router)`.

### `tests/test_classification_schema.py` (updated)

- **Retired** `test_stub_tasks_raise_not_implemented` (no stubs remain after Plan 3)
- **Added** `test_no_stub_tasks_remain` — positive assertion that all three Plan-5 tasks are fully implemented
- **Added** 9 new offline tests for `detect_anomalies`:
  - Import/source checks (IsolationForest present, 5 signals present, artifact exclusion, PipelineStatus.completed)
  - Behavioral mock tests: small observation skips IF, artifact never flagged, explanation is human-readable string

### `tests/test_anomaly_api.py` (new — CI regression suite, 11 tests)

Offline FastAPI TestClient tests with dependency-override mock sessions:
- `classifications`: 404 for unknown UUID; history ordered newest-first with correct fields
- `cross-matches`: 404 for unknown UUID; matches ordered by angular_separation_arcseconds
- `anomalies`: `[]` (not 404) for observation with no anomalies; correct payload with explanation for flagged objects
- `test_objects_router_registered_in_app`: verifies all 3 paths appear in `/openapi.json`

### `.github/workflows/ci.yml` (updated)

Added `tests/test_anomaly_api.py` to the `unit-tests` job's pytest command.

## Test results

```
69 passed in 13.75s
```

Suites: test_celery.py (2), test_classification_schema.py (56), test_knowledge_graph.py (8), test_anomaly_api.py (11) — all green.

## Knowledge graph

```
graphify update . → 808 nodes, 1268 edges, 86 communities
check_graph_fresh.py → Knowledge graph is current
```

## Deviations from plan

None. All `must_haves` truths and artifact constraints satisfied. The `objects_router` is in `api/routers/objects.py` as specified. The router variable is named `objects_router` in `api/main.py` per the spec's `contains: "objects_router"` constraint.

## Prototype comparison

No competing approaches were needed — the spec fully constrains the implementation (IsolationForest parameters, signal list, artifact exclusion, API endpoint shapes). The mock session pattern for the behavioral tests was iterated once: initial `side_effect` list on `filter().all()` failed because the task uses different chain patterns per query (`.order_by().all()`, `.group_by().all()`); switched to a call-count `query.side_effect` dispatcher which correctly routes each query call.
