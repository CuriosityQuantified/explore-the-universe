"""Classify Celery task: feature extraction + RF classification for every object.

Eighth step in the 9-task pipeline chain:
  download_fits -> validate_wcs -> generate_tiles -> detect_sources
  -> segment_sam -> generate_cutouts -> cross_match_catalogs
  -> classify_objects -> detect_anomalies

Receives the output dict from cross_match_catalogs.

Every AstronomicalObject in the observation is classified — including those
without a SAM segmentation mask (they receive SEP-only feature vectors).
If no pre-trained RF model exists in S3, all objects are classified as
'unknown' with confidence 0.0; the pipeline does NOT crash.

ObjectClassification records are append-only — one per object per pipeline run.
The anomaly_score and anomaly_explanation fields are left null here and filled
by the detect_anomalies task (Plan 3).
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from typing import Optional

import numpy as np
from astropy.io import fits
from sqlalchemy import func as sql_func

from api.db.session import SessionLocal
from pipeline.celery_app import celery_app
from pipeline.feature_extraction import extract_feature_vector
from pipeline.ml_models.classifier import (
    FEATURE_COLUMNS,
    load_or_create_classifier,
    predict_object_types,
)
from shared.config import settings
from shared.models import (
    AstronomicalObject,
    ObjectClassification,
    Observation,
    PipelineStatus,
    ProcessingStep,
    StepStatus,
)
from shared.s3 import get_s3_client

logger = logging.getLogger(__name__)

_FEATURE_EXTRACTOR_VERSION = "statmorph_0.7+sep"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _download_cutout(s3_client, cutout_s3_prefix: str) -> np.ndarray:
    """Download cutout.fits from MinIO and return its data as a float64 array."""
    s3_key = f"{cutout_s3_prefix}cutout.fits"
    fd, temp_path = tempfile.mkstemp(suffix=".fits")
    os.close(fd)
    try:
        s3_client.download_file(settings.s3_bucket_segmentation, s3_key, temp_path)
        with fits.open(temp_path) as hdul:
            for hdu in hdul:
                if hdu.data is not None and hdu.header.get("NAXIS", 0) >= 2:
                    return np.array(hdu.data, dtype=np.float64)
            return np.array(hdul[0].data, dtype=np.float64)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _build_feature_matrix(feature_vectors: list[dict]) -> np.ndarray:
    """Convert list of feature dicts to a numeric matrix (n_objects × n_features)."""
    matrix = np.full((len(feature_vectors), len(FEATURE_COLUMNS)), -999.0)
    for i, fv in enumerate(feature_vectors):
        for j, col in enumerate(FEATURE_COLUMNS):
            val = fv.get(col, -999.0)
            if val is None:
                val = -999.0
            try:
                f = float(val)
                matrix[i, j] = f if np.isfinite(f) else -999.0
            except (TypeError, ValueError):
                pass
    return matrix


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, acks_late=True)
def classify_objects(self, cross_match_result: dict) -> dict:
    """Extract morphological features and classify objects using a trained ML model.

    Eighth step in the 9-task pipeline chain.
    Receives the output dict from cross_match_catalogs.
    """
    observation_uuid_hex = cross_match_result["observation_uuid"]
    observation_uuid = uuid.UUID(observation_uuid_hex)

    database_session = SessionLocal()
    processing_step: Optional[ProcessingStep] = None

    try:
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="classify_objects",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        logger.info("Starting classification for observation %s", observation_uuid_hex)

        # Query ALL objects — no filter on segmentation_mask_rle; ML runs on every object
        all_objects = (
            database_session.query(AstronomicalObject)
            .filter(AstronomicalObject.source_observation_uuid == observation_uuid)
            .all()
        )

        if not all_objects:
            processing_step.step_status = StepStatus.completed
            processing_step.step_completed_at = sql_func.now()
            processing_step.step_output_metadata = {
                "objects_classified": 0,
                "model_version": "no_objects",
                "feature_extraction_failures": 0,
            }
            database_session.commit()
            return {
                "observation_uuid": observation_uuid_hex,
                "objects_classified": 0,
                "model_version": "no_objects",
                "status": "completed",
            }

        # Load ML classifier (returns None when no model exists in S3)
        s3_client = get_s3_client()
        classifier = None
        try:
            classifier = load_or_create_classifier(
                s3_client,
                settings.classification_ml_model_s3_key,
                settings.s3_bucket_models,
            )
        except Exception as exc:
            logger.warning("Could not load ML classifier: %s — all objects → 'unknown'", exc)

        model_version = "rf_v1.0" if classifier is not None else "no_model"
        if classifier is None:
            logger.warning(
                "No ML model found for observation %s — objects classified as 'unknown'; "
                "cross-match results are still stored",
                observation_uuid_hex,
            )

        # ---- Feature extraction ----
        feature_vectors: list[dict] = []
        extraction_failures = 0

        for obj in all_objects:
            # Merge AstronomicalObject column into sep_props so extract_feature_vector
            # can find detection_signal_to_noise_ratio in the same dict.
            sep_props = dict(obj.physical_properties or {})
            sep_props["detection_signal_to_noise_ratio"] = obj.detection_signal_to_noise_ratio

            try:
                if obj.segmentation_mask_rle is not None and obj.cutout_s3_prefix is not None:
                    cutout_data = _download_cutout(s3_client, obj.cutout_s3_prefix)
                    fv = extract_feature_vector(
                        cutout_data=cutout_data,
                        rle_mask=obj.segmentation_mask_rle,
                        sep_physical_properties=sep_props,
                    )
                else:
                    # SEP-only path — no mask available
                    fv = extract_feature_vector(
                        cutout_data=None,
                        rle_mask=None,
                        sep_physical_properties=sep_props,
                    )
            except Exception as exc:
                logger.warning(
                    "Feature extraction failed for object %s: %s",
                    obj.object_uuid,
                    exc,
                )
                fv = {"feature_source": "extraction_failed"}
                extraction_failures += 1

            feature_vectors.append(fv)

        # ---- ML classification ----
        if classifier is not None:
            feature_matrix = _build_feature_matrix(feature_vectors)
            predictions, confidence_scores, _ = predict_object_types(
                classifier, feature_matrix
            )
        else:
            predictions = np.array(["unknown"] * len(all_objects))
            confidence_scores = np.zeros(len(all_objects), dtype=float)

        # ---- Write ObjectClassification records (append-only) ----
        for i, obj in enumerate(all_objects):
            record = ObjectClassification(
                object_uuid=obj.object_uuid,
                predicted_object_type=str(predictions[i]),
                classification_confidence_score=float(confidence_scores[i]),
                ml_model_version=model_version,
                feature_extractor_version=_FEATURE_EXTRACTOR_VERSION,
                feature_vector=feature_vectors[i],
                is_anomaly_flagged=False,
            )
            database_session.add(record)

            if (i + 1) % 50 == 0:
                database_session.flush()

        database_session.flush()

        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = {
            "objects_classified": len(all_objects),
            "model_version": model_version,
            "feature_extraction_failures": extraction_failures,
        }
        database_session.commit()

        logger.info(
            "Classification complete for observation %s: %d objects, model=%s, failures=%d",
            observation_uuid_hex,
            len(all_objects),
            model_version,
            extraction_failures,
        )

        return {
            "observation_uuid": observation_uuid_hex,
            "objects_classified": len(all_objects),
            "model_version": model_version,
            "status": "completed",
        }

    except Exception:
        logger.exception(
            "classify_objects failed for observation %s", observation_uuid_hex
        )
        try:
            if processing_step:
                processing_step.step_status = StepStatus.failed
                processing_step.step_completed_at = sql_func.now()
                database_session.commit()
        except Exception:
            database_session.rollback()
        try:
            obs = (
                database_session.query(Observation)
                .filter(Observation.observation_uuid == observation_uuid)
                .first()
            )
            if obs:
                obs.pipeline_status = PipelineStatus.failed
                database_session.commit()
        except Exception:
            database_session.rollback()
        raise

    finally:
        database_session.close()
