"""Random Forest classifier for astronomical object morphological type prediction.

Exports:
    FEATURE_COLUMNS   — ordered list of feature names used for training/prediction
    OBJECT_TYPE_LABELS — full label vocabulary (must include at minimum those
                         required by the acceptance criteria)
    load_or_create_classifier — load pre-trained model from S3 or return None
    predict_object_types      — batch prediction with sentinel imputation
    save_classifier           — serialize and upload model to S3
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)

FEATURE_COLUMNS: list[str] = [
    "concentration",
    "asymmetry",
    "smoothness",
    "gini",
    "m20",
    "sersic_n",
    "ellipticity",
    "sep_flux",
    "detection_signal_to_noise_ratio",
    "sep_a",
]

OBJECT_TYPE_LABELS: list[str] = [
    "star",
    "white_dwarf",
    "binary_star",
    "spiral_galaxy",
    "elliptical_galaxy",
    "irregular_galaxy",
    "lenticular_galaxy",
    "planetary_nebula",
    "emission_nebula",
    "reflection_nebula",
    "globular_cluster",
    "open_cluster",
    "quasar",
    "active_galactic_nucleus",
    "artifact",
    "unknown",
]

_SENTINEL = -999.0


def load_or_create_classifier(
    s3_client,
    model_s3_key: str,
    bucket: str,
) -> Optional[RandomForestClassifier]:
    """Download and deserialize the pre-trained RF classifier from S3.

    Returns None if the model does not exist in S3 — the caller must then
    classify all objects as 'unknown' with confidence 0.0.
    """
    fd, temp_path = tempfile.mkstemp(suffix=".joblib")
    os.close(fd)
    try:
        s3_client.download_file(bucket, model_s3_key, temp_path)
        classifier = joblib.load(temp_path)
        logger.info("Loaded ML classifier from s3://%s/%s", bucket, model_s3_key)
        return classifier
    except Exception as exc:
        logger.warning(
            "No ML model found at s3://%s/%s (%s) — classifying all objects as 'unknown'",
            bucket,
            model_s3_key,
            exc,
        )
        return None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def predict_object_types(
    classifier: RandomForestClassifier,
    feature_matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Predict morphological types for a batch of objects.

    Sentinel values (-999.0) are imputed with column medians before prediction.

    Returns:
        predictions      — string label per object
        confidence_scores — max class probability per object
        probabilities    — full probability matrix (n_objects × n_classes)
    """
    imputed = feature_matrix.copy().astype(float)
    for col_idx in range(imputed.shape[1]):
        col = imputed[:, col_idx]
        valid = col[col != _SENTINEL]
        median = float(np.nanmedian(valid)) if len(valid) > 0 else 0.0
        imputed[col == _SENTINEL, col_idx] = median

    predictions = classifier.predict(imputed)
    probabilities = classifier.predict_proba(imputed)
    confidence_scores = probabilities.max(axis=1)
    return predictions, confidence_scores, probabilities


def save_classifier(
    classifier: RandomForestClassifier,
    s3_client,
    model_s3_key: str,
    bucket: str,
) -> None:
    """Serialize and upload a trained classifier to S3."""
    fd, temp_path = tempfile.mkstemp(suffix=".joblib")
    os.close(fd)
    try:
        joblib.dump(classifier, temp_path)
        s3_client.upload_file(temp_path, bucket, model_s3_key)
        logger.info("Saved ML classifier to s3://%s/%s", bucket, model_s3_key)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
