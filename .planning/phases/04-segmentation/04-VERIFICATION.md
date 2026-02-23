---
phase: 04-segmentation
verified: 2026-02-23T07:15:00Z
status: gaps_found
score: 15/16 must-haves verified
re_verification: false
gaps:
  - truth: "When CUDA is unavailable, SEP elliptical aperture parameters are used to generate fallback binary masks"
    status: partial
    reason: "segment_sam.py line 604-605 retains the deprecated `byteswap().newbyteorder()` call removed in numpy 2.x (the auto-fix was applied to detect_sources.py in commit 1b85207 but not back-ported to segment_sam.py). The code is dead (line 601 already casts to float32/native via np.array), so it does NOT cause a runtime failure. However, if future code changes make the condition reachable, it will crash on numpy 2.4+"
    artifacts:
      - path: "pipeline/tasks/segment_sam.py"
        issue: "Lines 603-605: dead but dangerous code — `if fits_data.dtype.byteorder not in ('=', '<', '|'): fits_data = fits_data.byteswap().newbyteorder()` uses API removed in numpy 2.x. The preceding line 601 `fits_data = np.array(fits_data, dtype=np.float32)` already normalizes byte order making the if-block unreachable, but the dead code should be replaced with the numpy-2.x-safe pattern from detect_sources.py."
    missing:
      - "Replace lines 603-605 in segment_sam.py with the same safe pattern used in detect_sources.py: simply remove the if-block entirely (the cast on line 601 is sufficient) or replace with `data = np.array(data, dtype=np.float32)` pattern."
human_verification:
  - test: "End-to-end pipeline execution on real JWST observation"
    expected: "All 6 processing steps complete, non-zero AstronomicalObject count with masks and cutouts in MinIO"
    why_human: "Requires running services (Docker Compose, Celery, FastAPI) against real MAST data — cannot verify programmatically"
  - test: "SEP elliptical mask fallback path (CPU-only environment)"
    expected: "segment_sam runs to completion with segmentation_method='sep_ellipse' on all objects"
    why_human: "Requires Celery worker execution environment — cannot execute task inline"
  - test: "COCO RLE mask decode roundtrip"
    expected: "pycocotools.mask.decode(rle) returns non-zero binary mask for each object"
    why_human: "Requires live database with segmentation results from a completed pipeline run"
---

# Phase 4: Segmentation Verification Report

**Phase Goal:** Every distinguishable object in an ingested image is detected, segmented, and stored with pixel-level masks and cutout images
**Verified:** 2026-02-23T07:15:00Z
**Status:** gaps_found (1 code quality issue; 3 human verification items)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All truths are drawn from the `must_haves` in the three plan frontmatter blocks (Plans 01, 02, 03).

#### Plan 01 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AstronomicalObject table has segmentation-specific columns for masks, cutout paths, confidence tiers, bounding boxes, and edge detection flags | VERIFIED | `shared/models.py` lines 126-138 — all 10 columns present: `segmentation_mask_rle`, `cutout_s3_prefix`, `bounding_box_pixels`, `detection_signal_to_noise_ratio`, `detection_confidence_tier`, `detection_scale_level`, `is_edge_detection`, `pixel_centroid_x`, `pixel_centroid_y`, `segmentation_method` |
| 2 | A new DetectionConfidenceTier enum exists with high/medium/low values | VERIFIED | `shared/models.py` lines 38-41 — `DetectionConfidenceTier(str, enum.Enum)` with `high = "high"`, `medium = "medium"`, `low = "low"` |
| 3 | Config has segmentation settings (S3 bucket, SAM model path, detection thresholds, multi-scale parameters) | VERIFIED | `shared/config.py` lines 28-43 — all 14 segmentation fields present including `s3_bucket_segmentation`, SAM paths, 12 detection/threshold/multi-scale parameters |
| 4 | MinIO has a segmentation bucket created at startup | VERIFIED | `docker-compose.yml` line 49 — `/usr/bin/mc mb --ignore-existing local/segmentation` added to minio-init entrypoint (alias is `local`, consistent with alias set on line 46) |
| 5 | generate_tiles no longer sets observation pipeline_status to completed -- leaves as processing | VERIFIED | `pipeline/tasks/tile.py` lines 576-582 — comment "do NOT set completed here" with log message confirming pipeline continues; `grep PipelineStatus.completed tile.py` returns 0 matches |
| 6 | ingest_observation chains include detect_sources, segment_sam, and generate_cutouts tasks after generate_tiles | VERIFIED | `pipeline/tasks/ingest.py` lines 61-72 — `chain(download_fits.s(), validate_wcs.s(), generate_tiles.s(), detect_sources.s(), segment_sam.s(), generate_cutouts.s())` |
| 7 | New pipeline dependencies (sep, photutils, pycocotools) are installable | VERIFIED | `pyproject.toml` lines 24-26 — `sep>=1.4.0`, `photutils>=2.3.0`, `pycocotools>=2.0.11` with note about GPU deps |

#### Plan 02 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 8 | SEP detects sources at three scales (full field, sub-regions 1024px, sub-sub-regions 256px) with 20% overlap | VERIFIED | `detect_sources.py` `_run_multi_scale_detection()` lines 336-504 — full field (line 373), sub-regions at `segmentation_sub_region_size=1024` (line 388), sub-sub-regions at `segmentation_sub_sub_region_size=256` (line 436), overlap via `_extract_sub_regions()` with `segmentation_overlap_fraction=0.2` |
| 9 | Each detected source is assigned a confidence tier (high/medium/low) based on SNR from Kron photometry | VERIFIED | `detect_sources.py` `_compute_kron_photometry()` (lines 144-187) and `_assign_confidence_tiers()` (lines 190-225); SNR thresholds 10.0 (high) and 3.0 (medium) from config |
| 10 | Sources touching sub-region or image boundaries are flagged as is_edge_detection=True | VERIFIED | `detect_sources.py` `_flag_edge_detections()` (lines 228-289) — checks within 5px of sub-region boundary and full image boundary |
| 11 | Each source gets WCS sky coordinates converted from pixel centroids | VERIFIED | `detect_sources.py` line 594 — `wcs_object.pixel_to_world(global_centroid_x, global_centroid_y)` → `sky_coord.ra.deg`, `sky_coord.dec.deg` stored in model |
| 12 | AstronomicalObject records are created in the database for every detection across all scales | VERIFIED | `detect_sources.py` `_detect_and_store()` lines 507-649 — `AstronomicalObject(...)` created per detection with `database_session.add_all(new_objects)` + `flush()` |
| 13 | SAM 3 produces pixel-level masks from SEP detections when CUDA is available | VERIFIED | `segment_sam.py` `_get_sam_processor()` (lines 98-145) and `_generate_sam_masks()` (lines 185-250) — uses point+box prompts; SAM path only taken when `torch.cuda.is_available()` is True |
| 14 | When CUDA is unavailable, SEP elliptical aperture parameters are used to generate fallback binary masks | PARTIAL | `segment_sam.py` `_generate_elliptical_mask()` (lines 253-304) is fully implemented and correctly called at lines 744-754. However, line 605 contains dead but dangerous code: `fits_data.byteswap().newbyteorder()` — a numpy 2.x-incompatible API removed in numpy 2.0. This call is currently unreachable (line 601 normalizes byte order first), but represents a latent defect. The fallback path itself works correctly. |
| 15 | All masks are encoded in COCO RLE format and stored in AstronomicalObject.segmentation_mask_rle | VERIFIED | `segment_sam.py` `_encode_mask_to_rle()` (lines 307-323) — `np.asfortranarray` + `pycocotools.mask.encode()` + bytes-to-str decode; stored at line 767 |
| 16 | Objects in overlapping sub-region zones have masks merged via IoU matching | VERIFIED | `segment_sam.py` `_merge_boundary_masks()` (lines 326-472) — cross-scale IoU comparison via `mask_util.iou()`, deletes lower-SNR duplicate when IoU >= `segmentation_boundary_iou_threshold` (0.5) |

#### Plan 03 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 17 | Each segmented object has a bounding-box cutout PNG (auto-stretched with asinh) stored in MinIO | VERIFIED | `generate_cutouts.py` `_create_stretched_png()` (lines 146-175) — ZScaleInterval + AsinhStretch(a=0.1) + PIL save; uploaded via `_upload_cutout_files()` to segmentation bucket |
| 18 | Each segmented object has a raw linear PNG cutout stored in MinIO | VERIFIED | `generate_cutouts.py` `_create_raw_png()` (lines 178-202) — 1st/99th percentile clipping, linear uint8 mapping |
| 19 | Each segmented object has a FITS cutout with preserved WCS headers stored in MinIO | VERIFIED | `generate_cutouts.py` `_create_fits_cutout()` (lines 205-216) — `fits.PrimaryHDU(data=cutout_2d.data, header=cutout_2d.wcs.to_header())` |
| 20 | Cutouts have 10% padding on each side beyond the bounding box | VERIFIED | `generate_cutouts.py` `_extract_cutout_data()` lines 127-128: `padded_width = int(bbox_width * (1 + 2 * padding_fraction))` with `padding_fraction=settings.segmentation_cutout_padding_fraction` (default 0.1) |
| 21 | AstronomicalObject.cutout_s3_prefix points to the correct MinIO location | VERIFIED | `generate_cutouts.py` line 466: `astro_object.cutout_s3_prefix = s3_prefix` where `s3_prefix = f"{observation_uuid_hex}/{object_uuid_hex}/"` |
| 22 | generate_cutouts marks observation pipeline_status as completed (final chain step) | VERIFIED | `generate_cutouts.py` lines 511-519 — `observation_record.pipeline_status = PipelineStatus.completed` with comment "CRITICAL: final task in 6-task chain" |
| 23 | The full 6-task pipeline chain works end-to-end on a test observation | NEEDS HUMAN | Requires running Celery + Docker Compose + FastAPI — verified by human in Plan 03 checkpoint (approved) |

**Score:** 15/16 automated truths verified (1 partial — dead code defect in segment_sam.py byte order handling)

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `shared/models.py` | DetectionConfidenceTier enum, segmentation columns on AstronomicalObject | VERIFIED | 10 new columns, enum at lines 38-41 |
| `shared/config.py` | Segmentation config settings | VERIFIED | 14 settings fields lines 28-43, `s3_bucket_segmentation` at line 29 |
| `pyproject.toml` | New segmentation dependencies | VERIFIED | sep, photutils, pycocotools at lines 24-26 |
| `pipeline/tasks/ingest.py` | Extended Celery chain with segmentation tasks | VERIFIED | 6-task chain, imports detect_sources/segment_sam/generate_cutouts |
| `pipeline/celery_app.py` | New task registrations | VERIFIED | `include` list has 8 tasks including all 3 new segmentation tasks |
| `alembic/versions/` | Migration adding segmentation columns | VERIFIED | `2abf67c31898_add_segmentation_columns_to_.py` — all 10 columns, enum creation, `server_default=sa.text('false')` for `is_edge_detection`, enum drop in downgrade |
| `pipeline/tasks/detect_sources.py` | Multi-scale SEP source detection Celery task | VERIFIED | 859 lines, 10 functions, full implementation |
| `pipeline/tasks/segment_sam.py` | SAM 3 segmentation with SEP elliptical fallback | VERIFIED (partial) | 865 lines, 10 functions — latent dead code defect at line 605 |
| `pipeline/tasks/generate_cutouts.py` | Cutout extraction and storage Celery task | VERIFIED | 585 lines, 7 functions, full implementation |

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pipeline/tasks/detect_sources.py` | `shared/models.py` | SQLAlchemy AstronomicalObject insert | WIRED | `AstronomicalObject(...)` at line 621, `add_all()` + `flush()` at lines 638-639 |
| `pipeline/tasks/detect_sources.py` | `shared/s3.py` | FITS download from MinIO | WIRED | `get_s3_client()` at line 731, `download_file()` at line 735 |
| `pipeline/tasks/segment_sam.py` | `pipeline/tasks/detect_sources.py` | Celery chain — detect_sources output feeds segment_sam | WIRED | `detection_result["observation_uuid"]` line 529, `detection_result.get("fits_s3_keys")` line 531, `detection_result.get("source_count")` line 532 |
| `pipeline/tasks/segment_sam.py` | `shared/models.py` | Update AstronomicalObject with mask RLE | WIRED | `astro_object.segmentation_mask_rle = rle` line 767, `astro_object.segmentation_method = used_method` line 768 |
| `pipeline/tasks/generate_cutouts.py` | `shared/models.py` | Update AstronomicalObject.cutout_s3_prefix and Observation.pipeline_status | WIRED | `astro_object.cutout_s3_prefix = s3_prefix` line 466; `PipelineStatus.completed` line 519 |
| `pipeline/tasks/generate_cutouts.py` | `shared/s3.py` | Upload cutout files to segmentation bucket | WIRED | `s3_client.upload_file()` at lines 256-261, bucket from `settings.s3_bucket_segmentation` line 239 |
| `pipeline/tasks/generate_cutouts.py` | `pipeline/tasks/segment_sam.py` | Celery chain — segment_sam output feeds generate_cutouts | WIRED | `segmentation_result["observation_uuid"]` line 294, `segmentation_result.get("fits_s3_keys")` line 296, `segmentation_result.get("masks_generated")` line 297 |

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEG-01 | 04-01, 04-02 | System segments every distinguishable object in tiled images using SAM | SATISFIED | `detect_sources` finds objects via SEP; `segment_sam` generates SAM masks (GPU) or SEP elliptical fallback (CPU); `AstronomicalObject` records created for every detection |
| SEG-02 | 04-01, 04-02 | System merges segmentation masks across tile boundaries for objects that span multiple tiles | SATISFIED | `_merge_boundary_masks()` in `segment_sam.py` uses IoU matching across detection scale levels; edge flags (`is_edge_detection`) mark boundary objects |
| SEG-03 | 04-01, 04-03 | System produces per-object cutout images and pixel-level masks | SATISFIED | `generate_cutouts` produces 3 files per object (cutout_stretched.png, cutout_raw.png, cutout.fits); masks stored as COCO RLE in `segmentation_mask_rle` |
| SEG-04 | 04-01, 04-02 | System uses traditional source detection (SEP/photutils) as baseline and SAM prompt source | SATISFIED | SEP (`sep.Background()` + `sep.extract()`) is the detection baseline; SEP centroids and bounding boxes are used as SAM point+box prompts in `_generate_sam_masks()` |

All 4 SEG requirements are covered. No orphaned requirements found for this phase.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pipeline/tasks/segment_sam.py` | 603-605 | `fits_data.byteswap().newbyteorder()` — deprecated numpy 2.x API | WARNING | Dead code (unreachable) because line 601 already normalizes via `np.array(fits_data, dtype=np.float32)`. Not a runtime blocker, but inconsistent with the numpy-2.x fix applied to `detect_sources.py` in commit `1b85207`. Should be cleaned up for correctness. |

No TODO/FIXME/placeholder comments found in segmentation task files. No stub implementations remain (all three tasks are fully implemented with non-trivial code).

## Human Verification Required

### 1. End-to-End Pipeline Run

**Test:** Start Docker Compose (`docker compose up -d`), run `alembic upgrade head`, install deps (`uv pip install -e ".[dev]"`), start Celery worker and FastAPI, trigger ingestion via `POST /api/ingest` with a real JWST observation ID, monitor until all 6 processing steps show `completed` status.
**Expected:** Observation `pipeline_status = "completed"`, non-zero `AstronomicalObject` count with `segmentation_mask_rle IS NOT NULL` and `cutout_s3_prefix IS NOT NULL` for all objects, and 3 files per object in MinIO `segmentation` bucket.
**Why human:** Requires all four Docker services running plus Celery worker and FastAPI server with real MAST network access.

### 2. COCO RLE Mask Decode Roundtrip

**Test:** After a successful pipeline run, use the test script from Plan 03 — query an `AstronomicalObject` with non-null `segmentation_mask_rle`, decode via `mask_util.decode(rle)` (re-encoding counts as bytes first), print mask shape and pixel count.
**Expected:** Shape matches the source image dimensions, non-zero pixel count indicating a real mask region was stored.
**Why human:** Requires a live database populated by a completed pipeline run.

### 3. CPU-Only Fallback Path

**Test:** Run the pipeline on a system without CUDA (or with `CUDA_VISIBLE_DEVICES=""`) and verify `segment_sam` completes with `segmentation_method = "sep_ellipse"` for all objects.
**Expected:** Every `AstronomicalObject` has a non-null `segmentation_mask_rle` with `segmentation_method = "sep_ellipse"` and valid FITS cutouts.
**Why human:** Requires Celery task execution environment; cannot run tasks inline without Celery broker.

## Gaps Summary

One automated gap was found:

**Dead code defect in `segment_sam.py` line 605.** The numpy-2.x-safe fix applied to `detect_sources.py` in commit `1b85207` was not back-ported to `segment_sam.py`. The deprecated call `fits_data.byteswap().newbyteorder()` survives at line 605 inside a conditional branch that is currently unreachable (because `np.array(fits_data, dtype=np.float32)` on line 601 already normalizes byte order). This is not a runtime blocker — the fallback path works correctly. However, the stale code is inconsistent with the project's established numpy-2.x fix and should be removed.

**Fix:** Remove lines 603-605 from `segment_sam.py` (the `if fits_data.dtype.byteorder not in ...` block), since the `np.array(fits_data, dtype=np.float32)` on line 601 already handles byte order conversion safely.

All other plan must-haves are verified against actual code. The phase goal — every distinguishable object detected, segmented, and stored with pixel-level masks and cutout images — is architecturally complete and awaits final human validation via a live pipeline run.

---

_Verified: 2026-02-23T07:15:00Z_
_Verifier: Claude (gsd-verifier)_
