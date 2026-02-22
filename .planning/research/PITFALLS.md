# Pitfalls Research

**Domain:** Astronomical data pipeline + interactive galactic encyclopedia (JWST/Rubin imagery, SAM segmentation, catalog cross-matching, knowledge graph, interactive explorer)
**Researched:** 2026-02-21
**Confidence:** HIGH (verified across official documentation, published research papers, and established astronomical computing community knowledge)

## Critical Pitfalls

### Pitfall 1: SAM Produces Garbage on Astronomical Images Without Domain Adaptation

**What goes wrong:**
SAM was trained on SA-1B -- 11 million natural photographs of everyday objects. Astronomical images have fundamentally different characteristics: 16/32-bit dynamic range (vs 8-bit), logarithmic intensity distributions, noise-dominated backgrounds, spatially extended diffuse emission (nebulae, tidal tails), overlapping sources in crowded fields, and point-spread-function artifacts. Out-of-the-box SAM will oversegment bright galaxies into meaningless sub-regions, miss faint diffuse structures entirely, segment noise spikes and cosmic ray artifacts as objects, and fail to deblend overlapping sources in crowded fields.

**Why it happens:**
SAM's training distribution has zero overlap with astronomical imagery. The model's learned priors for "object boundaries" (sharp RGB edges) do not apply to astronomical data where boundaries are defined by surface brightness profiles, not color edges. Additionally, SAM expects 8-bit 3-channel RGB input -- directly feeding a 32-bit single-channel FITS image will produce nonsense unless properly scaled and mapped to 3 channels.

**How to avoid:**
1. Start with traditional astronomical source detection (SExtractor/SEP or photutils) as a baseline -- these are battle-tested on astronomical data.
2. Use SAM only after converting FITS to properly scaled RGB representations (asinh stretch, per-band normalization).
3. Fine-tune SAM on annotated astronomical cutouts using the released SAM2 training code. Start with a small hand-annotated set from your JWST deep fields.
4. Use SAM in prompted mode with detections from traditional tools as prompts (point prompts at source centroids, bounding box prompts from catalog positions) rather than "segment everything" mode.
5. Implement a validation pipeline comparing SAM outputs against known catalog positions before trusting any segmentation run.

**Warning signs:**
- SAM segments produce hundreds of tiny fragments per galaxy instead of one coherent mask.
- Known bright stars are missed or split into rings/arcs (PSF artifact segmentation).
- Segmentation count varies wildly with minor changes to image scaling parameters.
- Background sky regions contain many spurious detections.

**Phase to address:**
Phase 1 (Pipeline Foundation). Do NOT defer SAM integration to later -- the entire downstream pipeline depends on segmentation quality. Build the traditional-detection baseline first, then layer SAM on top.

---

### Pitfall 2: WCS Coordinate Errors Silently Corrupt All Downstream Cross-Matching

**What goes wrong:**
World Coordinate System (WCS) headers in FITS files define the mapping from pixel coordinates to sky coordinates (RA/Dec). Errors in WCS -- wrong projection type, incorrect reference pixel (CRPIX), stale distortion coefficients, or missing SIP polynomial corrections -- cause pixel-to-sky transformations to be off by arcseconds to arcminutes. Since catalog cross-matching relies on positional matching within a tolerance radius (typically 1-3 arcseconds), even small WCS errors cause massive rates of false matches and missed matches. The failure is silent: you get plausible-looking but wrong cross-match results.

**Why it happens:**
- Different instruments use different WCS conventions (CD matrix vs CDELT+CROTA, SIP vs TPV distortion).
- JWST uses SIP distortion polynomials that astropy handles but some tools ignore.
- WCS solutions derived from few reference stars (< 10 matches) can have poor accuracy.
- Mosaicked images may have WCS that is accurate at the center but degrades toward edges due to projection distortion.
- Axis ordering confusion: NumPy arrays are row-major (y, x) while FITS convention is column-major (x, y / NAXIS1, NAXIS2).

**How to avoid:**
1. Validate every WCS solution before using it: convert known catalog source positions to pixel coordinates and verify they land on the correct sources visually.
2. Use `astropy.wcs.WCS` with `fix()` to handle deprecated/non-standard WCS features.
3. For images without reliable WCS, run astrometry.net to solve the WCS from scratch.
4. Store both pixel and sky coordinates for every detected source, maintaining the link to the specific WCS used, so corrections can propagate.
5. Implement a WCS quality score: number of reference stars used, RMS residual of the solution, edge-vs-center accuracy.

**Warning signs:**
- Cross-match rates suspiciously low (< 30% for well-surveyed fields) or suspiciously high (> 95% in sparse fields).
- Systematic positional offsets visible when overlaying detections on reference catalogs.
- Cross-match results change significantly when using a slightly different tolerance radius.
- astropy emits `FITSFixedWarning` about WCS keywords -- these indicate non-standard headers that may be silently misinterpreted.

**Phase to address:**
Phase 1 (Pipeline Foundation). WCS validation must be built into the ingestion pipeline before any cross-matching occurs.

---

### Pitfall 3: Memory Exhaustion Processing Trillion-Pixel FITS Images

**What goes wrong:**
A single JWST NIRCam mosaic can exceed a trillion pixels. Loading the full image array into memory at 32-bit float requires ~4 TB of RAM. Even with astropy's memory-mapping (`memmap=True`), operations that trigger a full array read (statistics, normalization, format conversion) will exhaust available memory. On systems with overcommit disabled, `mmap` itself fails with `[Errno 12] Cannot allocate memory` because the OS cannot guarantee copy-on-write backing for the entire array. The pipeline crashes or the system becomes unresponsive.

**Why it happens:**
- Developers test with small cutouts, then deploy on full mosaics.
- Many numpy/scipy operations materialize the entire array (e.g., `np.std(data)`, `data - np.median(data)`).
- astropy Tables do NOT support memory mapping -- reading catalog extensions loads everything into RAM.
- Image scaling (BSCALE/BZERO) causes astropy to create an in-memory copy of the scaled data even when memmap is enabled.
- Python garbage collection may not release mmap pages promptly.

**How to avoid:**
1. Design the pipeline for tile-based processing from day one. Never operate on full images -- always work on cutouts/tiles.
2. Use `ImageHDU.section` to read only the rows/columns needed.
3. For statistics, use streaming/chunked algorithms (e.g., Welford's online algorithm for mean/variance).
4. Open FITS files with `do_not_scale_image_data=True` when you only need header inspection or raw pixel values.
5. Implement explicit tile boundaries before any processing begins: divide the image into manageable tiles (e.g., 4096x4096 pixels) with overlap for edge objects.
6. Set hard memory limits and monitor RSS/VMS in the pipeline process.

**Warning signs:**
- Pipeline works on test images but OOM-kills on real JWST data.
- Increasing swap usage during FITS processing.
- astropy warnings about falling back to read-only arrays.
- Processing time scales super-linearly with image size.

**Phase to address:**
Phase 1 (Pipeline Foundation). The tiling strategy must be the first thing built -- every subsequent pipeline component receives tiles, not full images.

---

### Pitfall 4: Catalog Cross-Matching Produces Systematic False Associations

**What goes wrong:**
Naive nearest-neighbor cross-matching between detected sources and reference catalogs produces spurious associations at rates of 10-40% in crowded fields. The Gaia DR2 cross-match with Tycho-2, for example, showed that only 3,744 out of 13,098 binary sources matched correctly. False matches corrupt the classification pipeline: an unrelated catalog entry gets assigned to a detection, carrying wrong redshift, spectral type, or morphological class into the knowledge graph.

**Why it happens:**
- Fixed-radius matching ignores local source density: a 2" match radius is too loose in the galactic plane (crowded) and too tight in sparse high-latitude fields.
- Epoch differences between catalogs: proper motions of ~50 mas/yr over 20 years of epoch difference produce 1" offsets -- comparable to the match radius.
- Different catalogs resolve the same extended source differently (center of galaxy vs brightest knot).
- Photometric band differences cause centroid shifts for extended sources.
- Multiple catalog entries can match the same detection, requiring disambiguation logic.

**How to avoid:**
1. Use probabilistic cross-matching (Bayesian approach) that accounts for positional uncertainty, local source density, and magnitude priors -- not just closest distance. The astropy `SkyCoord.match_to_catalog_sky()` is a starting point but not sufficient alone.
2. Propagate proper motions to a common epoch before matching (critical for Gaia cross-references).
3. Apply catalog-specific match radii based on the catalog's astrometric precision.
4. For ambiguous matches (multiple candidates within tolerance), store all candidates with match probabilities rather than forcing a single assignment.
5. Validate cross-match quality by checking photometric consistency (does the matched catalog magnitude agree with the measured flux?).

**Warning signs:**
- Match fraction changes dramatically between sparse and crowded fields.
- Cross-matched sources have inconsistent photometric properties (catalog says magnitude 15, you measured magnitude 20).
- Same catalog source matched to multiple detections, or same detection matched to multiple catalog sources, at high rates.
- Known objects in your field do not appear in the match results.

**Phase to address:**
Phase 2 (Classification & Cross-Matching). But the positional infrastructure (proper WCS, coordinate storage) must be in Phase 1.

---

### Pitfall 5: Storage Costs Explode Before Funding Arrives

**What goes wrong:**
A single JWST deep field observation (all bands, all calibration levels) can be 50-200 GB. Storing the raw FITS, processed composites, tile pyramids, segmentation masks, and extracted catalogs for even a modest subset of JWST data can reach 5-10 TB within months. At AWS S3 standard pricing (~$23/TB/month), that is $115-230/month just for storage, before compute or transfer costs. The tile pyramid generation alone adds ~33% overhead. Cloud egress charges ($0.09/GB) for serving tiles to the frontend add up fast with interactive deep-zoom usage.

**Why it happens:**
- Storing multiple processing levels (raw, calibrated, mosaic, tiles, masks) multiplies storage per observation by 5-10x.
- FITS files are poorly compressible -- they are already packed binary data.
- Tile pyramids at multiple zoom levels add 33% more data.
- Developers underestimate costs because MAST provides free downloads but you pay to store and serve the data yourself.
- "Design for scale" is interpreted as "provision for scale" -- storing everything "just in case."

**How to avoid:**
1. Use MAST as your archive of record -- download and process on demand rather than pre-caching everything.
2. Implement a tiered storage strategy: keep only tile pyramids and catalogs in hot storage; raw FITS in cold/archive storage (S3 Glacier: ~$4/TB/month) or not at all (re-download from MAST).
3. Generate tile pyramids lazily on first access rather than eagerly for all data.
4. Use lossy compression (JPEG/WebP) for visual display tiles; keep lossless only for science-grade analysis.
5. Track storage costs weekly from day one. Set budget alerts.
6. Consider local NAS storage for the POC phase -- a 20TB NAS costs ~$500 once vs $460/month on S3.

**Warning signs:**
- Cloud bill increasing month-over-month without corresponding increase in processed data.
- Multiple copies of the same data at different processing stages.
- Tile pyramid storage exceeding original image storage.
- Most stored data has never been accessed.

**Phase to address:**
Phase 1 (Pipeline Foundation). Storage architecture decisions made early have compound cost effects.

---

### Pitfall 6: Knowledge Graph Schema Lock-In Before Understanding the Data

**What goes wrong:**
Designing the knowledge graph ontology before processing real data leads to a schema that does not match astronomical reality. Common mistakes: assuming clean hierarchical relationships (galaxy -> star system -> star -> planet) when real data is messy (unresolved blends, uncertain classifications, objects that change classification with better data), failing to handle the fact that the same physical object has different identifiers in different catalogs (M31 = NGC 224 = UGC 443 = PGC 2557), and not accounting for uncertain or probabilistic classifications ("70% likely elliptical galaxy, 30% likely lenticular").

**Why it happens:**
- Developers design the ontology from textbook astronomy rather than from the actual data they will process.
- Graph schemas are designed around display needs (clean drill-down navigation) rather than data reality (uncertain, multi-valued, evolving).
- Identity resolution across catalogs is treated as a lookup table rather than an ongoing probabilistic process.
- Classification is treated as a discrete label rather than a probability distribution.

**How to avoid:**
1. Process a representative data subset through the full pipeline BEFORE designing the graph schema.
2. Model classifications as probability distributions, not labels: `{type: "elliptical", confidence: 0.7}` not `{type: "elliptical"}`.
3. Implement identity resolution as a first-class entity: create "canonical source" nodes that link to all catalog identifiers via "same_as" edges, with a confidence score.
4. Use a flexible property graph model (Neo4j) rather than a rigid RDF triple store -- properties can be added without schema migration.
5. Version the ontology and support schema evolution -- classifications will change as better data arrives.

**Warning signs:**
- Many objects do not fit cleanly into the hierarchy.
- Frequent schema migrations required as new data types are ingested.
- Same physical object duplicated across multiple graph nodes.
- UI shows "Unknown" classification for > 30% of objects.

**Phase to address:**
Phase 3 (Knowledge Graph). But deliberately defer final schema decisions until Phase 2 results (actual classified data) are available.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded image scaling (e.g., fixed asinh stretch parameters) | Quick visualization | Fails on data with different dynamic range; SAM gets inconsistent input | POC only, with documented parameters |
| Single-threaded FITS processing | Simpler code, easier debugging | 100x slower at scale; cannot process nightly Rubin batches | POC with < 10 images |
| Storing segmentation masks as full-resolution bitmaps | Simple to implement | 1:1 storage overhead with source image; 10TB images = 10TB masks | Never -- use run-length encoding or polygon contours from the start |
| Fixed cross-match radius for all catalogs | Simple implementation | Systematic errors in crowded/sparse fields; false match rates vary by 10x | Never -- at minimum use catalog-specific radii |
| Loading entire catalog tables into memory for matching | Fast development | Crashes at > 10M sources; Gaia alone has 1.8 billion | POC with single-field catalogs only |
| Monolithic pipeline script (ingest -> segment -> classify -> store) | Fast to build | Cannot restart from failure point; wastes compute reprocessing completed steps | First prototype only; refactor before Phase 2 |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| MAST API (JWST data) | Querying all products for a large program at once; query times out at ~20K products | Batch queries by observation ID; use `Nobs_per_batch` pattern; use async curl downloads for bulk retrieval |
| MAST API (downloads) | Using synchronous portal download for large datasets | Use asynchronous retrieval (curl scripts) which has no volume limits and supports resume on interruption |
| Simbad/NED/SDSS APIs | Hammering the API with per-source queries (one HTTP request per detected object) | Batch queries using cone search or TAP/ADQL; cache responses; respect rate limits (Simbad: 6 queries/sec) |
| astropy FITS reading | Opening files without `memmap=True` then wondering why 50GB FITS kills the process | Always use `memmap=True`; use `section` for partial reads; use `do_not_scale_image_data=True` when only reading headers |
| astropy WCS | Ignoring `FITSFixedWarning` about non-standard WCS keywords | Always call `wcs.fix()` after construction; log and investigate warnings rather than suppressing them |
| Neo4j bulk import | Using Cypher `CREATE` statements in a loop for millions of nodes | Use `neo4j-admin database import` for initial bulk load; use `UNWIND` with batched transactions for incremental updates |
| Tile pyramid generation | Converting full FITS to PNG tiles in a single process | Use STIFF or FitsMap for FITS-to-tile conversion; parallelize by zoom level; generate lazily |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full FITS arrays for header-only operations | 30-second delay to read a file's metadata | Use `astropy.io.fits.getheader()` or open with `lazy_load_hdus=True` | Any image > 1GB |
| Unindexed spatial queries on the knowledge graph | Object lookups by sky position take seconds instead of milliseconds | Use spatial indexing (HEALPix tessellation for sky coordinates, Neo4j spatial index) | > 100K nodes |
| Serving raw FITS tiles to the browser | Multi-second tile load times; browser memory exhaustion | Pre-render to JPEG/WebP tiles at appropriate bit depth; serve via CDN | Any interactive use |
| Frontend rendering full catalog overlays | Browser freezes when displaying 100K+ source markers on the map | Use WebGL point rendering (deck.gl), server-side clustering, or LOD (level-of-detail) filtering | > 10K visible sources |
| N+1 graph queries for object detail pages | Each page load triggers dozens of individual Cypher queries | Use graph query patterns that fetch the object and its neighborhood in a single traversal | > 1K concurrent users |
| Re-processing unchanged data on pipeline reruns | Hours wasted reprocessing already-completed tiles | Implement content-addressed caching (hash of input tile -> skip if output exists) | Any production run |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing MAST API tokens in code or config files committed to git | Token leaked in public repo; unauthorized data access | Use environment variables or secrets manager; add `*.env` to `.gitignore` |
| Serving user-uploaded FITS files without validation | Malformed FITS files could exploit buffer overflows in processing libraries | Validate FITS structure before processing; run processing in sandboxed containers |
| Exposing Neo4j Bolt protocol directly to the internet | Direct database access; data exfiltration or deletion | Place Neo4j behind the API layer; never expose port 7687 publicly |
| No rate limiting on the tile server API | DDoS via deep-zoom tile requests; cloud cost spike | Implement rate limiting and request throttling; use CDN with caching |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing raw FITS pixel values without stretch/colormap | Images appear black or washed out; users think the data is broken | Apply astronomical visualization stretches (asinh, log, sqrt) with sensible defaults; let users adjust |
| Deep-zoom loads all tile levels eagerly | Initial page load takes 30+ seconds for large images | Load only visible tiles at current zoom level; progressive loading with blur-up placeholders |
| Knowledge graph navigation dumps entire graph on screen | Incomprehensible hairball of nodes and edges | Show only immediate neighborhood (1-2 hops); progressive disclosure; faceted filtering |
| Search returns raw catalog identifiers (e.g., "2MASS J04414489+2301513") | Meaningless to non-astronomers; poor discoverability | Show common names when available (e.g., "T Tauri"); show thumbnail and classification alongside identifiers |
| Object detail pages show only catalog data, no visual context | Users cannot connect data to what they see in images | Always show the source image cutout centered on the object with the segmentation mask overlaid |
| No loading states during pipeline processing | Users think the system is broken during long operations | Show progress indicators for tile generation, segmentation, and classification with estimated completion times |

## "Looks Done But Isn't" Checklist

- [ ] **FITS ingestion:** Often missing handling of multi-extension FITS (MEF) files -- verify the pipeline reads all HDU extensions, not just the primary
- [ ] **WCS extraction:** Often missing SIP distortion correction -- verify `SIP_A_ORDER` / `SIP_B_ORDER` keywords are being used when present
- [ ] **Tile pyramid:** Often missing overlap between tiles -- verify that objects near tile boundaries are not clipped or duplicated
- [ ] **SAM segmentation:** Often missing validation against known sources -- verify that a reference field with known objects produces correct detections
- [ ] **Cross-matching:** Often missing proper motion correction -- verify epoch propagation for Gaia sources when matching against JWST (epoch ~2023-2025 vs Gaia J2016.0)
- [ ] **Cross-matching:** Often missing magnitude/flux consistency check -- verify matched sources have compatible brightness across bands
- [ ] **Knowledge graph:** Often missing identity resolution -- verify that M31, NGC 224, and UGC 443 resolve to the same canonical node
- [ ] **Knowledge graph:** Often missing spatial indexing -- verify that "find all objects within 1 arcminute of RA=150.0, Dec=2.0" completes in < 100ms
- [ ] **Tile viewer:** Often missing coordinate overlay -- verify that clicking a point in the viewer shows the correct RA/Dec, not just pixel coordinates
- [ ] **Tile viewer:** Often missing scale bar -- verify the viewer shows angular scale (arcminutes/arcseconds) at current zoom level
- [ ] **Classification:** Often missing confidence scores -- verify that every classification carries a probability, not just a label

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SAM segmentation garbage | MEDIUM | Revert to traditional detection (SEP/photutils) as interim; collect SAM failure cases as fine-tuning dataset; retrain on domain data |
| WCS corruption in stored data | HIGH | Re-extract WCS from original FITS headers; re-run astrometry.net on affected images; recompute all cross-matches for affected fields |
| Memory exhaustion at scale | MEDIUM | Retrofit tile-based processing; requires refactoring but not rewriting -- add tile iterator wrapper around existing per-image functions |
| False cross-match associations | HIGH | Must re-run all cross-matching with corrected algorithm; all downstream classifications and graph relationships derived from bad matches must be invalidated |
| Storage cost overrun | LOW | Audit storage; delete intermediate products; move cold data to Glacier; implement lazy tile generation. Immediate savings. |
| Knowledge graph schema rewrite | HIGH | Export all data; redesign schema; write migration scripts; re-import. Neo4j has no ALTER SCHEMA -- must rebuild. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SAM domain mismatch | Phase 1: Pipeline Foundation | Run SAM on 5 well-studied JWST fields; compare detection catalog against Simbad; require > 80% recall for sources brighter than 25th magnitude |
| WCS coordinate errors | Phase 1: Pipeline Foundation | For every ingested image, overlay detected sources on DSS/2MASS reference image; visual spot-check + automated RMS residual < 0.5" |
| Memory exhaustion on large images | Phase 1: Pipeline Foundation | Process the largest available JWST mosaic (COSMOS-Web, JADES) end-to-end on a machine with 32GB RAM; must complete without OOM |
| False cross-match associations | Phase 2: Classification & Cross-Matching | Measure false-match rate using synthetic injection: add fake sources at known positions and verify match accuracy > 95% |
| Storage cost explosion | Phase 1: Pipeline Foundation | Set monthly budget cap; implement storage monitoring dashboard; review storage breakdown weekly for first 3 months |
| Knowledge graph schema lock-in | Phase 3: Knowledge Graph | Process 10 diverse fields through Phase 2 before finalizing schema; schema must handle edge cases (unresolved blends, uncertain classifications, multi-catalog identities) without modification |
| MAST API integration failures | Phase 1: Pipeline Foundation | Implement retry logic with exponential backoff; test bulk download of 1000+ products; verify resume-on-failure works |
| Frontend performance with large catalogs | Phase 4: Interactive Explorer | Load test with 1M sources in a single view; verify < 2 second initial render; verify smooth 60fps pan/zoom with WebGL rendering |
| Tile pyramid coordinate preservation | Phase 1: Pipeline Foundation | Click 10 random points in the tile viewer; verify RA/Dec matches the original FITS WCS to within 0.1" |

## Sources

- [Astropy FITS documentation - memory mapping and large files](https://docs.astropy.org/en/stable/io/fits/index.html)
- [Astropy WCS documentation](https://docs.astropy.org/en/stable/wcs/index.html)
- [Astropy FITS image data handling](https://docs.astropy.org/en/stable/io/fits/usage/image.html)
- [Working with large FITS files tutorial](https://learn.astropy.org/tutorials/FITS-large.html)
- [MAST API access for JWST](https://jwst-docs.stsci.edu/accessing-jwst-data/mast-api-access)
- [JWST data retrieval documentation](https://jwst-docs.stsci.edu/accessing-jwst-data)
- [Gaia DR2 cross-match algorithms and results (A&A)](https://www.aanda.org/articles/aa/full_html/2019/01/aa34142-18/aa34142-18.html)
- [Gaia DR1 cross-match algorithm and results (A&A)](https://www.aanda.org/articles/aa/full_html/2017/11/aa30965-17/aa30965-17.html)
- [Probabilistic multi-catalogue positional cross-match (A&A)](https://www.aanda.org/articles/aa/full_html/2017/01/aa29219-16/aa29219-16.html)
- [Overcoming proper motion in catalogue cross-matching (RAS TI)](https://academic.oup.com/rasti/article/2/1/1/6960586)
- [SAM for remote sensing applications (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S1569843223003643)
- [SAM2 repository and fine-tuning](https://github.com/facebookresearch/sam2)
- [SAMRefiner for noisy inputs](https://arxiv.org/html/2502.06756v1)
- [FitsMap: lightweight FITS visualization tool](https://arxiv.org/pdf/2201.12308v1)
- [Rubin Observatory data deluge preparation (SLAC)](https://www6.slac.stanford.edu/news/2025-05-15-ready-set-process-preparing-rubin-observatorys-data-deluge)
- [Cloud computing for observational astronomy (Astrobites)](https://astrobites.org/2023/01/26/cloud-computing-astro/)
- [How will astronomy archives survive the data tsunami? (ACM)](https://queue.acm.org/detail.cfm?id=2047483)
- [Galaxy morphology classification with imbalanced data (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S2213133721000469)
- [Conditional diffusion model for galaxy augmentation](https://arxiv.org/html/2506.16233)
- [Neo4j scaling to billions of nodes](https://neo4j.com/press-releases/neo4j-scales-trillion-plus-relationship-graph/)
- [Knowledge Graph in Astronomical Research with LLMs](https://openreview.net/pdf?id=V2jHazRjHn)
- [FITS metadata inconsistency in telescope data](https://github.com/DaveStrickland/AstroPhotography/issues/1)
- [Astropy memory mapping pull request #7926](https://github.com/astropy/astropy/pull/7926)

---
*Pitfalls research for: Astronomical data pipeline + interactive galactic encyclopedia*
*Researched: 2026-02-21*
