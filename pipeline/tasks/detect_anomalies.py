"""Anomaly detection Celery task: IsolationForest scoring + multi-signal flagging.

Ninth (final) step in the 9-task pipeline chain.  Owns PipelineStatus.completed.
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import func as sql_func

from api.db.session import SessionLocal
from pipeline.celery_app import celery_app
from pipeline.ml_models.classifier import FEATURE_COLUMNS
from shared.config import settings
from shared.models import (
    AstronomicalObject,
    CatalogCrossMatch,
    ObjectClassification,
    Observation,
    PipelineStatus,
    ProcessingStep,
    StepStatus,
)
from shared.s3 import get_s3_client

logger = logging.getLogger(__name__)

_SENTINEL = -999.0


def _build_feature_matrix(feature_vectors: list[dict]) -> np.ndarray:
    """Build a 2-D float array from a list of feature-vector dicts.

    Missing or sentinel values are kept as-is; callers impute before use.
    """
    rows = []
    for fv in feature_vectors:
        row = [float(fv.get(col, _SENTINEL) or _SENTINEL) for col in FEATURE_COLUMNS]
        rows.append(row)
    return np.array(rows, dtype=float)


def _impute_sentinels(matrix: np.ndarray) -> np.ndarray:
    """Replace -999.0 sentinel and NaN values with column medians in-place copy."""
    imputed = matrix.copy()
    for col_idx in range(imputed.shape[1]):
        col = imputed[:, col_idx]
        valid = col[(col != _SENTINEL) & ~np.isnan(col)]
        median = float(np.nanmedian(valid)) if len(valid) > 0 else 0.0
        mask = (col == _SENTINEL) | np.isnan(col)
        imputed[mask, col_idx] = median
    return imputed


def _save_model_to_s3(iso_forest: IsolationForest, s3_client) -> None:
    """Serialize IsolationForest to a tempfile and upload to S3."""
    fd, temp_path = tempfile.mkstemp(suffix=".joblib")
    os.close(fd)
    try:
        joblib.dump(iso_forest, temp_path)
        s3_client.upload_file(
            temp_path,
            settings.s3_bucket_models,
            settings.classification_anomaly_model_s3_key,
        )
        logger.info(
            "Saved anomaly model to s3://%s/%s",
            settings.s3_bucket_models,
            settings.classification_anomaly_model_s3_key,
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@celery_app.task(bind=True, acks_late=True)
def detect_anomalies(self, classification_result: dict) -> dict:
    """Score objects for anomalies and flag novel detections.

    Ninth (final) step in the 9-task pipeline chain.
    Receives the output dict from classify_objects.
    Sets PipelineStatus.completed on the observation upon success.
    """
    observation_uuid_hex = classification_result["observation_uuid"]
    observation_uuid = uuid.UUID(observation_uuid_hex)

    database_session = SessionLocal()
    processing_step: Optional[ProcessingStep] = None

    try:
        processing_step = ProcessingStep(
            observation_uuid=observation_uuid,
            step_name="detect_anomalies",
            step_status=StepStatus.running,
            step_started_at=sql_func.now(),
        )
        database_session.add(processing_step)
        database_session.commit()
        database_session.refresh(processing_step)

        logger.info(
            "Starting anomaly detection for observation %s", observation_uuid_hex
        )

        # --- 1. Load latest ObjectClassification per object ---
        # Subquery: most recent classified_at per object_uuid for this observation
        all_objects = (
            database_session.query(AstronomicalObject)
            .filter(AstronomicalObject.source_observation_uuid == observation_uuid)
            .all()
        )

        if not all_objects:
            _finalize_empty(
                database_session, processing_step, observation_uuid, observation_uuid_hex
            )
            return {
                "observation_uuid": observation_uuid_hex,
                "objects_scored": 0,
                "anomalies_flagged": 0,
                "status": "completed",
            }

        object_uuids = [obj.object_uuid for obj in all_objects]

        # Latest classification per object
        latest_classifications: dict[uuid.UUID, ObjectClassification] = {}
        all_classifications = (
            database_session.query(ObjectClassification)
            .filter(ObjectClassification.object_uuid.in_(object_uuids))
            .order_by(ObjectClassification.classified_at.desc())
            .all()
        )
        for clf_record in all_classifications:
            if clf_record.object_uuid not in latest_classifications:
                latest_classifications[clf_record.object_uuid] = clf_record

        # Cross-match counts per object (for Signal 3)
        cross_match_counts: dict[uuid.UUID, int] = {oid: 0 for oid in object_uuids}
        all_cross_matches = (
            database_session.query(
                CatalogCrossMatch.object_uuid, sql_func.count(CatalogCrossMatch.match_uuid)
            )
            .filter(CatalogCrossMatch.object_uuid.in_(object_uuids))
            .group_by(CatalogCrossMatch.object_uuid)
            .all()
        )
        for row in all_cross_matches:
            cross_match_counts[row[0]] = row[1]

        # --- 2. Build feature matrix ---
        objects_with_clf = [
            obj for obj in all_objects if obj.object_uuid in latest_classifications
        ]
        if not objects_with_clf:
            _finalize_empty(
                database_session, processing_step, observation_uuid, observation_uuid_hex
            )
            return {
                "observation_uuid": observation_uuid_hex,
                "objects_scored": 0,
                "anomalies_flagged": 0,
                "status": "completed",
            }

        feature_vectors = [
            latest_classifications[obj.object_uuid].feature_vector
            for obj in objects_with_clf
        ]
        feature_matrix = _build_feature_matrix(feature_vectors)
        imputed_matrix = _impute_sentinels(feature_matrix)

        # --- 3. IsolationForest (only when >= 10 objects) ---
        n_objects = len(objects_with_clf)
        isolation_forest_fit = False
        anomaly_scores = np.zeros(n_objects, dtype=float)
        anomaly_predictions = np.ones(n_objects, dtype=int)  # 1=normal default

        if n_objects >= 10:
            try:
                s3_client = get_s3_client()
                iso_forest = IsolationForest(
                    n_estimators=200,
                    contamination=settings.classification_anomaly_contamination,
                    random_state=42,
                    n_jobs=-1,
                )
                iso_forest.fit(imputed_matrix)
                anomaly_scores = iso_forest.score_samples(imputed_matrix)
                anomaly_predictions = iso_forest.predict(imputed_matrix)
                isolation_forest_fit = True
                _save_model_to_s3(iso_forest, s3_client)
            except Exception as exc:
                logger.warning(
                    "IsolationForest failed for observation %s: %s — skipping IF signal",
                    observation_uuid_hex,
                    exc,
                )
        else:
            logger.warning(
                "Observation %s has only %d objects (< 10) — skipping IsolationForest",
                observation_uuid_hex,
                n_objects,
            )

        # --- 4. Multi-signal flagging ---
        signal_counts = {
            "feature_outlier": 0,
            "catalog_disagreement": 0,
            "no_catalog_match": 0,
            "unusual_morphology": 0,
            "low_confidence": 0,
        }
        anomalies_flagged = 0

        for i, obj in enumerate(objects_with_clf):
            clf_record = latest_classifications[obj.object_uuid]
            triggered_signals: list[str] = []

            # Signal 1 — IsolationForest outlier (-1 = anomaly)
            if isolation_forest_fit and anomaly_predictions[i] == -1:
                triggered_signals.append(
                    f"Feature vector outlier (IsolationForest score: {anomaly_scores[i]:.3f})"
                )
                signal_counts["feature_outlier"] += 1

            # Signal 2 — ML↔catalog type disagreement
            ml_type = clf_record.predicted_object_type or ""
            catalog_type = obj.classified_object_type or ""
            if (
                ml_type
                and catalog_type
                and ml_type not in ("unknown", "artifact")
                and catalog_type not in ("unknown",)
                and ml_type != catalog_type
            ):
                triggered_signals.append(
                    f"ML type '{ml_type}' disagrees with catalog type '{catalog_type}'"
                )
                signal_counts["catalog_disagreement"] += 1

            # Signal 3 — Zero CatalogCrossMatch records
            if cross_match_counts.get(obj.object_uuid, 0) == 0:
                triggered_signals.append("No catalog match within search radius")
                signal_counts["no_catalog_match"] += 1

            # Signal 4 — Unusual morphology (statmorph flag >= 2)
            fv = clf_record.feature_vector or {}
            statmorph_flag = fv.get("flag", 0) or 0
            if statmorph_flag >= 2:
                triggered_signals.append(
                    f"Unusual morphology (statmorph flag={statmorph_flag})"
                )
                signal_counts["unusual_morphology"] += 1

            # Signal 5 — Low ML confidence
            confidence = clf_record.classification_confidence_score or 0.0
            if confidence < 0.3:
                triggered_signals.append(
                    f"ML confidence below threshold ({confidence:.2f})"
                )
                signal_counts["low_confidence"] += 1

            # Flag: any signal fired AND predicted type is NOT "artifact"
            is_anomaly = bool(triggered_signals) and ml_type != "artifact"

            clf_record.is_anomaly_flagged = is_anomaly
            clf_record.anomaly_score = float(anomaly_scores[i])
            clf_record.anomaly_explanation = (
                "; ".join(triggered_signals) if triggered_signals else None
            )
            obj.is_anomaly_flagged = is_anomaly

            if is_anomaly:
                anomalies_flagged += 1

            if (i + 1) % 50 == 0:
                database_session.flush()

        database_session.flush()

        # --- 5. Pipeline finalization ---
        observation = (
            database_session.query(Observation)
            .filter(Observation.observation_uuid == observation_uuid)
            .first()
        )
        if observation:
            observation.pipeline_status = PipelineStatus.completed

        processing_step.step_status = StepStatus.completed
        processing_step.step_completed_at = sql_func.now()
        processing_step.step_output_metadata = {
            "objects_scored": n_objects,
            "anomalies_flagged": anomalies_flagged,
            "isolation_forest_fit": isolation_forest_fit,
            "signals_distribution": signal_counts,
        }
        database_session.commit()

        logger.info(
            "Anomaly detection complete for observation %s: %d scored, %d flagged",
            observation_uuid_hex,
            n_objects,
            anomalies_flagged,
        )

        return {
            "observation_uuid": observation_uuid_hex,
            "objects_scored": n_objects,
            "anomalies_flagged": anomalies_flagged,
            "status": "completed",
        }

    except Exception:
        logger.exception(
            "detect_anomalies failed for observation %s", observation_uuid_hex
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


def _finalize_empty(
    database_session,
    processing_step: ProcessingStep,
    observation_uuid: uuid.UUID,
    observation_uuid_hex: str,
) -> None:
    """Mark step and observation completed when there are no objects to score."""
    observation = (
        database_session.query(Observation)
        .filter(Observation.observation_uuid == observation_uuid)
        .first()
    )
    if observation:
        observation.pipeline_status = PipelineStatus.completed
    processing_step.step_status = StepStatus.completed
    processing_step.step_completed_at = sql_func.now()
    processing_step.step_output_metadata = {
        "objects_scored": 0,
        "anomalies_flagged": 0,
        "isolation_forest_fit": False,
        "signals_distribution": {},
    }
    database_session.commit()
    logger.info("No objects to score for observation %s", observation_uuid_hex)
