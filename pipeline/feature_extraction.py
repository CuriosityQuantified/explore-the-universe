"""Morphological feature extraction for astronomical objects.

Path A (statmorph): cutout_data + rle_mask both provided → full CAS/Gini/M20 features.
Path B (SEP fallback): rle_mask is None or statmorph flag >= 2 → photometric features only.

NaN/Inf values are replaced with the -999.0 sentinel so the RF classifier
can impute them at prediction time.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_SENTINEL = -999.0
_STATMORPH_FLAG_OK_THRESHOLD = 2  # flag < 2 → acceptable statmorph result


def extract_feature_vector(
    cutout_data: Optional[np.ndarray],
    rle_mask: Optional[dict],
    sep_physical_properties: Optional[dict] = None,
    gain: float = 1e5,
) -> dict:
    """Compute a feature vector for one astronomical object.

    Returns a dict of named floats plus 'feature_source': 'statmorph'|'sep_fallback'.
    All NaN/Inf values are replaced with -999.0.
    """
    sep_props = sep_physical_properties or {}

    if cutout_data is not None and rle_mask is not None:
        try:
            features = _run_statmorph(cutout_data, rle_mask, gain)
            if features is not None:
                _augment_with_sep(features, sep_props)
                return _sanitize(features)
        except Exception as exc:
            logger.warning("statmorph failed, falling back to SEP-only: %s", exc)

    return _sanitize(_sep_fallback(sep_props))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_statmorph(
    cutout_data: np.ndarray, rle_mask: dict, gain: float
) -> Optional[dict]:
    """Run statmorph on cutout+mask. Returns feature dict or None on failure."""
    try:
        import statmorph
    except ImportError:
        logger.warning("statmorph not installed; using SEP fallback")
        return None

    try:
        from pycocotools import mask as mask_util
    except ImportError:
        logger.warning("pycocotools not installed; cannot decode RLE mask")
        return None

    rle_copy = dict(rle_mask)
    if isinstance(rle_copy.get("counts"), str):
        rle_copy["counts"] = rle_copy["counts"].encode("utf-8")

    binary_mask = mask_util.decode(rle_copy)
    if binary_mask.ndim == 3:
        binary_mask = binary_mask[:, :, 0]

    segmap = np.zeros(cutout_data.shape[:2], dtype=int)
    segmap[binary_mask > 0] = 1

    morphs = statmorph.source_morphology(cutout_data, segmap, gain=gain)
    if not morphs:
        return None

    morph = morphs[0]
    if morph.flag >= _STATMORPH_FLAG_OK_THRESHOLD:
        logger.debug("statmorph flag=%d; falling back to SEP", morph.flag)
        return None

    return {
        "concentration": _safe_float(morph.concentration),
        "asymmetry": _safe_float(morph.asymmetry),
        "smoothness": _safe_float(morph.smoothness),
        "gini": _safe_float(morph.gini),
        "m20": _safe_float(morph.m20),
        "sersic_n": _safe_float(morph.sersic_n),
        "sersic_rhalf": _safe_float(morph.sersic_rhalf),
        "ellipticity": _safe_float(morph.ellipticity),
        "statmorph_flag": int(morph.flag),
        "statmorph_flag_sersic": int(morph.flag_sersic),
        "feature_source": "statmorph",
    }


def _sep_fallback(sep_props: dict) -> dict:
    """Build a SEP-only feature dict (statmorph fields set to sentinel)."""
    sep_a = _safe_float(sep_props.get("sep_a"))
    sep_b = _safe_float(sep_props.get("sep_b"))
    ellipticity = (
        1.0 - (sep_b / sep_a)
        if sep_a > 0 and sep_b != _SENTINEL
        else _SENTINEL
    )
    features = {
        "concentration": _SENTINEL,
        "asymmetry": _SENTINEL,
        "smoothness": _SENTINEL,
        "gini": _SENTINEL,
        "m20": _SENTINEL,
        "sersic_n": _SENTINEL,
        "sersic_rhalf": _SENTINEL,
        "ellipticity": ellipticity,
        "statmorph_flag": _SENTINEL,
        "statmorph_flag_sersic": _SENTINEL,
        "feature_source": "sep_fallback",
    }
    _augment_with_sep(features, sep_props)
    return features


def _augment_with_sep(features: dict, sep_props: dict) -> None:
    """Merge SEP photometric properties into features (in-place)."""
    features["sep_flux"] = _safe_float(sep_props.get("sep_flux"))
    features["sep_a"] = _safe_float(sep_props.get("sep_a"))
    features["sep_b"] = _safe_float(sep_props.get("sep_b"))
    features["detection_signal_to_noise_ratio"] = _safe_float(
        sep_props.get("detection_signal_to_noise_ratio")
    )


def _safe_float(val) -> float:
    if val is None:
        return _SENTINEL
    try:
        f = float(val)
        return _SENTINEL if (np.isnan(f) or np.isinf(f)) else f
    except (TypeError, ValueError):
        return _SENTINEL


def _sanitize(features: dict) -> dict:
    """Replace any remaining NaN/Inf with sentinel; leave strings untouched."""
    result = {}
    for k, v in features.items():
        if isinstance(v, str):
            result[k] = v
        elif isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            result[k] = _SENTINEL
        else:
            result[k] = v
    return result
