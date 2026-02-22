# Phase 2: Data Ingestion & Tiling - Research

**Researched:** 2026-02-21
**Domain:** Astronomical data ingestion (MAST/JWST), FITS processing, WCS extraction, image tiling
**Confidence:** HIGH (core stack verified via official docs, patterns verified via multiple sources)

## Summary

Phase 2 transforms JWST observation IDs into validated, tiled imagery stored in MinIO. The pipeline is: query MAST by observation/program ID, download calibrated FITS files, extract and validate WCS coordinates, store provenance metadata in PostgreSQL, then tile images into multi-resolution DZI pyramids for web viewing and SAM processing.

The standard Python astronomy stack (astropy + astroquery) handles FITS I/O, WCS, and MAST access. For tiling, libvips/pyvips is the correct tool -- it generates DZI tile pyramids from large images using streaming (constant memory), which directly solves the trillion-pixel requirement. DZI tiles served from MinIO pair with OpenSeadragon (Phase 3) for the web viewer. The critical bridge between FITS data (32-bit float, arbitrary dynamic range) and tile generation (8-bit RGB/JPEG) is astropy's visualization normalization (ZScale/asinh stretch), which must produce perceptually useful images before tiling.

**Primary recommendation:** Use astroquery.mast for MAST access, astropy for FITS/WCS, pyvips.dzsave() for DZI tile generation, and astropy.visualization for FITS-to-RGB normalization. Process FITS data in chunks via memmap + numpy slicing, convert chunks to normalized 8-bit images, then feed to pyvips for streaming tile pyramid generation.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INGEST-01 | User can trigger ingestion of JWST observations from MAST by observation ID or program ID | astroquery.mast.Observations.query_criteria() supports obs_collection='JWST', proposal_id, obs_id queries. MastMissions class provides JWST-specific metadata access. Download via get_product_list + filter_products + download_products. |
| INGEST-02 | System extracts and validates WCS coordinates from FITS headers for accurate sky positioning | astropy.wcs.WCS(header) extracts WCS from FITS headers. Validation via round-trip pixel-to-world-to-pixel with tolerance check. wcslint CLI tool validates WCS keywords. CRVAL1/CRVAL2 provide pointing RA/Dec. |
| INGEST-03 | System tiles ingested images into multi-resolution pyramids for web viewing and SAM processing | pyvips.Image.dzsave() generates DZI tile pyramids (quadtree structure, configurable tile size). Tile size of 256px for web viewing; separate 1024px tiles for SAM processing. OpenSeadragon consumes DZI in Phase 3. |
| INGEST-04 | System stores data provenance metadata (telescope, instrument, filter, exposure time, observation ID, program ID) | JWST FITS headers contain TELESCOP, INSTRUME, FILTER, EXPTIME keywords. astroquery MAST queries return proposal_id, obs_id, instrument_name, filters. Store in existing Observation model fields. |
| INGEST-05 | System handles trillion-pixel FITS images via tile-based processing without memory exhaustion | astropy memmap=True avoids loading full image. Process in row-band chunks (e.g., 4096 rows at a time). pyvips uses streaming pipeline (constant memory). Combine: read FITS chunk -> normalize -> write temp TIFF strip -> pyvips dzsave on final TIFF. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| astropy | >=7.0 | FITS I/O, WCS parsing, image normalization, coordinate transforms | The astronomy Python standard. 7.2.0 is current stable (Nov 2025). Handles all FITS operations, WCS standards, coordinate frames. |
| astroquery | >=0.4.11 | MAST API access, JWST observation queries, product downloads | Official astropy-affiliated package for archive access. 0.4.11 is current stable (Sep 2025). Wraps MAST REST API with Python objects. |
| pyvips | >=3.1.0 | DZI tile pyramid generation from large images | Binding for libvips -- streams images without loading into memory. dzsave() generates DeepZoom pyramids. 3.1.x is current (Dec 2025). |
| numpy | >=1.26 | Array operations for FITS data manipulation | Already a transitive dependency of astropy. Required for FITS data arrays, normalization math. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | >=10.0 | Image format conversion (numpy array to PNG/JPEG for intermediate steps) | Bridge between numpy arrays and image file formats for tile generation |
| dask | >=2024.1 | Optional: lazy array operations for very large FITS | Only needed if numpy + memmap chunk processing proves insufficient for specific files |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DZI (pyvips) | HiPS (hipsgen) | HiPS is the astronomical standard for all-sky surveys, uses HEALPix tessellation with native spherical coordinates. But: HiPS is designed for multi-survey all-sky composites, not single-observation tiling. DZI is simpler, directly supported by OpenSeadragon and pyvips, and maps cleanly to per-observation tile sets. HiPS would be appropriate if the project later needs all-sky survey mosaics. |
| DZI (pyvips) | Leaflet/Slippy tiles | Google Maps-style XYZ tiles. Similar simplicity to DZI. But: pyvips dzsave has first-class DZI support and OpenSeadragon is purpose-built for DZI. No advantage to slippy tiles for single-image viewing. |
| pyvips | deepzoom.py / Pillow-based tilers | Pure-Python DZI generators exist. But: they load entire images into memory (fatal for trillion-pixel), are 10-100x slower, and lack streaming. pyvips/libvips is the correct tool for large-image tiling. |
| astroquery.mast | Direct MAST REST API (requests/httpx) | Could call MAST API directly. But: astroquery handles authentication, pagination, retry logic, product URI resolution, and cloud data access. No reason to hand-roll. |

**Installation:**
```bash
# System dependency (macOS)
brew install vips

# Python packages
uv pip install astropy>=7.0 astroquery>=0.4.11 pyvips>=3.1.0 Pillow>=10.0
```

## Architecture Patterns

### Recommended Project Structure
```
pipeline/
    tasks/
        __init__.py
        test_noop.py          # existing
        ingest.py             # NEW: orchestration task chain
        download.py           # NEW: MAST query + download
        validate_wcs.py       # NEW: WCS extraction + validation
        tile.py               # NEW: FITS normalization + DZI tiling
shared/
    config.py                 # existing (add MAST settings)
    models.py                 # existing (Observation model already has fields)
    s3.py                     # NEW: factored S3 client (pending TODO from Phase 1)
```

### Pattern 1: Celery Task Chain for Ingestion Pipeline
**What:** Chain of Celery tasks: download -> validate_wcs -> tile, with each step recording a ProcessingStep in PostgreSQL.
**When to use:** Every observation ingestion follows this chain.
**Example:**
```python
# pipeline/tasks/ingest.py
from celery import chain
from pipeline.celery_app import celery_app

@celery_app.task
def ingest_observation(observation_id: str, program_id: str | None = None):
    """Orchestrate the full ingestion pipeline for a JWST observation."""
    # Create Observation record in PostgreSQL
    obs_uuid = create_observation_record(observation_id, program_id)

    # Chain: download -> validate_wcs -> tile
    pipeline = chain(
        download_fits.s(obs_uuid, observation_id, program_id),
        validate_wcs.s(obs_uuid),
        generate_tiles.s(obs_uuid),
    )
    pipeline.apply_async()
    return {"observation_uuid": str(obs_uuid), "status": "pipeline_started"}
```

### Pattern 2: Chunked FITS Processing for Large Images
**What:** Read FITS data in row-band chunks using memmap, normalize each chunk, write to intermediate striped TIFF, then run pyvips dzsave on the TIFF.
**When to use:** All FITS-to-tile conversions (the default path, not just for large files).
**Example:**
```python
# Source: astropy official docs + pyvips docs
from astropy.io import fits
from astropy.visualization import ZScaleInterval, AsinhStretch, ImageNormalize
import numpy as np
import pyvips

def generate_tile_pyramid(fits_path: str, output_dir: str, tile_size: int = 256):
    """Generate DZI tile pyramid from FITS file."""
    with fits.open(fits_path, memmap=True, mode='denywrite') as hdul:
        data = hdul[0].data  # or hdul['SCI'].data for MEF

        # Compute normalization parameters on a subsample (not full image)
        sample = data[::10, ::10]  # every 10th pixel
        interval = ZScaleInterval()
        vmin, vmax = interval.get_limits(sample)

        # Normalize and stretch full image in chunks
        # ... (chunked processing pattern below)

    # Generate DZI pyramid with pyvips
    vips_image = pyvips.Image.new_from_file(temp_tiff_path, access='sequential')
    vips_image.dzsave(
        output_dir,
        tile_size=tile_size,
        overlap=1,
        depth='onepixel',  # full pyramid from max resolution to 1px
        suffix='.jpg[Q=85]',
        layout='dz',
    )
```

### Pattern 3: FITS-to-RGB Normalization
**What:** Convert 32-bit float FITS data to 8-bit RGB suitable for web tile display using astropy visualization stretches.
**When to use:** Before any tiling operation -- FITS data must be normalized to [0, 255] uint8.
**Example:**
```python
# Source: astropy.visualization docs
from astropy.visualization import ZScaleInterval, AsinhStretch, ImageNormalize
import numpy as np

def normalize_fits_chunk(data_chunk: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    """Normalize a FITS data chunk to 8-bit grayscale."""
    # Handle NaN/Inf values (common in astronomical data)
    data_chunk = np.nan_to_num(data_chunk, nan=0.0, posinf=0.0, neginf=0.0)

    # Apply asinh stretch (preserves both faint and bright features)
    stretch = AsinhStretch(a=0.1)

    # Normalize to [0, 1]
    norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=stretch)
    normalized = norm(data_chunk)

    # Convert to uint8
    return (normalized * 255).astype(np.uint8)
```

### Pattern 4: S3-Based Tile Storage
**What:** Upload DZI tiles to MinIO bucket following DZI directory structure. Serve tiles via presigned URLs or direct MinIO access.
**When to use:** After tile generation, tiles go to MinIO `tiles` bucket for web serving.
**Example:**
```python
# Tile storage path convention in MinIO
# tiles/{observation_uuid}/{resolution_level}/{column}_{row}.jpg
# tiles/{observation_uuid}/{observation_uuid}.dzi  (metadata XML)
```

### Anti-Patterns to Avoid
- **Loading full FITS into memory:** Never use `hdul[0].data[:]` or `.copy()` on large files. Always use memmap + chunk slicing.
- **Tiling with Pillow/PIL:** Pillow loads entire images into RAM. Use pyvips for any tiling operation.
- **Custom tile format:** Do not invent a tile naming/storage scheme. Use DZI standard exactly as pyvips produces it.
- **Normalizing per-tile:** Compute normalization parameters (vmin/vmax) once per image from a subsample, then apply to all chunks. Per-tile normalization creates visible seams.
- **Downloading all MAST products:** Filter to specific calibration levels (2 or 3) and SCIENCE product type. Unfiltered downloads include guide star data, previews, and other unwanted files.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MAST API client | Custom REST client for MAST | astroquery.mast | Handles auth tokens, pagination, product URI resolution, cloud data access, retry logic |
| WCS parsing | Manual FITS header keyword parsing | astropy.wcs.WCS(header) | WCS standard has 4+ papers of complexity. SIP distortions, CD matrix vs CDELT, projection types. Never parse manually. |
| Image tiling | Pillow-based tile cutter, custom pyramid builder | pyvips.dzsave() | Memory-safe streaming, handles overlap, generates all zoom levels, produces standard DZI XML |
| FITS normalization | Manual min/max scaling | astropy.visualization (ZScaleInterval, AsinhStretch) | ZScale is the astronomical standard for auto-scaling. Asinh stretch handles the enormous dynamic range of astronomical images (faint nebulae + bright stars). |
| Coordinate validation | Custom RA/Dec range checks | astropy.wcs validation + round-trip test | WCS validation includes projection checks, axis consistency, unit validation beyond simple range checks |
| FITS data type handling | Manual BSCALE/BZERO application | astropy.io.fits (automatic) | astropy automatically applies BSCALE/BZERO scaling when reading data. Hand-rolling this is error-prone. |

**Key insight:** Astronomical data processing is a mature domain with battle-tested libraries. Every "simple" operation (WCS parsing, FITS scaling, coordinate transforms) has edge cases that take months to discover. The astropy ecosystem exists precisely because these problems are deceptively complex.

## Common Pitfalls

### Pitfall 1: Memory Exhaustion on Large FITS Files
**What goes wrong:** Loading a 100GB+ FITS file with `data = hdul[0].data[:]` or `np.array(hdul[0].data)` consumes all available RAM and the process is killed.
**Why it happens:** FITS data arrays can be enormous. A 100,000 x 100,000 pixel float32 image is ~40GB. Default numpy operations eagerly materialize arrays.
**How to avoid:** Always open with `memmap=True` and `mode='denywrite'`. Process in row-band chunks (e.g., 4096 rows). Never call `.copy()` on the full data array. Use `mmap.MADV_SEQUENTIAL` hint for sequential access patterns.
**Warning signs:** Process memory growing linearly during FITS read. OOM killer activation. Swap thrashing.

### Pitfall 2: NaN and Inf Values in FITS Data
**What goes wrong:** Astronomical FITS data commonly contains NaN (not-a-number) and Inf values for bad/saturated pixels. These propagate through normalization and produce black or white artifacts in tiles.
**Why it happens:** Detector bad pixels, cosmic ray hits, saturation, and calibration artifacts all produce non-finite values in calibrated FITS data.
**How to avoid:** Always apply `np.nan_to_num()` before normalization. Consider using astropy's `Cutout2D` which handles edge cases. Track NaN pixel masks separately for scientific validity.
**Warning signs:** Black patches in tiles. All-white tiles at certain zoom levels. Normalization producing vmin=vmax.

### Pitfall 3: MAST obsid vs obs_id Confusion
**What goes wrong:** Using `obs_id` (the mission-specific observation identifier like "jw01073001001_02101_00001_nrca1") where MAST expects `obsid` (the MAST internal integer product group ID) or vice versa.
**Why it happens:** MAST's `Observations.get_product_list()` requires the MAST `obsid`, not the mission `obs_id`. The astroquery docs explicitly warn about this.
**How to avoid:** Always query with `Observations.query_criteria()` first to get the full result table including both identifiers. Pass the table rows (which contain `obsid`) to `get_product_list()`, not raw ID strings.
**Warning signs:** Empty product lists. "No products found" when products clearly exist.

### Pitfall 4: WCS in Wrong Extension
**What goes wrong:** Extracting WCS from `hdul[0].header` when the actual science data and WCS are in a different extension (e.g., `hdul['SCI']` or `hdul[1]`).
**Why it happens:** JWST FITS files are Multi-Extension FITS (MEF). The primary HDU (index 0) often contains only global metadata, while the SCI extension contains the image data and its WCS. JWST also stores WCS in ASDF format within the file.
**How to avoid:** Always check for named extensions ('SCI', 'ERR', 'DQ'). Iterate HDUs to find the one with NAXIS > 0. For JWST data, prefer `hdul['SCI'].header` for WCS extraction.
**Warning signs:** WCS object with 0 axes. NAXIS=0 in the header you're reading. Coordinate transforms returning nonsense values.

### Pitfall 5: Tile Normalization Inconsistency
**What goes wrong:** Each tile is independently normalized, causing visible brightness discontinuities at tile boundaries.
**Why it happens:** Computing ZScale/percentile limits independently per tile produces different vmin/vmax for each tile.
**How to avoid:** Compute normalization parameters ONCE from a representative subsample of the full image (every Nth pixel). Apply those fixed parameters to all chunks/tiles. Store vmin/vmax in step_output_metadata for reproducibility.
**Warning signs:** Checkerboard brightness pattern in tile viewer. Seams visible at tile boundaries.

### Pitfall 6: MAST Token Expiration
**What goes wrong:** Downloads fail silently or return access-denied errors partway through a large observation download.
**Why it happens:** MAST API tokens expire after 10 days of non-use. For exclusive access (proprietary) data, authentication is required.
**How to avoid:** Set MAST_API_TOKEN environment variable. Implement token refresh/validation before starting large downloads. For public data (most JWST data after the 1-year proprietary period), no token is needed.
**Warning signs:** HTTP 401/403 responses. Partial download manifests with errors.

### Pitfall 7: pyvips/libvips Not Installed
**What goes wrong:** `import pyvips` fails because libvips shared library is not on the system library path.
**Why it happens:** pyvips is a Python binding that requires the libvips C library to be installed separately. `pip install pyvips` installs only the binding, not the library.
**How to avoid:** Document the `brew install vips` (macOS) or `apt install libvips-dev` (Linux) prerequisite. Check for libvips in the system before running the tiling pipeline. Docker images should include libvips.
**Warning signs:** ImportError or OSError on `import pyvips`. "libvips not found" message.

## Code Examples

Verified patterns from official sources:

### MAST Query and Download
```python
# Source: astroquery.readthedocs.io/en/latest/mast/mast_obsquery.html
from astroquery.mast import Observations

# Query by observation ID or program ID
obs_table = Observations.query_criteria(
    obs_collection='JWST',
    proposal_id='1073',        # program ID
    instrument_name='NIRCAM*',  # wildcard recommended for JWST
    dataRights='PUBLIC',
)

# Get data products for specific observations
products = Observations.get_product_list(obs_table[0:5])

# Filter to calibrated FITS science products
filtered = Observations.filter_products(
    products,
    extension='fits',
    calib_level=[2, 3],       # Level 2 (calibrated) or Level 3 (combined)
    productType='SCIENCE',
)

# Download to local directory
manifest = Observations.download_products(
    filtered,
    download_dir='./mast_downloads',
)
# manifest is a Table with columns: Local Path, Status, Message, URL
```

### WCS Extraction and Validation
```python
# Source: docs.astropy.org/en/stable/wcs/loading_from_fits.html
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

with fits.open(fits_path, memmap=True) as hdul:
    # Find the SCI extension (JWST MEF structure)
    sci_hdu = hdul['SCI'] if 'SCI' in hdul else hdul[0]
    w = WCS(sci_hdu.header)

    # Extract pointing coordinates (image center)
    ny, nx = sci_hdu.data.shape
    center_sky = w.pixel_to_world(nx // 2, ny // 2)
    ra_deg = center_sky.ra.deg   # Right Ascension in degrees
    dec_deg = center_sky.dec.deg  # Declination in degrees

    # Validate WCS with round-trip test
    test_pixels = np.array([[0, 0], [nx//2, ny//2], [nx-1, ny-1]], dtype=np.float64)
    world = w.all_pix2world(test_pixels, 0)
    roundtrip = w.all_world2pix(world, 0)
    max_error = np.max(np.abs(test_pixels - roundtrip))
    wcs_valid = max_error < 1.0  # sub-pixel accuracy

    # Extract provenance from header
    header = sci_hdu.header
    provenance = {
        'telescope': header.get('TELESCOP', 'UNKNOWN'),
        'instrument': header.get('INSTRUME', 'UNKNOWN'),
        'filter': header.get('FILTER', header.get('FILTER1', 'UNKNOWN')),
        'exposure_time': header.get('EXPTIME', 0.0),
    }
```

### Chunked FITS Normalization to TIFF
```python
# Source: astropy docs (memmap, visualization) + pyvips docs
from astropy.io import fits
from astropy.visualization import ZScaleInterval, AsinhStretch
import numpy as np
from pathlib import Path

def fits_to_normalized_tiff(fits_path: str, tiff_path: str, chunk_rows: int = 4096):
    """Convert FITS to normalized 8-bit TIFF in chunks (constant memory)."""
    with fits.open(fits_path, memmap=True, mode='denywrite') as hdul:
        sci = hdul['SCI'] if 'SCI' in hdul else hdul[0]
        data = sci.data
        ny, nx = data.shape

        # Compute normalization from subsample
        step = max(1, ny // 100)
        sample = data[::step, ::step]
        sample = np.nan_to_num(np.array(sample, dtype=np.float32))
        interval = ZScaleInterval()
        vmin, vmax = interval.get_limits(sample)
        stretch = AsinhStretch(a=0.1)

        # Write normalized chunks to TIFF via pyvips sequential write
        # (Alternative: write raw strips then dzsave)
        import pyvips

        strips = []
        for y_start in range(0, ny, chunk_rows):
            y_end = min(y_start + chunk_rows, ny)
            chunk = np.array(data[y_start:y_end, :], dtype=np.float32)
            chunk = np.nan_to_num(chunk)

            # Normalize to [0, 1] then to uint8
            chunk = np.clip((chunk - vmin) / (vmax - vmin), 0, 1)
            chunk = stretch(chunk)
            chunk_uint8 = (chunk * 255).astype(np.uint8)

            # Convert to pyvips strip
            strip = pyvips.Image.new_from_memory(
                chunk_uint8.tobytes(), nx, y_end - y_start, 1, 'uchar'
            )
            strips.append(strip)

        # Join all strips vertically and save as TIFF
        full_image = strips[0].arrayjoin(strips[1:], across=1) if len(strips) > 1 else strips[0]
        # Note: for truly huge images, use pyvips sequential write instead of arrayjoin
        full_image.tiffsave(tiff_path, tile=True, pyramid=True, compression='jpeg', Q=85)
```

### DZI Tile Pyramid Generation
```python
# Source: libvips.org/API/current/making-image-pyramids.html
import pyvips

def generate_dzi_tiles(tiff_path: str, output_base: str, tile_size: int = 256):
    """Generate DZI tile pyramid from normalized TIFF."""
    image = pyvips.Image.new_from_file(tiff_path, access='sequential')

    image.dzsave(
        output_base,           # Creates {output_base}.dzi and {output_base}_files/
        tile_size=tile_size,   # 256 for web viewing
        overlap=1,             # 1px overlap prevents seam artifacts
        depth='onepixel',      # Full pyramid down to 1px
        suffix='.jpg[Q=85]',   # JPEG tiles at quality 85
        layout='dz',           # DeepZoom format
    )
    # Output structure:
    #   {output_base}.dzi          -- XML metadata
    #   {output_base}_files/
    #       0/                     -- lowest zoom (1px)
    #       1/
    #       ...
    #       N/                     -- highest zoom (full resolution)
    #           0_0.jpg, 0_1.jpg, ...  -- tiles as col_row.jpg
```

### Upload Tiles to MinIO
```python
# Pattern for uploading DZI tile directory to MinIO
import boto3
from pathlib import Path

def upload_tiles_to_minio(
    local_dzi_base: str,
    observation_uuid: str,
    s3_client,
    bucket: str = 'tiles',
):
    """Upload DZI tile pyramid to MinIO."""
    base_path = Path(local_dzi_base)

    # Upload .dzi metadata file
    dzi_file = f"{local_dzi_base}.dzi"
    s3_key = f"{observation_uuid}/{observation_uuid}.dzi"
    s3_client.upload_file(dzi_file, bucket, s3_key, ExtraArgs={'ContentType': 'application/xml'})

    # Upload all tile files
    tiles_dir = Path(f"{local_dzi_base}_files")
    for tile_file in tiles_dir.rglob('*.jpg'):
        relative = tile_file.relative_to(tiles_dir)
        s3_key = f"{observation_uuid}/tiles/{relative}"
        s3_client.upload_file(
            str(tile_file), bucket, s3_key,
            ExtraArgs={'ContentType': 'image/jpeg'},
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| astropy < 5.0 FITS lazy loading | astropy >= 5.0 proper dask array support in FITS HDU | 2022 (astropy 5.0) | Can write dask arrays directly to FITS, avoiding full materialization |
| Manual WCS keyword parsing | astropy.wcs with APE 14 common WCS API (pixel_to_world) | 2019 (astropy 4.0) | Unified high-level API that returns SkyCoord objects regardless of WCS flavor |
| Custom tile cutters (Pillow) | pyvips dzsave with streaming | Stable since libvips 8.x | Memory-safe tiling of arbitrary-size images |
| astroquery.mast classic Observations API | astroquery.mast.MastMissions for JWST-specific queries | 2025 (astroquery 0.4.10+) | Mission-specific metadata fields, improved product filtering |
| HiPS for single-observation viewing | DZI for per-observation, HiPS for all-sky surveys | Ongoing | HiPS remains standard for survey-level data; DZI is simpler for isolated observations |

**Deprecated/outdated:**
- `pyfits`: Merged into astropy.io.fits years ago. Never use standalone pyfits.
- `astropy.nddata.CCDData` for large FITS: Not suitable for trillion-pixel images; use raw FITS + memmap.
- `Observations.download_products(curl_flag=True)`: Curl script download is legacy; direct download with `download_products()` is preferred for programmatic pipelines.

## Open Questions

1. **pyvips FITS loading vs astropy FITS loading**
   - What we know: pyvips has `fitsload()` but its FITS support is basic. astropy's FITS handling is comprehensive (handles all FITS extensions, WCS, BSCALE/BZERO).
   - What's unclear: Whether pyvips can directly load and dzsave a FITS file without going through an intermediate TIFF, and whether it handles 32-bit float FITS with proper normalization.
   - Recommendation: Use astropy for FITS reading/normalization, write intermediate TIFF, then pyvips for tiling. This separates concerns cleanly and uses each tool where it's strongest. Validate during implementation whether direct pyvips FITS loading can skip the intermediate TIFF for simple cases.

2. **SAM tile size alignment with DZI tiles**
   - What we know: SAM expects 1024x1024 input. DZI default tile size is 256px. These are different use cases.
   - What's unclear: Whether the Phase 4 SAM pipeline should use DZI tiles directly (4 tiles = 1 SAM input) or produce separate 1024px tiles during ingestion.
   - Recommendation: Generate DZI at 256px tile size for web viewing. For SAM (Phase 4), either read 1024px blocks directly from the normalized TIFF in MinIO or generate a second tile set at 1024px. Defer the exact SAM tile strategy to Phase 4 planning, but ensure the normalized TIFF or full-resolution DZI tiles are available in MinIO for Phase 4 to consume.

3. **Multi-band/Multi-extension FITS handling**
   - What we know: JWST data has multiple extensions (SCI, ERR, DQ, plus multiple filters). Level 3 products may combine multiple exposures.
   - What's unclear: Whether to tile only the primary SCI extension or generate separate tile sets per filter/band.
   - Recommendation: For v1, tile only the primary SCI extension of each FITS file. Store the filter name in metadata. Multi-band composites (false color from multiple filters) can be added later. Each FITS file with a unique observation_id + filter gets its own tile set.

4. **Intermediate file storage during processing**
   - What we know: The pipeline produces intermediate files (downloaded FITS, normalized TIFF, DZI tiles). FITS files go to MinIO `fits-raw` bucket. Tiles go to MinIO `tiles` bucket.
   - What's unclear: Whether intermediate TIFFs should be stored in MinIO or local temp storage, and cleanup strategy.
   - Recommendation: Use local temp directory for intermediate TIFF (cleaned up after tile upload). Store raw FITS in MinIO `fits-raw`. Store DZI tiles in MinIO `tiles`. The intermediate TIFF is transient processing artifact, not a data product.

5. **MAST download resilience**
   - What we know: MAST downloads can be large (many GB per observation). Network issues, timeouts, and rate limits are real concerns.
   - What's unclear: Exact MAST API rate limits. Whether astroquery handles retry automatically.
   - Recommendation: Implement download with Celery retry (exponential backoff). Download products individually rather than in bulk. Validate file integrity (check FITS can be opened) after download. Store download manifest in step_output_metadata for resume capability.

## Sources

### Primary (HIGH confidence)
- [astroquery MAST Observation Queries](https://astroquery.readthedocs.io/en/latest/mast/mast_obsquery.html) - query_criteria, get_product_list, filter_products, download_products API
- [astroquery MAST Missions](https://astroquery.readthedocs.io/en/latest/mast/mast_missions.html) - MastMissions class for JWST-specific metadata
- [astropy WCS loading from FITS](https://docs.astropy.org/en/stable/wcs/loading_from_fits.html) - WCS extraction patterns, pixel_to_world, coordinate transforms
- [astropy WCS validation](https://docs.astropy.org/en/stable/wcs/validation.html) - wcslint, bounds checking
- [astropy FITS large files tutorial](https://learn.astropy.org/tutorials/FITS-large.html) - memmap, chunk processing, MADV_SEQUENTIAL
- [astropy image normalization](https://docs.astropy.org/en/stable/visualization/normalization.html) - ZScaleInterval, AsinhStretch, ImageNormalize
- [libvips image pyramid docs](https://www.libvips.org/API/current/making-image-pyramids.html) - dzsave parameters, tile formats, memory usage
- [pyvips documentation](https://libvips.github.io/pyvips/vimage.html) - Image class, numpy integration, dzsave
- [JWST science products docs](https://jwst-pipeline.readthedocs.io/en/latest/jwst/data_products/science_products.html) - FITS extension structure, MEF format, calibration levels
- [JWST data formats](https://jwst-docs.stsci.edu/getting-started-with-jwst-data/understanding-jwst-data-files/jwst-data-formats) - header keywords, processing stages

### Secondary (MEDIUM confidence)
- [MAST API access docs](https://jwst-docs.stsci.edu/accessing-jwst-data/mast-api-access) - MAST token, authentication
- [MAST large downloads notebook](https://spacetelescope.github.io/mast_notebooks/notebooks/multi_mission/large_downloads/large_downloads.html) - batch download strategies
- [OpenSeadragon DZI format](https://github.com/openseadragon/openseadragon/wiki/The-DZI-File-Format) - DZI file structure for Phase 3 compatibility
- [Aladin Lite](https://github.com/cds-astro/aladin-lite) - HiPS viewer alternative (evaluated but not recommended for v1)
- [astropy PyPI release](https://pypi.org/project/astropy/) - version 7.2.0 confirmed
- [astroquery PyPI release](https://pypi.org/project/astroquery/) - version 0.4.11 confirmed
- [pyvips PyPI release](https://pypi.org/project/pyvips/) - version 3.1.x confirmed

### Tertiary (LOW confidence)
- SAM input size 1024x1024: Based on multiple sources (HuggingFace forums, GitHub issues) but exact SAM 2 requirements may differ. Validate during Phase 4 research.
- MAST API rate limits: No official documentation found. Implementation should include retry logic regardless.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - astropy, astroquery, pyvips all verified via official docs and PyPI with current versions
- Architecture: HIGH - Celery chain pattern proven in Phase 1; chunked processing is standard for large astronomical images
- Pitfalls: HIGH - All pitfalls sourced from official documentation warnings, GitHub issues, or standard astronomical data processing experience
- Tiling format (DZI vs HiPS): MEDIUM - DZI is the pragmatic choice for per-observation tiling but HiPS may be needed later for all-sky views
- Memory-safe pipeline: MEDIUM - The chunked FITS -> TIFF -> DZI pipeline is sound in principle but the exact pyvips arrayjoin vs sequential write approach needs validation with a real trillion-pixel FITS file

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (30 days - libraries are stable, MAST API is stable)
