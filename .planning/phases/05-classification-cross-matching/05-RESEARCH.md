# Phase 5: Classification & Cross-Matching - Research

**Researched:** 2026-02-23
**Domain:** Astronomical catalog cross-matching, ML classification, anomaly detection
**Confidence:** HIGH (standard libraries, well-documented APIs, established algorithms)

## Summary

Phase 5 transforms raw segmented objects (AstronomicalObject records from Phase 4 with RA/Dec, bounding boxes, SEP ellipse params, cutout images, and segmentation masks) into classified, cross-matched, and anomaly-scored objects. The work divides into four technical domains: (1) catalog cross-matching against SIMBAD, NED, SDSS, and Gaia using astroquery (already a project dependency), (2) morphological feature extraction using statmorph on cutout images and segmentation masks, (3) ML classification using scikit-learn Random Forest on feature vectors, and (4) anomaly detection using scikit-learn Isolation Forest.

All four catalogs are queryable through astroquery, which is already installed (>=0.4.11). The critical architectural decision is batch querying: SIMBAD supports vectorized coordinate queries and TAP/ADQL for bulk operations; NED requires per-object queries with rate-limit-aware throttling; SDSS supports vectorized query_region; and Gaia supports TAP with async jobs. The ML classifier should use scikit-learn's RandomForestClassifier trained on feature vectors computed by statmorph (concentration, asymmetry, smoothness, Gini, M20, Sersic index, ellipticity) augmented with SEP photometric features already stored in physical_properties. Isolation Forest provides the anomaly scoring mandated by INTEL-01.

**Primary recommendation:** Use astroquery's vectorized/TAP interfaces for each catalog, add statmorph for feature extraction, scikit-learn for classification + anomaly detection, and extend the existing Celery chain with three new tasks: `cross_match_catalogs`, `classify_objects`, and `detect_anomalies`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Adaptive search radius based on object angular extent from segmentation -- compact sources ~2-3 arcsec, extended sources scale up proportionally
- Keep ALL matches from ALL catalogs -- every match stored with distance and confidence score
- Query SIMBAD, NED, SDSS, and Gaia in parallel (no priority order, no early exit)
- On catalog API failure: retry 3x with backoff, then mark that catalog as "not queried" for affected objects -- pipeline continues with remaining catalogs; reprocessable later
- Detailed subtypes (spiral galaxy, elliptical galaxy, planetary nebula, emission nebula, main sequence star, white dwarf, etc.) -- not just broad categories
- Use existing labeled astronomical datasets for training (researcher to investigate Galaxy Zoo, SDSS spectroscopic classifications, and other available labeled data)
- ML classifier runs on EVERY object, whether catalog-matched or not -- enables disagreement detection and validates catalog matches
- Catalog classification is authoritative, but ML prediction is always stored alongside for comparison
- Persist full feature vectors (ellipticity, concentration, asymmetry, etc.) per object -- powers anomaly detection (INTEL-01) and future analysis
- Cast a wide net for anomalies -- better to review 100 candidates and find 5 real anomalies than miss one
- Any single signal triggers a flag: feature vector outlier OR catalog disagreement OR no catalog match OR unusual morphology OR low ML confidence
- Every anomaly flag includes a human-readable explanation
- Artifacts (diffraction spikes, cosmic rays, imaging artifacts) classified as "artifact" type by ML -- NOT flagged as anomalies
- Core fields indexed as database columns (name, type, coordinates, magnitude, redshift) for fast querying
- Full catalog response stored as raw JSON blob alongside indexed fields
- Basic API endpoints in this phase: get object classifications, get cross-matches by object ID, list anomalies
- Full provenance tracking: classification timestamp, ML model version, feature extractor version, catalog query date
- Reclassification supported via append: new classification runs create new records alongside old ones, preserving full classification history per object

### Claude's Discretion
- Exact ML model architecture and training approach
- Feature vector engineering details
- Database schema design for classification/match tables
- API endpoint structure and response formats
- Anomaly score computation method
- Catalog query optimization and rate limiting strategy

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLASS-01 | System cross-matches segmented object coordinates against SIMBAD catalog | astroquery.simbad with query_region (vectorized) and query_tap (ADQL) |
| CLASS-02 | System cross-matches segmented object coordinates against NED catalog | astroquery.ipac.ned with query_region (per-object, throttled) |
| CLASS-03 | System cross-matches segmented object coordinates against SDSS catalog | astroquery.sdss with query_region (vectorized, 3 arcmin max radius) |
| CLASS-04 | System cross-matches segmented object coordinates against Gaia catalog | astroquery.gaia with cone_search_async and TAP queries |
| CLASS-05 | System classifies objects not found in any catalog using ML classifier | scikit-learn RandomForestClassifier on statmorph + SEP feature vectors; runs on ALL objects per user decision |
| CLASS-06 | System flags truly novel/unknown objects for human review with anomaly confidence scores | scikit-learn IsolationForest on feature vectors; multi-signal flagging per user decision |
| INTEL-01 | System automatically flags objects that don't match known categories using anomaly detection (Isolation Forests on feature vectors) | IsolationForest from scikit-learn; feature vectors from statmorph CAS/Gini/M20 + SEP photometry |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| astroquery | >=0.4.11 (installed) | Query SIMBAD, NED, SDSS, Gaia catalogs | Official astropy-affiliated; unified interface to all four catalogs |
| scikit-learn | >=1.4.0 | RandomForestClassifier + IsolationForest | Industry standard ML; no GPU required; proven on astronomical data |
| statmorph | >=0.7.1 | Non-parametric morphological diagnostics (CAS, Gini-M20, MID, Sersic) | Standard tool for galaxy morphology; used in hundreds of astronomical papers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| joblib | >=1.3.0 (scikit-learn dep) | Model serialization (save/load trained classifier) | Persisting trained RF/IF models to S3 |
| astropy.coordinates | (installed) | SkyCoord creation for catalog queries | Every cross-match query |
| astropy.units | (installed) | Angular separation units (arcsec, arcmin, deg) | Search radius specification |
| photutils | >=2.3.0 (installed) | Segmentation map utilities for statmorph input | Converting COCO RLE masks to labeled segmentation maps |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| scikit-learn RF | XGBoost/LightGBM | Better accuracy on tabular data, but adds dependency; RF sufficient for ~10-20 features |
| statmorph | Custom feature extraction | statmorph is battle-tested, computes 30+ morphological features; hand-rolling would miss edge cases |
| IsolationForest | Local Outlier Factor (LOF) | LOF is density-based, slower on high-dimensional data; IF explicitly mentioned in requirements (INTEL-01) |
| Per-object NED queries | pyVO TAP-based batch | NED's TAP service is less mature than SIMBAD/Gaia; astroquery.ipac.ned is the standard interface |

**Installation:**
```bash
uv pip install scikit-learn statmorph
```

## Architecture Patterns

### Recommended Project Structure
```
pipeline/tasks/
├── cross_match_catalogs.py   # Celery task: query all 4 catalogs per observation
├── classify_objects.py       # Celery task: feature extraction + RF classification
├── detect_anomalies.py       # Celery task: IsolationForest scoring + flag setting
├── ingest.py                 # MODIFIED: add 3 new tasks to chain
└── ... (existing tasks)

pipeline/
├── catalog_clients/
│   ├── __init__.py
│   ├── simbad_client.py      # SIMBAD query logic (vectorized + TAP)
│   ├── ned_client.py         # NED query logic (per-object, throttled)
│   ├── sdss_client.py        # SDSS query logic (vectorized)
│   └── gaia_client.py        # Gaia query logic (cone_search + TAP)
├── feature_extraction.py     # statmorph feature vector computation
└── ml_models/
    ├── __init__.py
    └── classifier.py         # RF training, prediction, model I/O

shared/models.py              # MODIFIED: add ObjectClassification table + enums
api/routers/
├── objects.py                # NEW: classification, cross-match, anomaly endpoints
└── ... (existing routers)
```

### Pattern 1: Parallel Catalog Querying with Graceful Degradation
**What:** Query all four catalogs concurrently using Python's `concurrent.futures.ThreadPoolExecutor`, with per-catalog retry (3x backoff) and independent failure handling.
**When to use:** The cross_match_catalogs Celery task.
**Example:**
```python
# Source: User decision in CONTEXT.md + astroquery patterns
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def cross_match_single_catalog(catalog_client, coordinates, search_radius):
    """Query one catalog with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return catalog_client.query_region(coordinates, radius=search_radius)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            return {"status": "not_queried", "error": str(e)}

def cross_match_all_catalogs(ra_deg, dec_deg, search_radius_arcsec):
    """Query SIMBAD, NED, SDSS, Gaia in parallel."""
    coord = SkyCoord(ra=ra_deg, dec=dec_deg, unit='deg', frame='icrs')
    radius = search_radius_arcsec * u.arcsec

    catalog_clients = {
        "simbad": simbad_client,
        "ned": ned_client,
        "sdss": sdss_client,
        "gaia": gaia_client,
    }

    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(cross_match_single_catalog, client, coord, radius): name
            for name, client in catalog_clients.items()
        }
        for future in as_completed(futures):
            catalog_name = futures[future]
            results[catalog_name] = future.result()

    return results
```

### Pattern 2: Adaptive Search Radius
**What:** Compute search radius from object angular extent (bounding box + WCS pixel scale), with floor of 2 arcsec for compact sources and proportional scaling for extended.
**When to use:** Before every cross-match query.
**Example:**
```python
# Source: User decision in CONTEXT.md
import numpy as np

COMPACT_SOURCE_RADIUS_ARCSEC = 2.0
EXTENDED_SOURCE_SCALE_FACTOR = 1.5  # multiply angular extent by this

def compute_search_radius_arcsec(
    bounding_box_pixels: dict,
    pixel_scale_arcsec_per_pixel: float,
) -> float:
    """Adaptive radius: compact ~2-3 arcsec, extended scales up."""
    bbox_width = bounding_box_pixels["xmax"] - bounding_box_pixels["xmin"]
    bbox_height = bounding_box_pixels["ymax"] - bounding_box_pixels["ymin"]
    angular_extent_arcsec = max(bbox_width, bbox_height) * pixel_scale_arcsec_per_pixel

    if angular_extent_arcsec < 5.0:  # compact source
        return max(COMPACT_SOURCE_RADIUS_ARCSEC, angular_extent_arcsec)
    else:  # extended source
        return angular_extent_arcsec * EXTENDED_SOURCE_SCALE_FACTOR
```

### Pattern 3: Append-Only Classification History
**What:** New classification runs create new `ObjectClassification` records, never overwrite old ones. Query latest via `ORDER BY classified_at DESC LIMIT 1`.
**When to use:** All classification and anomaly detection writes.
**Example:**
```python
# Source: User decision in CONTEXT.md (reclassification via append)
class ObjectClassification(Base):
    __tablename__ = "object_classifications"

    classification_uuid = Column(UUID, primary_key=True, default=uuid.uuid4)
    object_uuid = Column(UUID, ForeignKey("astronomical_objects.object_uuid"), nullable=False)

    # ML classification
    predicted_object_type = Column(String, nullable=False)
    classification_confidence_score = Column(Float, nullable=False)
    ml_model_version = Column(String, nullable=False)
    feature_extractor_version = Column(String, nullable=False)

    # Feature vector (full persistence per user decision)
    feature_vector = Column(JSONB, nullable=False)

    # Anomaly detection
    is_anomaly_flagged = Column(Boolean, default=False, nullable=False)
    anomaly_score = Column(Float, nullable=True)
    anomaly_explanation = Column(Text, nullable=True)

    # Provenance
    classified_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
```

### Pattern 4: Vectorized SIMBAD Queries via TAP/ADQL
**What:** Instead of per-object query_region loops, upload a batch of coordinates and query via ADQL CONTAINS for high-throughput matching.
**When to use:** When processing observations with 100+ objects.
**Example:**
```python
# Source: astroquery SIMBAD TAP docs
from astroquery.simbad import Simbad

def batch_simbad_query(coordinates_list, radius_arcsec_list):
    """Query SIMBAD for multiple objects in a single TAP request."""
    # Build ADQL with UNION of coordinate circles
    # For very large batches, chunk into groups of ~100
    conditions = []
    for i, (coord, radius) in enumerate(zip(coordinates_list, radius_arcsec_list)):
        radius_deg = radius / 3600.0
        conditions.append(
            f"CONTAINS(POINT('ICRS', ra, dec), "
            f"CIRCLE('ICRS', {coord.ra.deg}, {coord.dec.deg}, {radius_deg})) = 1"
        )

    # For small batches, use vectorized query_region
    if len(coordinates_list) <= 20:
        result = Simbad.query_region(
            coordinates_list,
            radius=[r * u.arcsec for r in radius_arcsec_list],
        )
        return result

    # For large batches, use TAP with chunking
    # (SIMBAD TAP handles complex ADQL well)
    ...
```

### Anti-Patterns to Avoid
- **Per-object serial catalog queries:** Query catalogs in parallel (ThreadPoolExecutor), and use vectorized/TAP interfaces where available. Never loop over 1000 objects with individual HTTP requests.
- **Training on cutout pixels directly:** Use computed feature vectors (statmorph + SEP), not raw pixel data. RF on pixel data is inferior to RF on morphological features for this classification task.
- **Overwriting classification records:** Always append new classification records. The user explicitly requires full classification history.
- **Hard-failing on catalog API errors:** The user decision is clear: retry 3x then mark "not_queried" and continue. Never let a single catalog failure block the pipeline.
- **Treating SDSS as unlimited:** SDSS query_region has a strict 3 arcmin radius limit imposed by their servers. Extended sources with larger search radii need special handling (use SDSS SQL query or skip if radius exceeds 3 arcmin).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Morphological feature extraction | Custom CAS computation | statmorph.source_morphology() | Handles edge cases (degenerate Sersic fits, asymmetry centering), computes 30+ features, peer-reviewed |
| Catalog coordinate matching | Custom HTTP to SIMBAD/NED APIs | astroquery (already installed) | Handles VOTable parsing, pagination, timeouts, retries, coordinate frame conversion |
| Anomaly scoring | Custom outlier distance computation | sklearn.ensemble.IsolationForest | Efficient on high-dimensional data, well-tuned contamination thresholds, standard in astronomy |
| Model persistence | pickle/json serialization | joblib.dump/load | Handles numpy arrays, sparse matrices, scikit-learn version compatibility |
| RLE mask to segmentation map | Custom bit unpacking | pycocotools.mask.decode() | Already used in Phase 4; convert COCO RLE back to binary mask for statmorph input |
| Coordinate frame conversion | Manual RA/Dec arithmetic | astropy.coordinates.SkyCoord | Handles precession, frame transforms, angular separation computation |

**Key insight:** The astronomy Python ecosystem has mature, tested solutions for every component of this phase. Custom implementations would introduce subtle bugs in coordinate handling, morphological statistics, and catalog protocol compliance.

## Common Pitfalls

### Pitfall 1: SIMBAD Rate Limiting / Blacklisting
**What goes wrong:** Querying SIMBAD >5-10 times per second causes temporary IP blacklist (up to 1 hour).
**Why it happens:** Looping over objects with individual query_region calls.
**How to avoid:** (1) Use vectorized query_region with coordinate lists, (2) Use TAP/ADQL for bulk queries, (3) Add explicit rate limiting (max 5 queries/sec) for any per-object fallback queries.
**Warning signs:** HTTP 503 or timeout errors from SIMBAD after initial queries succeed.

### Pitfall 2: NED Has No Batch Query Interface
**What goes wrong:** Unlike SIMBAD and Gaia, NED's astroquery interface does NOT support vectorized coordinate queries. Each object requires a separate HTTP request.
**Why it happens:** NED's API architecture is older and does not support TAP.
**How to avoid:** (1) Explicit rate limiting (2-3 queries/sec), (2) Process NED queries sequentially with sleep intervals, (3) Run NED in its own thread while other catalogs process in parallel.
**Warning signs:** NED returning 429 or connection reset errors.

### Pitfall 3: SDSS 3 Arcmin Radius Limit
**What goes wrong:** SDSS query_region raises an error if radius > 3 arcmin.
**Why it happens:** Server-side hard limit.
**How to avoid:** Cap SDSS search radius at 3 arcmin. For extended objects that need larger radii, either (1) query at 3 arcmin and accept partial matches, or (2) use SDSS SQL query interface (query_sql) for custom cone searches.
**Warning signs:** ValueError or server error when radius exceeds 180 arcsec.

### Pitfall 4: statmorph Requires Segmentation Map, Not RLE
**What goes wrong:** Passing COCO RLE directly to statmorph fails. It needs integer-labeled 2D segmentation maps.
**Why it happens:** statmorph expects photutils-style segmentation maps where each source has a unique integer label.
**How to avoid:** Decode COCO RLE to binary mask (pycocotools.mask.decode), then create a labeled segmap (mask * object_label_int). statmorph.source_morphology expects the segmap to have the source labeled with its integer ID.
**Warning signs:** statmorph returning all NaN values or raising shape mismatch errors.

### Pitfall 5: Feature Vector NaN/Inf from Failed Morphological Fits
**What goes wrong:** statmorph returns NaN for concentration, Sersic index, etc. when fits fail (small objects, noisy data, edge objects). Passing NaN feature vectors to RF/IF crashes or produces garbage.
**Why it happens:** Many astronomical objects are too small, too faint, or too irregular for reliable morphological fitting.
**How to avoid:** (1) Check statmorph's `flag` attribute (0=good, 1=suspect, 2=bad, 4=catastrophic), (2) Impute NaN features with median values from the observation, (3) Fall back to SEP-only features when statmorph fails entirely.
**Warning signs:** statmorph.flag >= 2 for most objects; RF predictions all mapping to a single class.

### Pitfall 6: Training Data Mismatch with JWST Imagery
**What goes wrong:** Galaxy Zoo / SDSS training data is optical (g/r/i bands), while JWST data is primarily infrared (NIRCam F150W, F200W, etc.). Feature distributions differ significantly.
**Why it happens:** No large labeled JWST morphological dataset exists yet.
**How to avoid:** (1) Train on feature vectors (not pixels) -- morphological features are more wavelength-invariant than raw pixel values, (2) Use SDSS spectroscopic CLASS/SUBCLASS labels as ground truth for cross-matched objects (self-supervised bootstrapping), (3) Keep the classifier simple (RF) so it can be retrained quickly as more JWST objects accumulate labeled data.
**Warning signs:** Classifier confidence scores clustering near 50% (coin flip); all objects classified as a single type.

### Pitfall 7: Anomaly Detection Overwhelm
**What goes wrong:** With "cast a wide net" philosophy, nearly every object gets flagged as anomalous, making the anomaly list useless.
**Why it happens:** Multiple independent triggers (no catalog match, low ML confidence, feature outlier) each flag independently. On new fields with few catalog matches, almost everything triggers.
**How to avoid:** (1) Compute a composite anomaly score that weights signals, (2) Exclude artifact-classified objects from anomaly flagging, (3) Make the anomaly threshold tunable and start conservative, (4) Store the raw anomaly score (continuous) separately from the binary flag.
**Warning signs:** >50% of objects flagged as anomalies.

## Code Examples

### Cross-Matching with SIMBAD (Vectorized)
```python
# Source: https://astroquery.readthedocs.io/en/latest/simbad/simbad.html
from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord
import astropy.units as u

simbad = Simbad()
simbad.add_votable_fields("otype", "flux(V)", "rvz_redshift", "rvz_type")

# Vectorized: pass list of SkyCoord, get single result table
coords = SkyCoord(
    ra=[148.888, 150.123, 152.456],
    dec=[69.065, 70.123, 68.789],
    unit=(u.deg, u.deg),
    frame='icrs',
)
result = simbad.query_region(
    coords,
    radius=[3 * u.arcsec, 5 * u.arcsec, 2 * u.arcsec],
)
# result is an astropy Table with columns: MAIN_ID, RA, DEC, OTYPE, etc.
```

### Cross-Matching with NED (Per-Object, Throttled)
```python
# Source: https://astroquery.readthedocs.io/en/latest/ipac/ned/ned.html
from astroquery.ipac.ned import Ned
import time

def query_ned_throttled(coord, radius_arcsec, max_retries=3):
    """Query NED with rate limiting and retry."""
    radius = radius_arcsec * u.arcsec
    for attempt in range(max_retries):
        try:
            result = Ned.query_region(coord, radius=radius)
            time.sleep(0.5)  # Rate limit: ~2 queries/sec
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None  # Mark as "not_queried"
```

### Cross-Matching with SDSS
```python
# Source: https://astroquery.readthedocs.io/en/latest/sdss/sdss.html
from astroquery.sdss import SDSS

# Vectorized query with spectral matching
result = SDSS.query_region(
    coords,  # List of SkyCoord
    radius=3 * u.arcsec,  # Max 3 arcmin!
    spectro=True,
    photoobj_fields=['objid', 'ra', 'dec', 'type', 'petroMag_r',
                     'petroMag_g', 'petroMag_i'],
    specobj_fields=['class', 'subclass', 'z', 'zErr'],
)
```

### Cross-Matching with Gaia DR3
```python
# Source: https://astroquery.readthedocs.io/en/latest/gaia/gaia.html
from astroquery.gaia import Gaia

Gaia.MAIN_GAIA_TABLE = "gaiadr3.gaia_source"
Gaia.ROW_LIMIT = 50

job = Gaia.cone_search_async(coord, radius=search_radius)
result = job.get_results()
# Columns: source_id, ra, dec, parallax, phot_g_mean_mag, bp_rp, etc.
```

### Feature Extraction with statmorph
```python
# Source: https://statmorph.readthedocs.io/en/stable/notebooks/tutorial.html
import statmorph
import numpy as np
from pycocotools import mask as mask_util

def extract_features(cutout_data, rle_mask, gain=1e5):
    """Extract morphological features from cutout + mask."""
    # Decode COCO RLE to binary mask
    rle_copy = dict(rle_mask)
    if isinstance(rle_copy["counts"], str):
        rle_copy["counts"] = rle_copy["counts"].encode("utf-8")
    binary_mask = mask_util.decode(rle_copy).squeeze()

    # Create labeled segmap (statmorph expects integer labels)
    segmap = np.zeros_like(cutout_data, dtype=int)
    segmap[binary_mask > 0] = 1  # Label source as 1

    # Run statmorph
    source_morphs = statmorph.source_morphology(
        cutout_data, segmap, gain=gain
    )

    if len(source_morphs) == 0:
        return None

    morph = source_morphs[0]

    return {
        "concentration": morph.concentration,
        "asymmetry": morph.asymmetry,
        "smoothness": morph.smoothness,
        "gini": morph.gini,
        "m20": morph.m20,
        "sersic_n": morph.sersic_n,
        "sersic_rhalf": morph.sersic_rhalf,
        "ellipticity": morph.ellipticity,
        "flag": morph.flag,
        "flag_sersic": morph.flag_sersic,
    }
```

### ML Classification with RandomForest
```python
# Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html
from sklearn.ensemble import RandomForestClassifier
import joblib
import numpy as np

# Feature columns used for classification
FEATURE_COLUMNS = [
    "concentration", "asymmetry", "smoothness",
    "gini", "m20", "sersic_n", "ellipticity",
    "sep_flux", "detection_signal_to_noise_ratio",
]

# Training (done once, model persisted to S3)
clf = RandomForestClassifier(
    n_estimators=200,
    max_depth=20,
    min_samples_leaf=5,
    class_weight="balanced",  # Handle imbalanced classes
    random_state=42,
    n_jobs=-1,
)
clf.fit(X_train, y_train)  # X: feature matrix, y: type labels
joblib.dump(clf, "classifier_v1.joblib")

# Prediction (per observation run)
clf = joblib.load("classifier_v1.joblib")
predictions = clf.predict(X_new)
probabilities = clf.predict_proba(X_new)
confidence = probabilities.max(axis=1)
```

### Anomaly Detection with IsolationForest
```python
# Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html
from sklearn.ensemble import IsolationForest

# Fit on all objects (unsupervised -- no labels needed)
iso_forest = IsolationForest(
    n_estimators=200,
    contamination=0.1,  # Expect ~10% anomalies (wide net)
    max_samples='auto',
    random_state=42,
    n_jobs=-1,
)
iso_forest.fit(X_features)

# Score all objects
anomaly_scores = iso_forest.score_samples(X_features)
# Lower score = more anomalous
# decision_function returns negative for anomalies
anomaly_predictions = iso_forest.predict(X_features)  # 1=normal, -1=anomaly
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SIMBAD scripted queries | SIMBAD TAP/ADQL via astroquery 0.4.7+ | 2024 | Bulk queries possible; vectorized coordinate input |
| Manual CAS computation | statmorph 0.7.x | 2022+ | Standard 30+ feature extraction; Sersic fitting included |
| Galaxy Zoo 1 labels (binary) | Galaxy Zoo 2+ detailed morphology | 2013+ | Detailed subtype labels (spiral arms, bars, bulge prominence) |
| Gaia DR2 | Gaia DR3 (default in astroquery) | 2022 | More sources, better photometry, astrophysical parameters |
| Custom anomaly scoring | scikit-learn IsolationForest | Stable | No labeled data needed; works on high-dimensional feature vectors |

**Deprecated/outdated:**
- SIMBAD script interface: Replaced by TAP. Use `Simbad.query_tap()` for complex queries, not `Simbad.query_criteria()`.
- `Simbad.query_criteria()`: Still works but TAP is more flexible and performant for batch operations.
- Galaxy Zoo 1 data: Only spiral/elliptical/merger. Use Galaxy Zoo 2 (GZ2) or Galaxy Zoo DECaLS for detailed subtypes.

## Catalog API Details

### SIMBAD
- **Interface:** `astroquery.simbad.Simbad`
- **Batch support:** YES -- vectorized `query_region(list_of_coords, radius=list_of_radii)`
- **TAP support:** YES -- `query_tap(adql_string)`
- **Rate limit:** ~5-10 queries/sec before blacklist (1 hour ban)
- **Key fields:** MAIN_ID, RA, DEC, OTYPE (object type), rvz_redshift, flux(V), parallax
- **Object types:** 230+ SIMBAD types (Star, HII, GlC, G, QSO, Neb, etc.)
- **Confidence:** HIGH (verified with official docs)

### NED
- **Interface:** `astroquery.ipac.ned.Ned`
- **Batch support:** NO -- per-object queries only
- **Rate limit:** Undocumented; recommend 2-3 queries/sec
- **Key fields:** Object Name, RA, DEC, Type, Velocity, Redshift
- **Object types:** G (Galaxy), GPair, GGroup, GClstr, QSO, PofG, RadioS, etc.
- **Confidence:** MEDIUM (rate limit is estimated, not documented)

### SDSS
- **Interface:** `astroquery.sdss.SDSS`
- **Batch support:** YES -- vectorized `query_region(list_of_coords)`
- **Radius limit:** HARD 3 arcmin maximum (server-enforced)
- **Key fields:** objid, ra, dec, type (3=galaxy, 6=star), class, subclass, z, petroMag_*
- **Spectroscopic types:** STAR (O/B/A/F/G/K/M/L/T/Carbon/WD/CV), GALAXY (STARFORMING/AGN), QSO
- **Confidence:** HIGH (verified radius limit with official docs)

### Gaia DR3
- **Interface:** `astroquery.gaia.Gaia`
- **Batch support:** YES -- TAP async queries
- **Default table:** `gaiadr3.gaia_source` (1.8 billion sources)
- **Key fields:** source_id, ra, dec, parallax, phot_g_mean_mag, bp_rp, proper motions
- **Object focus:** Primarily stars (not galaxies/nebulae)
- **Confidence:** HIGH (verified with official docs)

## Training Data Sources

### SDSS Spectroscopic Labels (Recommended Primary)
- **Source:** SDSS DR17/DR18 specObj table
- **Labels:** CLASS (STAR/GALAXY/QSO) + SUBCLASS (30+ detailed types)
- **Size:** ~5 million spectra with classifications
- **Access:** `astroquery.sdss.SDSS.query_region(spectro=True)` returns class/subclass for matched objects
- **Advantage:** Self-supervised bootstrapping -- objects that cross-match with SDSS automatically get training labels
- **Confidence:** HIGH

### Galaxy Zoo 2 Morphologies (Recommended Secondary)
- **Source:** galaxy-datasets Python package or data.galaxyzoo.org
- **Labels:** Detailed morphology votes (spiral/elliptical/merger + arm count, bar, bulge prominence, etc.)
- **Size:** ~300,000 galaxies with volunteer classifications
- **Access:** `from galaxy_datasets import gz2; catalog, label_cols = gz2(root=..., train=True, download=True)`
- **Advantage:** Rich morphological subtypes; ideal for training galaxy subtype classifier
- **Confidence:** HIGH

### Galaxy10 DECaLS (Alternative)
- **Source:** astroNN package
- **Labels:** 10 morphological classes (~441k galaxies)
- **Advantage:** Pre-curated, balanced classes, easy to load
- **Confidence:** MEDIUM (less detailed subtypes than GZ2)

## Database Schema Recommendations

### New Table: `object_classifications`
Stores append-only classification records with full provenance per user decision.

| Column | Type | Purpose |
|--------|------|---------|
| classification_uuid | UUID PK | Unique classification record |
| object_uuid | UUID FK -> astronomical_objects | Which object |
| predicted_object_type | String | ML predicted type (detailed subtype) |
| classification_confidence_score | Float | RF max probability |
| ml_model_version | String | e.g., "rf_v1.0" |
| feature_extractor_version | String | e.g., "statmorph_0.7.1+sep" |
| feature_vector | JSONB | Full feature dict {concentration: ..., asymmetry: ..., ...} |
| is_anomaly_flagged | Boolean | Whether this object is flagged |
| anomaly_score | Float | IsolationForest raw score |
| anomaly_explanation | Text | Human-readable explanation of why flagged |
| classified_at | Timestamp | When this classification was created |

### Existing Table Modifications: `astronomical_objects`
Add indexed columns for fast querying per user decision:

| Column | Type | Purpose |
|--------|------|---------|
| classified_object_type | String (EXISTS) | Best current type (from catalog or ML) |
| classification_source_catalog | String (EXISTS) | Which catalog provided the type |
| classification_confidence_score | Float (EXISTS) | Score from best source |
| is_anomaly_flagged | Boolean (EXISTS) | Already exists from Phase 1 schema |
| catalog_object_name | String (NEW) | Primary name from catalogs (e.g., "NGC 1234") |
| catalog_magnitude | Float (NEW) | V-band or G-band magnitude from catalogs |
| catalog_redshift | Float (NEW) | Redshift from catalogs (SIMBAD/NED/SDSS) |

### Existing Table: `catalog_cross_matches`
Already defined in Phase 1 schema. Fields align with user decisions:

| Column | Existing | Notes |
|--------|----------|-------|
| match_uuid | YES | PK |
| object_uuid | YES | FK to astronomical_objects |
| catalog_name | YES | "simbad", "ned", "sdss", "gaia" |
| catalog_source_id | YES | Catalog-specific ID |
| angular_separation_arcseconds | YES | Distance from object center |
| match_probability_score | YES | Confidence of match |
| raw_catalog_response | YES (JSONB) | Full raw response per user decision |

This table already perfectly matches the user's requirements. No schema changes needed for cross-match storage.

## Celery Chain Integration

The existing pipeline chain is:
```
download_fits -> validate_wcs -> generate_tiles -> detect_sources -> segment_sam -> generate_cutouts
```

Phase 5 adds three tasks after generate_cutouts:
```
... -> generate_cutouts -> cross_match_catalogs -> classify_objects -> detect_anomalies
```

- `cross_match_catalogs`: Queries all 4 catalogs, writes CatalogCrossMatch records, updates AstronomicalObject indexed fields
- `classify_objects`: Extracts statmorph features, runs RF classifier, writes ObjectClassification records
- `detect_anomalies`: Runs IsolationForest, checks multi-signal triggers, sets anomaly flags and explanations

The `generate_cutouts` task currently sets `PipelineStatus.completed`. This must be changed: `generate_cutouts` should NOT set completed; `detect_anomalies` (the new final task) sets `PipelineStatus.completed`.

## Open Questions

1. **Pre-trained model bootstrapping**
   - What we know: SDSS cross-matched objects will provide labels; Galaxy Zoo provides galaxy morphology labels
   - What's unclear: For the very first observation processed (no training data yet), how should the classifier behave?
   - Recommendation: Ship a pre-trained model trained on Galaxy Zoo + SDSS labels (offline step). If no model file exists at runtime, skip ML classification and only do catalog cross-matching. The classifier can be trained/retrained as labeled data accumulates.

2. **WCS pixel scale availability**
   - What we know: Phase 2/3 extract WCS from FITS headers; pixel scale is needed for adaptive search radius computation
   - What's unclear: Is pixel scale directly available in the AstronomicalObject record or does it need re-extraction from FITS?
   - Recommendation: Compute pixel scale from the WCS header in the cross_match_catalogs task (same FITS-download-and-open pattern as detect_sources). Store pixel scale in the ProcessingStep metadata so it's available without re-downloading.

3. **Object count and query volume**
   - What we know: Test observation 0a870e98 had 273 detections (320x320 image). Real JWST images are much larger (4000x4000+).
   - What's unclear: How many objects per observation in production (could be 10,000+)?
   - Recommendation: Design for 10,000+ objects per observation. Batch SIMBAD/SDSS/Gaia queries. NED will be the bottleneck (~2 queries/sec = ~80 min for 10,000 objects). Consider chunking NED queries and storing partial results.

## Sources

### Primary (HIGH confidence)
- [astroquery SIMBAD docs](https://astroquery.readthedocs.io/en/latest/simbad/simbad.html) - query_region, query_tap, vectorized queries, rate limits
- [astroquery NED docs](https://astroquery.readthedocs.io/en/latest/ipac/ned/ned.html) - query_region, returned fields
- [astroquery SDSS docs](https://astroquery.readthedocs.io/en/latest/sdss/sdss.html) - query_region, 3 arcmin limit, photoobj/specobj fields
- [astroquery Gaia docs](https://astroquery.readthedocs.io/en/latest/gaia/gaia.html) - cone_search_async, TAP, gaiadr3.gaia_source
- [scikit-learn IsolationForest docs](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html) - parameters, score_samples, predict
- [scikit-learn RandomForestClassifier docs](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html) - class_weight, predict_proba
- [statmorph docs](https://statmorph.readthedocs.io/en/stable/overview.html) - CAS, Gini-M20, Sersic, source_morphology API

### Secondary (MEDIUM confidence)
- [Galaxy Zoo data portal](https://data.galaxyzoo.org/) - GZ2 morphology labels
- [galaxy-datasets PyPI](https://pypi.org/project/galaxy-datasets/) - ML-friendly Galaxy Zoo data loader
- [SDSS spectroscopic catalogs](https://www.sdss4.org/dr17/spectro/catalogs/) - CLASS/SUBCLASS label definitions
- [CDS SIMBAD TAP announcement](https://cds.unistra.fr/news/2024/04/05-access-simbad-tap-from-astroquery/) - TAP in astroquery 0.4.7+

### Tertiary (LOW confidence)
- NED rate limiting estimates (~2-3 queries/sec) - based on community experience, not official documentation
- Galaxy Zoo / SDSS feature transferability to JWST infrared data - plausible but untested at scale

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries are well-established, actively maintained, and already partially installed
- Architecture: HIGH - follows existing Celery chain pattern; catalog APIs well-documented
- Pitfalls: HIGH - rate limits, SDSS radius cap, and statmorph input requirements are documented facts
- Training data: MEDIUM - SDSS labels are certain; Galaxy Zoo availability is certain; transferability to JWST feature space is theoretical

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable domain; catalog APIs change slowly)
