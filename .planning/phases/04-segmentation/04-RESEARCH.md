# Phase 4: Segmentation - Research

**Researched:** 2026-02-23
**Domain:** Computer vision segmentation (SAM 3) + astronomical source detection (SEP/photutils)
**Confidence:** MEDIUM — SAM 3 is new (Nov 2025), CPU fallback situation is still fluid, and the model has never been systematically applied to JWST imagery at pipeline scale.

## Summary

Phase 4 builds a hybrid segmentation pipeline: traditional astronomical source detection via SEP produces a catalog of candidate positions (centroids, bounding boxes), which then serve as prompts for Meta's SAM 3 to generate pixel-level masks. The pipeline operates on the same FITS files already stored in MinIO from Phase 2, with results (masks in COCO RLE format, cutout PNGs, cutout FITS with WCS) stored in a new `segmentation` MinIO bucket and metadata written to the `astronomical_objects` PostgreSQL table.

The highest-risk element is SAM 3's hard CUDA requirement. The official facebookresearch/sam3 repo requires Python 3.12+, PyTorch 2.7+, and CUDA 12.6+. There is no official CPU or MPS (Apple Silicon) support. Community workarounds exist for MPS via `PYTORCH_ENABLE_MPS_FALLBACK=1` and a device-agnostic PR (#173), but these are unofficial. The fallback strategy must support degraded-mode operation (SEP-only segmentation without SAM) for environments without CUDA GPUs.

**Primary recommendation:** Implement SEP detection as the foundation layer that always runs. SAM 3 segmentation is an optional enhancement that activates when a CUDA GPU is available. The pipeline must produce valid results either way — SEP provides elliptical aperture masks as fallback when SAM is unavailable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Hybrid pipeline: SEP/photutils for traditional source detection + SAM 3 for pixel-level segmentation
- Both tools implemented in this phase — SEP finds where objects are, SAM 3 delineates what each object looks like
- Target SAM 3 specifically (Meta's latest, released Nov 2025) — leverage text-prompt segmentation capabilities for astronomical objects
- GPU preferred for SAM inference, but CPU fallback required — must work without CUDA
- Tiered detection with three confidence levels: High (definite source), Medium (likely real), Low (uncertain/borderline)
- No hard SNR cutoff — detect everything, assign to confidence tiers. Classification phase decides what's real
- All three tiers get full SAM segmentation (SAM on everything, not just high-confidence)
- Edge-of-image objects: detect and flag as 'partial/edge' in metadata, segment what's visible
- Multi-scale processing at three levels: full field, sub-regions, sub-sub-regions
- Hierarchical detection: detect large structures AND sub-structures within them (e.g., galaxy + spiral arms + core)
- Aggressive deblending in crowded fields — process at multiple zoom levels to separate overlapping sources
- Flat object list output — all objects at all scales stored without parent-child relationships (Phase 7 builds hierarchy)
- Keep all detections across scales, deduplicate later — Phase 5 or 7 handles deduplication with more context
- Detect-then-tag approach: pipeline detects artifacts (diffraction spikes, cosmic rays, hot pixels) like any other source
- No pre-filtering of artifacts before detection — everything goes through the full pipeline
- No artifact-specific metadata in Phase 4 — Phase 5 classification handles all artifact identification
- Bounding box crop with 10% padding on each side (not tight mask-only)
- Dual format: PNG for web display + FITS with WCS for science/export
- Segmentation masks stored as RLE encoding (COCO format) — compact, standard, needs decoding for display
- Dual stretch: store both raw linear and auto-stretched (asinh/histogram equalization) PNG versions
- Display auto-stretched version in UI, offer raw for download

### Claude's Discretion
- SAM 3 inference batch size and tiling strategy
- SEP/photutils detection parameter tuning (threshold, deblending parameters)
- Specific auto-stretch algorithm choice (asinh vs histogram equalization)
- RLE encoding implementation details
- Sub-region size and overlap for multi-scale processing
- Tile boundary merging strategy (IoU threshold, NMS parameters)
- Database schema additions for segmentation results
- MinIO storage path structure for cutouts and masks

### Deferred Ideas (OUT OF SCOPE)
- Parent-child object relationships (hierarchy) — Phase 7 Knowledge Graph
- Artifact classification and identification — Phase 5 Classification
- Object deduplication across scales — Phase 5 or Phase 7
- Adaptive scale levels (subdivide further only where density is high) — potential future optimization
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEG-01 | System segments every distinguishable object in tiled images using SAM | SAM 3 `Sam3Processor` with `predict_inst` for point/box prompts from SEP detections. Text prompts via `set_text_prompt` for concept sweeps ("galaxy", "star"). Automatic mask generation via grid prompts for comprehensive coverage. |
| SEG-02 | System merges segmentation masks across tile boundaries for objects that span multiple tiles | Multi-scale processing with overlapping sub-regions. IoU-based mask matching at boundaries with NMS deduplication. SEP detections near edges flagged as `partial/edge`. |
| SEG-03 | System produces per-object cutout images and pixel-level masks | `astropy.nddata.Cutout2D` for WCS-aware cutouts with 10% padding. Masks stored as COCO RLE via `pycocotools.mask.encode()`. Dual PNG (auto-stretched + raw) + FITS with WCS. |
| SEG-04 | System uses traditional source detection (SEP/photutils) as baseline and SAM prompt source | SEP `sep.extract()` produces centroids (x, y), bounding boxes (xmin/xmax/ymin/ymax), ellipse params (a, b, theta), and flux. These become point prompts and box prompts for SAM 3. Three confidence tiers from SNR. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sep | >=1.4.0 | Astronomical source detection, background estimation, deblending | Standard in astronomy, wraps SExtractor algorithms. NumPy-only dependency. Fast C backend. Returns structured arrays with centroids, ellipse params, flux. |
| sam3 | HEAD (facebookresearch/sam3) | Pixel-level segmentation with text and point prompts | Meta's latest (Nov 2025). 848M params. Text-prompt capability unique to SAM 3. Installed from GitHub, not PyPI. |
| torch | >=2.7.0 | SAM 3 dependency, GPU inference | Required by SAM 3. Must match CUDA version for GPU path. |
| torchvision | >=0.20.1 | SAM 3 dependency, image transforms | Required by SAM 3 for image preprocessing. |
| pycocotools | >=2.0.11 | COCO RLE mask encoding/decoding | De facto standard for binary mask serialization. C extension for speed. |
| astropy | >=7.0 (already installed) | Cutout2D, WCS, FITS I/O, visualization stretches | Already in project. Cutout2D preserves WCS. AsinhStretch and HistEqStretch for auto-stretch. |
| Pillow | >=10.0 (already installed) | PNG creation from numpy arrays | Already in project. |
| numpy | (already installed) | Array operations throughout | Already in project. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| photutils | >=2.3.0 | Extended source segmentation via `detect_sources`/`deblend_sources`, `SourceFinder` | For the multi-scale detection passes where SEP's SExtractor approach needs supplementing with watershed-based deblending. Also provides `SegmentationImage` for labeling. |
| scipy | (comes with numpy/astropy) | `scipy.ndimage` for morphological ops, `scipy.spatial` for spatial queries | Mask cleanup (binary_fill_holes, label), nearest-neighbor matching for boundary merging. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SAM 3 | SAM 2.1 (sam2 on PyPI) | SAM 2 has broader device support (CPU works) but lacks text-prompt capability. Could be fallback if SAM 3 GPU requirement is blocking. |
| SAM 3 | SAM 1 (segment-anything on PyPI) | Original SAM runs on CPU, has SamAutomaticMaskGenerator, 3 model sizes (ViT-B 91M, ViT-L 308M, ViT-H 636M). No text prompts. Best CPU fallback. |
| sep | photutils-only | photutils `SourceFinder` combines detect+deblend but is slower than SEP's C backend for initial detection. SEP better for the fast first pass. |
| pycocotools | rlemasklib | Fork with more mask operations, but pycocotools is more widely used and sufficient. |

**Installation:**
```bash
# Core astronomy (already installed)
pip install "sep>=1.4.0" "photutils>=2.3.0" "pycocotools>=2.0.11"

# SAM 3 (GPU path — requires CUDA 12.6+)
pip install torch==2.7.0 torchvision --index-url https://download.pytorch.org/whl/cu126
git clone https://github.com/facebookresearch/sam3.git
cd sam3 && pip install -e .

# SAM 3 model checkpoint (requires HuggingFace auth)
# huggingface-cli login
# Checkpoint auto-downloads on first use from facebook/sam3
```

## Architecture Patterns

### Recommended Project Structure
```
pipeline/
├── tasks/
│   ├── detect_sources.py     # SEP/photutils source detection Celery task
│   ├── segment_sam.py        # SAM 3 segmentation Celery task (optional GPU step)
│   └── generate_cutouts.py   # Cutout extraction and storage Celery task
shared/
├── models.py                 # + new columns on AstronomicalObject
├── config.py                 # + new settings (SAM model path, bucket name, thresholds)
└── s3.py                     # existing singleton, new bucket: segmentation
```

### Pattern 1: SEP Detection as Foundation

**What:** SEP runs on the full FITS image (chunked for large images) to produce a complete source catalog. This catalog is stored in the DB and serves as the prompt source for SAM. If SAM is unavailable, SEP's elliptical aperture masks are the final masks.

**When to use:** Always — this is the mandatory first step.

**Key decisions:**
- Detection threshold: `1.5 * bkg.globalrms` (standard astronomical threshold)
- Deblending: `deblend_nthresh=32, deblend_cont=0.005` (SExtractor defaults — well-validated)
- Minimum area: `minarea=5` (default — catches point sources while rejecting single-pixel noise)
- Background box size: `bw=64, bh=64` (good for JWST images with ~0.03"/pixel)

**Confidence tier assignment:**
```python
# After sep.extract(), assign tiers based on SNR
snr = objects['flux'] / flux_err  # flux_err from sep.sum_circle or sep.kron_radius photometry
confidence_tier = np.where(snr >= 10, 'high',
                  np.where(snr >= 3, 'medium', 'low'))
```

**Example:**
```python
import sep
import numpy as np

def detect_sources_in_fits(fits_data: np.ndarray) -> np.ndarray:
    """Run SEP source detection on a 2D FITS image array.

    Args:
        fits_data: 2D float32 array from FITS SCI extension.

    Returns:
        Structured numpy array with fields: x, y, a, b, theta, flux, etc.
    """
    # SEP requires native byte order
    data = fits_data.astype(np.float32, copy=False)
    if data.dtype.byteorder not in ('=', '<', '|'):
        data = data.byteswap().newbyteorder()

    # Background estimation
    bkg = sep.Background(data, bw=64, bh=64, fw=3, fh=3)
    data_sub = data - bkg.back()

    # Source extraction with deblending
    objects = sep.extract(
        data_sub,
        thresh=1.5,
        err=bkg.globalrms,
        minarea=5,
        deblend_nthresh=32,
        deblend_cont=0.005,
        segmentation_map=False,
    )

    return objects
```

### Pattern 2: Multi-Scale Detection

**What:** Three detection passes at increasing zoom. Each pass runs SEP independently, and all detections across scales are stored in a flat list.

**When to use:** For every observation. Required by locked decision.

**Scale levels:**
1. **Full field** — entire FITS image, detects large-scale structures (galaxies, nebulae, extended emission)
2. **Sub-regions** — image divided into overlapping tiles (512x512 or 1024x1024 with 20% overlap), detects medium structures
3. **Sub-sub-regions** — dense sub-regions further subdivided (256x256 with 20% overlap), detects faint compact sources in crowded fields

**Overlap rationale:** 20% overlap ensures objects near tile edges are fully captured in at least one tile. Objects appearing in the overlap zone of multiple tiles are detected multiple times — this is intentional (deduplication deferred to Phase 5/7 per locked decision).

### Pattern 3: SAM 3 as Enhancement Layer

**What:** SAM 3 takes SEP detections as prompts and produces pixel-level segmentation masks. It runs as a separate Celery task that can be skipped if no GPU is available.

**When to use:** When CUDA GPU is available. Graceful degradation when not.

**Prompt strategy:**
1. **Point prompts** from SEP centroids — `predict_inst(point_coords=[[x, y]], point_labels=[1])`
2. **Box prompts** from SEP bounding boxes — `predict_inst(box=[xmin, ymin, xmax, ymax])`
3. **Text prompts** for concept sweeps — `set_text_prompt(prompt="galaxy")` followed by `set_text_prompt(prompt="star")` (SAM 3's unique capability)
4. **Batch inference** — `predict_inst_batch()` for processing many prompts efficiently

**SAM 3 image preprocessing for FITS:**
SAM expects RGB uint8 images (H, W, 3). FITS science data must be:
1. Normalized to [0, 255] using ZScale + asinh stretch (reuse tile.py normalization)
2. Converted from single-channel grayscale to 3-channel RGB (replicate across channels)
3. Resized if exceeding SAM's 1024px limit (use the tiled approach for larger images)

**Example:**
```python
from sam3 import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor

def create_sam_processor():
    """Initialize SAM 3 model and processor. Returns None if CUDA unavailable."""
    import torch
    if not torch.cuda.is_available():
        logger.warning("No CUDA GPU — SAM 3 disabled, using SEP masks only")
        return None

    bpe_path = settings.sam3_bpe_path  # path to bpe_simple_vocab_16e6.txt.gz
    model = build_sam3_image_model(bpe_path=bpe_path, enable_inst_interactivity=True)
    return Sam3Processor(model)

def segment_with_sam(processor, image_rgb, sep_objects):
    """Generate SAM masks from SEP detections.

    Args:
        processor: Sam3Processor instance.
        image_rgb: uint8 RGB numpy array (H, W, 3).
        sep_objects: structured array from sep.extract().

    Returns:
        List of dicts with 'mask' (bool array), 'score' (float), 'box' (xyxy).
    """
    from PIL import Image
    pil_image = Image.fromarray(image_rgb)
    inference_state = processor.set_image(pil_image)

    # Batch point + box prompts from SEP detections
    point_coords = np.column_stack([sep_objects['x'], sep_objects['y']])
    point_labels = np.ones(len(sep_objects), dtype=np.int32)

    boxes = np.column_stack([
        sep_objects['xmin'], sep_objects['ymin'],
        sep_objects['xmax'], sep_objects['ymax'],
    ])

    masks_batch, scores_batch, _ = processor.model.predict_inst_batch(
        inference_state,
        point_coords_batch=point_coords[:, np.newaxis, :],
        labels_batch=point_labels[:, np.newaxis],
        box_batch=boxes,
        multimask_output=False,
    )

    return masks_batch, scores_batch
```

### Pattern 4: Celery Task Chain Extension

**What:** Extend the existing pipeline chain to include segmentation steps after tile generation.

**Current chain:** `download_fits -> validate_wcs -> generate_tiles`
**New chain:** `download_fits -> validate_wcs -> generate_tiles -> detect_sources -> segment_sam -> generate_cutouts`

**Important:** `generate_tiles` currently marks the observation as `completed`. This needs to change — `completed` should only be set by the last step in the chain (now `generate_cutouts`). The tile step should set an intermediate status or leave status as `processing`.

**Task data flow:**
```
generate_tiles output -> detect_sources input:
  {observation_uuid, fits_s3_keys, tile_count, dzi_s3_key, image_dimensions}

detect_sources output -> segment_sam input:
  {observation_uuid, fits_s3_keys, source_count, detection_ids[], scale_level}

segment_sam output -> generate_cutouts input:
  {observation_uuid, fits_s3_keys, object_uuids[], has_sam_masks: bool}
```

### Anti-Patterns to Avoid

- **Loading full FITS into memory for SAM:** FITS images can be gigapixels. Must tile/chunk for SAM just as tile.py does for DZI generation. SAM's 1024px input limit naturally enforces this.
- **Running SAM on every pixel via automatic mask generation:** Too slow for large astronomical images. Use SEP detections as targeted prompts instead of SAM's grid-based automatic mask generator.
- **Tight coupling between SEP and SAM:** SAM must be optional. The pipeline must produce valid (if lower quality) results with SEP alone.
- **Storing masks as full bitmap arrays in the database:** Binary masks for thousands of objects would bloat PostgreSQL. Use COCO RLE encoding and store in JSONB column or reference S3 path.
- **Normalizing FITS data per-tile for SAM:** Same as the tile.py lesson — normalization parameters must be computed once for the entire image and applied consistently. Per-tile normalization creates discontinuities.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background estimation | Custom median filter background | `sep.Background(data, bw=64, bh=64)` | SEP implements SExtractor's proven background mesh algorithm with bicubic spline interpolation. Edge cases (masked pixels, cosmic rays) are handled. |
| Source deblending | Threshold-based splitting | `sep.extract(deblend_nthresh=32, deblend_cont=0.005)` | Multi-threshold tree deblending with contrast ratio is SExtractor's core algorithm. Decades of validation in astronomy. |
| Binary mask RLE encoding | Custom run-length encoding | `pycocotools.mask.encode(np.asfortranarray(mask))` | COCO RLE is the standard. pycocotools C extension is fast. Compatible with all downstream tools. |
| Image cutouts with WCS | Manual array slicing + WCS recomputation | `astropy.nddata.Cutout2D(data, position, size, wcs=wcs)` | Cutout2D handles WCS transformation, partial overlap, and edge cases (mode='partial'). |
| Asinh stretch normalization | Custom asinh function | `astropy.visualization.AsinhStretch(a=0.1)` with `ZScaleInterval()` | Already used in tile.py. Consistent stretch across the project. |
| NMS for mask deduplication | Custom overlap checking | `torchvision.ops.nms()` or pycocotools IoU | NMS is a standard operation with optimized implementations. Don't reimplement IoU calculation. |

**Key insight:** Astronomical source detection is a solved problem with 30+ years of SExtractor heritage. SAM adds modern pixel-level precision but the detection foundation must use proven astronomical algorithms.

## Common Pitfalls

### Pitfall 1: SEP Byte Order Requirement
**What goes wrong:** `sep.extract()` raises `ValueError: Input array with dtype '>f4' has non-native byte order` on FITS data loaded with astropy.
**Why it happens:** FITS uses big-endian byte order. SEP's C backend requires native (little-endian on x86/ARM) byte order.
**How to avoid:** Always convert: `data = data.byteswap().newbyteorder()` or `data = np.array(data, dtype=np.float32)`.
**Warning signs:** ValueError mentioning byte order on first sep.extract() call.

### Pitfall 2: SAM 3 CUDA-Only Requirement
**What goes wrong:** Import fails or inference crashes on machines without NVIDIA GPU.
**Why it happens:** SAM 3 uses CUDA-only extensions: `torch_generic_nms`, Triton kernels. No CPU/MPS fallback in official code.
**How to avoid:** Wrap SAM import and initialization in try/except. Check `torch.cuda.is_available()` before attempting SAM. Design pipeline so SEP results are valid standalone.
**Warning signs:** ImportError for sam3 modules, RuntimeError about CUDA.

### Pitfall 3: Memory Exhaustion on Large Images
**What goes wrong:** Loading a 16k x 16k FITS image fully into memory for SEP detection exhausts RAM.
**Why it happens:** JWST images can be 4096x4096 to 16384x16384+ pixels. At float32, a 16k x 16k image is ~1GB. SEP's internal allocations can triple this.
**How to avoid:** For images above a size threshold (e.g., 4096x4096), use the multi-scale tiling approach — run SEP on sub-regions rather than the full image. This aligns with the locked decision for multi-scale processing.
**Warning signs:** MemoryError or OOM kill during sep.extract().

### Pitfall 4: FITS-to-SAM Image Preprocessing
**What goes wrong:** SAM produces garbage masks because the input image is not properly normalized.
**Why it happens:** SAM was trained on natural RGB images (uint8, 0-255). FITS science data is float32/float64 with arbitrary value ranges, often with NaN/inf values.
**How to avoid:** Apply ZScale + asinh stretch to [0, 255] uint8 (same as tile.py), replicate to 3 channels for RGB. Handle NaN/inf before normalization.
**Warning signs:** All SAM masks cover entire image or are empty.

### Pitfall 5: Fortran-Order Requirement for pycocotools
**What goes wrong:** RLE encoding produces incorrect masks.
**Why it happens:** `pycocotools.mask.encode()` expects Fortran-order (column-major) arrays. NumPy arrays are C-order (row-major) by default.
**How to avoid:** Always: `rle = mask_util.encode(np.asfortranarray(binary_mask[:, :, np.newaxis]))`.
**Warning signs:** Decoded masks appear transposed or garbled.

### Pitfall 6: Pipeline Status Regression
**What goes wrong:** Adding segmentation tasks after `generate_tiles` but `generate_tiles` already marks observation as `completed`.
**Why it happens:** Current tile.py sets `pipeline_status = PipelineStatus.completed` at the end. New downstream tasks run on an already-"completed" observation.
**How to avoid:** Modify tile.py to NOT set `completed` — let the final task in the chain (generate_cutouts) set the terminal status.
**Warning signs:** Observation shows `completed` before segmentation runs.

## Code Examples

### SEP Background Estimation + Source Extraction (Verified Pattern)
```python
# Source: SEP docs https://sep.readthedocs.io/en/stable/tutorial.html
import sep
import numpy as np
from astropy.io import fits

with fits.open(fits_path, memmap=True) as hdul:
    data = np.array(hdul['SCI'].data, dtype=np.float32)

# Fix byte order for SEP
data = data.byteswap().newbyteorder() if data.dtype.byteorder == '>' else data

# Background estimation
bkg = sep.Background(data, bw=64, bh=64, fw=3, fh=3)
data_sub = data - bkg.back()

# Extract sources
objects = sep.extract(data_sub, 1.5, err=bkg.globalrms, minarea=5,
                      deblend_nthresh=32, deblend_cont=0.005)

# Kron radius photometry for better flux estimates
kronrad, krflag = sep.kron_radius(data_sub, objects['x'], objects['y'],
                                   objects['a'], objects['b'], objects['theta'], 6.0)
flux, fluxerr, flag = sep.sum_ellipse(data_sub, objects['x'], objects['y'],
                                       objects['a'], objects['b'], objects['theta'],
                                       2.5 * kronrad, err=bkg.globalrms, subpix=1)
```

### COCO RLE Mask Encoding (Verified Pattern)
```python
# Source: pycocotools https://github.com/cocodataset/cocoapi
import pycocotools.mask as mask_util
import numpy as np

def encode_mask_to_rle(binary_mask: np.ndarray) -> dict:
    """Encode a binary mask to COCO RLE format.

    Args:
        binary_mask: 2D bool/uint8 array, shape (H, W).

    Returns:
        Dict with 'size' [H, W] and 'counts' (str).
    """
    # pycocotools requires Fortran-order uint8 array with extra dim
    fortran_mask = np.asfortranarray(binary_mask.astype(np.uint8))
    rle = mask_util.encode(fortran_mask[:, :, np.newaxis])[0]
    rle['counts'] = rle['counts'].decode('utf-8')  # bytes -> str for JSON
    return rle

def decode_rle_to_mask(rle: dict) -> np.ndarray:
    """Decode COCO RLE to binary mask."""
    if isinstance(rle['counts'], str):
        rle['counts'] = rle['counts'].encode('utf-8')
    return mask_util.decode(rle).squeeze()
```

### Cutout2D with WCS Preservation (Verified Pattern)
```python
# Source: Astropy docs https://docs.astropy.org/en/stable/nddata/utils.html
from astropy.nddata import Cutout2D
from astropy.wcs import WCS

def extract_cutout(data, wcs, center_x, center_y, bbox_width, bbox_height, padding_fraction=0.1):
    """Extract a cutout with padding and WCS preservation.

    Args:
        data: 2D FITS image array.
        wcs: astropy WCS object.
        center_x, center_y: Object centroid in pixel coords.
        bbox_width, bbox_height: Bounding box size in pixels.
        padding_fraction: Fractional padding (0.1 = 10% each side).

    Returns:
        Cutout2D object with .data and .wcs attributes.
    """
    padded_width = int(bbox_width * (1 + 2 * padding_fraction))
    padded_height = int(bbox_height * (1 + 2 * padding_fraction))

    # Cutout2D position is (x, y), size is (ny, nx)
    cutout = Cutout2D(
        data,
        position=(center_x, center_y),
        size=(padded_height, padded_width),
        wcs=wcs,
        mode='partial',  # handles edge objects gracefully
        fill_value=0.0,
    )
    return cutout
```

### SAM 3 Graceful Initialization (Recommended Pattern)
```python
import logging

logger = logging.getLogger(__name__)

_sam_processor = None
_sam_available = None

def get_sam_processor():
    """Lazily initialize SAM 3. Returns None if CUDA unavailable."""
    global _sam_processor, _sam_available

    if _sam_available is False:
        return None

    if _sam_processor is not None:
        return _sam_processor

    try:
        import torch
        if not torch.cuda.is_available():
            logger.warning("CUDA not available — SAM 3 segmentation disabled")
            _sam_available = False
            return None

        from sam3 import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor

        bpe_path = settings.sam3_bpe_path
        model = build_sam3_image_model(bpe_path=bpe_path, enable_inst_interactivity=True)
        _sam_processor = Sam3Processor(model)
        _sam_available = True
        logger.info("SAM 3 initialized on %s", torch.cuda.get_device_name(0))
        return _sam_processor

    except Exception as e:
        logger.warning("SAM 3 initialization failed: %s — using SEP masks only", e)
        _sam_available = False
        return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SExtractor command-line | SEP Python library (same algorithms) | 2016 | Same algorithms, direct NumPy integration, no temp files |
| SAM 1 (point/box prompts only) | SAM 3 (text + point + box + exemplar prompts) | Nov 2025 | Text prompts enable concept-based sweeps without geometric prompts |
| Manual mask creation | SAM automatic segmentation | 2023 | Zero-shot segmentation from any prompt type |
| Custom RLE implementations | pycocotools standard RLE | 2017+ | Universal format, fast C backend, ecosystem compatibility |
| photutils-only detection | SEP + photutils hybrid | Ongoing | SEP faster for initial detection, photutils better for extended source deblending |

**Deprecated/outdated:**
- SAM 1 (`segment-anything` on PyPI): Superseded by SAM 3, but remains the best CPU-compatible option. Still valid as fallback.
- SAM 2 (`sam2` on PyPI): Superseded by SAM 3 for image segmentation. Video capabilities not relevant here.

## Open Questions

1. **SAM 3 checkpoint access**
   - What we know: Requires HuggingFace account approval before downloading. Model is ~3.4 GB (848M params).
   - What's unclear: How long approval takes. Whether checkpoints can be cached in MinIO or must be on local filesystem.
   - Recommendation: Apply for access immediately. Store checkpoint at a configurable local path. Add to `.env` configuration.

2. **SAM 3 performance on astronomical images**
   - What we know: SAM applied to Euclid/HST galaxy images achieved ~3% size agreement. SAM was trained on natural images, not astronomical data.
   - What's unclear: How well SAM 3 handles: diffuse nebular emission, overlapping sources in crowded fields, diffraction spike artifacts, faint low-SNR sources.
   - Recommendation: Treat SAM quality as MEDIUM confidence until validated on actual JWST test observations. This is the highest technical risk noted in STATE.md.

3. **Multi-scale sub-region sizing**
   - What we know: Full field -> sub-regions -> sub-sub-regions. Need overlap to catch boundary objects.
   - What's unclear: Optimal sub-region sizes for JWST images. 512x512 vs 1024x1024 for middle scale.
   - Recommendation: Start with 1024x1024 sub-regions with 20% overlap (204px overlap band). Sub-sub-regions 256x256 with 20% overlap. Make sizes configurable via Settings. Tune based on test observation results.

4. **Database schema for segmentation metadata**
   - What we know: `AstronomicalObject` table exists with basic fields (coords, classification, properties JSONB).
   - What's unclear: Whether to add dedicated columns for segmentation data or use `physical_properties` JSONB.
   - Recommendation: Add dedicated columns for frequently-queried fields: `segmentation_mask_rle` (JSONB), `cutout_s3_prefix` (String), `bounding_box_pixels` (JSONB), `detection_snr` (Float), `detection_confidence_tier` (Enum), `detection_scale_level` (String), `is_edge_detection` (Boolean). Use Alembic migration.

5. **SAM 3 fallback strategy details**
   - What we know: Must work without CUDA. SEP provides ellipse parameters.
   - What's unclear: Whether to use SAM 1 (CPU-compatible, no text prompts) as intermediate fallback, or go straight to SEP-only elliptical masks.
   - Recommendation: Two-tier fallback: (1) SAM 3 with CUDA, (2) SEP elliptical aperture masks without SAM. Skip SAM 1 intermediate — adds complexity for marginal benefit. The elliptical apertures from SEP (a, b, theta parameters) produce reasonable masks for most astronomical sources.

## Sources

### Primary (HIGH confidence)
- SEP documentation v1.4.1: https://sep.readthedocs.io/en/stable/ — tutorial, API reference for `sep.extract()`, background estimation
- photutils documentation v2.3.0: https://photutils.readthedocs.io/en/stable/ — `detect_sources`, `deblend_sources`, `SegmentationImage`
- Astropy Cutout2D v7.2.0: https://docs.astropy.org/en/stable/api/astropy.nddata.Cutout2D.html — WCS-preserving cutouts
- Astropy visualization v7.2.0: https://docs.astropy.org/en/stable/visualization/index.html — AsinhStretch, HistEqStretch, ZScaleInterval
- pycocotools (PyPI v2.0.11): https://pypi.org/project/pycocotools/ — COCO RLE mask encoding/decoding
- facebookresearch/sam3 README: https://github.com/facebookresearch/sam3 — installation, API, model architecture (848M params)

### Secondary (MEDIUM confidence)
- SAM 3 GitHub Issue #164 (CPU/MPS support): https://github.com/facebookresearch/sam3/issues/164 — confirmed CUDA-only, community workarounds via PR #173
- SAM 3 GitHub Issue #219 (smaller models): https://github.com/facebookresearch/sam3/issues/219 — no smaller variants available
- SAM 3 for SAM 1 tasks notebook: https://github.com/facebookresearch/sam3/blob/main/examples/sam3_for_sam1_task_example.ipynb — `predict_inst`, `predict_inst_batch` API
- Automated galaxy sizes with SAM (A&A 2025): https://www.aanda.org/articles/aa/full_html/2025/01/aa52482-24/aa52482-24.html — SAM on Euclid/HST galaxies, ~3% size agreement
- segment-geospatial SAM 3 tiled segmentation: https://samgeo.gishub.org/examples/sam3_tiled_segmentation/ — tiling approach for large images

### Tertiary (LOW confidence)
- SAM 3 HuggingFace (facebook/sam3): https://huggingface.co/facebook/sam3 — checkpoint access, model card (needs validation of specific API calls)
- SAM 3 text prompt examples from Roboflow/Codecademy: Code examples in web search results showing `set_text_prompt()` API — needs verification against actual sam3 source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — SEP, pycocotools, astropy Cutout2D are mature, well-documented libraries with stable APIs
- Architecture: MEDIUM — Multi-scale detection pattern is sound but optimal parameters need tuning per observation. SAM integration pattern based on API docs and example notebooks.
- Pitfalls: HIGH — Byte order, RLE Fortran order, CUDA requirement, memory management are well-documented gotchas
- SAM 3 specifics: LOW-MEDIUM — API based on README + notebooks, but SAM 3 is new and API may evolve. Text prompt effectiveness on astronomical images is unknown.

**Research date:** 2026-02-23
**Valid until:** 2026-03-09 (14 days — SAM 3 ecosystem is fast-moving, check for CPU support updates)
