# Phase 4: Segmentation - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect, segment, and store every distinguishable object in ingested JWST imagery. Uses traditional source detection (SEP/photutils) as baseline and prompt source, plus SAM 3 for pixel-level segmentation masks. Produces per-object cutout images and masks. Does NOT classify objects or identify artifacts — that is Phase 5. Does NOT build object hierarchy/relationships — that is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Segmentation Approach
- Hybrid pipeline: SEP/photutils for traditional source detection + SAM 3 for pixel-level segmentation
- Both tools implemented in this phase — SEP finds where objects are, SAM 3 delineates what each object looks like
- Target SAM 3 specifically (Meta's latest, released Nov 2025) — leverage text-prompt segmentation capabilities for astronomical objects
- GPU preferred for SAM inference, but CPU fallback required — must work without CUDA

### Detection Scope
- Tiered detection with three confidence levels: High (definite source), Medium (likely real), Low (uncertain/borderline)
- No hard SNR cutoff — detect everything, assign to confidence tiers. Classification phase decides what's real
- All three tiers get full SAM segmentation (SAM on everything, not just high-confidence)
- Edge-of-image objects: detect and flag as 'partial/edge' in metadata, segment what's visible

### Object Granularity
- Multi-scale processing at three levels: full field, sub-regions, sub-sub-regions
- Hierarchical detection: detect large structures AND sub-structures within them (e.g., galaxy + spiral arms + core)
- Aggressive deblending in crowded fields — process at multiple zoom levels to separate overlapping sources
- Flat object list output — all objects at all scales stored without parent-child relationships (Phase 7 builds hierarchy)
- Keep all detections across scales, deduplicate later — Phase 5 or 7 handles deduplication with more context

### Artifact Handling
- Detect-then-tag approach: pipeline detects artifacts (diffraction spikes, cosmic rays, hot pixels) like any other source
- No pre-filtering of artifacts before detection — everything goes through the full pipeline
- Diffraction spikes get masks like anything else — they're large features but treated consistently
- No artifact-specific metadata in Phase 4 — Phase 5 classification handles all artifact identification
- No special heuristics or flagging — keep Phase 4 focused purely on detection and segmentation

### Cutout Presentation
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

</decisions>

<specifics>
## Specific Ideas

- Multi-scale processing should work like zooming in: first pass sees the whole field, second pass zooms into regions, third pass zooms into dense sub-regions within those
- SAM 3's text-prompt capability could enable concept-based sweeps ("segment all galaxies", "segment all stars") alongside traditional point prompts from SEP
- The three confidence tiers should flow through to the API so downstream phases can filter by confidence

</specifics>

<deferred>
## Deferred Ideas

- Parent-child object relationships (hierarchy) — Phase 7 Knowledge Graph
- Artifact classification and identification — Phase 5 Classification
- Object deduplication across scales — Phase 5 or Phase 7
- Adaptive scale levels (subdivide further only where density is high) — potential future optimization

</deferred>

---

*Phase: 04-segmentation*
*Context gathered: 2026-02-22*
