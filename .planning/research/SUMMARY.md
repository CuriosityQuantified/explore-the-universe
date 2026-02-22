# Project Research Summary

**Project:** Explore the Universe
**Domain:** Astronomical data pipeline + interactive galactic encyclopedia
**Researched:** 2026-02-21
**Confidence:** MEDIUM-HIGH

## Executive Summary

Explore the Universe is an automated astronomical data pipeline that ingests JWST and Rubin Observatory FITS imagery, segments every distinguishable object using Meta's SAM 2.1, classifies objects via catalog cross-matching and ML, and presents everything through an interactive encyclopedia with deep-zoom viewing, search, and knowledge graph navigation. The expert approach for this type of system is a staged pipeline architecture: ingest FITS from archive APIs, tile into multi-resolution pyramids for web viewing and SAM processing, run segmentation, cross-match against existing catalogs (SIMBAD, NED, SDSS, Gaia), classify unknowns with ML, and store results in a dual-database system (PostgreSQL for structured/spatial queries, Neo4j for graph traversal). The frontend is a Next.js app with an OpenSeadragon deep-zoom viewer, search/browse interface, object detail pages, and force-directed graph explorer.

The recommended approach is to build the pipeline end-to-end on a small curated JWST dataset first, validating each stage before expanding scope. The critical path is infrastructure setup, FITS ingestion, tile generation, and sky viewer -- this delivers something visible and testable fastest. SAM segmentation should be validated early (zero-shot first, fine-tune only after measuring failures) because every downstream feature depends on segmentation quality. The dual-database strategy (PostgreSQL + Neo4j) is justified but Neo4j should be deferred until classified objects exist to populate it -- use PostgreSQL with JSONB for early relationship modeling.

The highest risk is SAM's performance on astronomical images. SAM was trained exclusively on natural photographs and astronomical imagery differs fundamentally in dynamic range, noise characteristics, and object morphology. Expect poor out-of-box results on nebulae, faint galaxies, and crowded fields. Mitigation: use traditional source detection (SEP/photutils) as baseline and SAM prompt source, validate against known catalog positions, and budget significant time for domain adaptation. Secondary risks are WCS coordinate errors silently corrupting cross-matching, memory exhaustion on trillion-pixel images (mandate tile-based processing from day one), and storage costs escalating before funding arrives.

## Key Findings

### Recommended Stack

The stack splits into a Python backend/pipeline and a TypeScript frontend. The astronomy/ML ecosystem is mature and well-defined: Astropy (7.2.0) for FITS I/O and WCS, astroquery (0.4.11) for catalog APIs, pyvips (3.1.1) for memory-efficient FITS-to-tile conversion, SAM 2.1 with PyTorch 2.10 for segmentation, and timm/scikit-learn for classification. The pipeline uses Celery + Redis for task orchestration. The API is FastAPI with PostgreSQL (healpix-alchemy for celestial spatial indexing) and Neo4j for the knowledge graph. MinIO provides S3-compatible object storage at zero cost for the POC.

**Core technologies:**
- **Astropy + astroquery**: FITS parsing, WCS handling, catalog queries -- the non-negotiable foundation of any astronomical computing project
- **pyvips**: FITS-to-DeepZoom tile generation with constant memory usage -- critical for trillion-pixel images where Pillow will OOM
- **SAM 2.1 + PyTorch 2.10**: Zero-shot segmentation with fine-tuning path -- project's primary differentiator but highest technical risk
- **PostgreSQL + healpix-alchemy**: Relational storage with HEALPix spatial indexing -- the IVOA standard for celestial coordinate queries
- **Neo4j Community**: Knowledge graph for hierarchical relationships and catalog cross-references -- deferred until data exists to populate it
- **Celery + Redis**: Pipeline task orchestration with retry, chaining, and monitoring -- simpler than Prefect/Airflow for POC
- **OpenSeadragon**: Deep-zoom tile viewer supporting DZI format -- purpose-built for this use case, proven in astronomy
- **Next.js 16 + React 19 + Tailwind 4**: Frontend framework -- project constraint, well-suited for data-heavy server components
- **react-force-graph**: WebGL-powered graph visualization for knowledge graph exploration

**Critical version constraints:** SAM 2.1 requires PyTorch >= 2.5.1 and Python >= 3.10. Astropy 7.x requires NumPy >= 1.24. healpix-alchemy requires PostgreSQL >= 14. Next.js 16 requires React 19.

### Expected Features

**Must have (table stakes):**
- Zoomable sky map / deep-zoom image viewer (every astronomy tool has this)
- FITS file ingestion and processing (FITS is the universal format)
- WCS coordinate system support (fundamental to astronomy)
- Catalog cross-matching against SIMBAD/NED/SDSS (users expect known objects identified)
- Object search by name, coordinates, and type
- Individual object detail pages with properties, imagery, and catalog links
- Data provenance and metadata display (telescope, instrument, observation ID)

**Should have (differentiators -- no competitor has these):**
- Automated SAM-based object segmentation (primary differentiator)
- Knowledge graph with spatial hierarchy (galaxy -> system -> star)
- Visual knowledge graph explorer
- ML classification for unknown objects
- Anomaly detection and novel object flagging
- Unified end-to-end pipeline (image -> segmentation -> classification -> encyclopedia)

**Defer (v2+):**
- AI natural language querying (requires mature knowledge graph first)
- Temporal change tracking (requires repeated observations and object identity persistence)
- Statistical analysis dashboard (requires large classified dataset)
- Citizen feedback mechanism (requires users)

### Architecture Approach

The system is a four-layer architecture: Data Ingestion (archive downloaders + Celery queue), Processing (pipeline DAG: tile -> segment -> cross-match -> classify), Storage (MinIO for blobs, PostgreSQL for metadata/spatial, Neo4j for graph), and Presentation (FastAPI REST/WebSocket API + Next.js frontend). The pipeline and API are separate deployment units sharing only databases and object storage, enabling independent scaling and parallel development.

**Major components:**
1. **Pipeline Orchestrator (Celery DAG)** -- Chains processing stages per observation: download -> validate -> tile -> segment -> cross-match -> classify -> store. Each stage is an independent retryable task.
2. **Tiler** -- Converts FITS to multi-resolution tile pyramids (HiPS/DZI) using pyvips for streaming processing. Also produces overlapping 1024x1024 cutouts for SAM input.
3. **SAM Segmenter** -- Runs automatic mask generation on tiles, merges boundary-spanning masks via IoU matching, extracts per-object polygons and bounding boxes.
4. **Catalog Cross-Matcher** -- Converts pixel coordinates to RA/Dec via WCS, queries SIMBAD/NED/SDSS/Gaia with batch cone searches, stores match candidates with probabilities.
5. **Dual Database (PostgreSQL + Neo4j)** -- PostgreSQL is source of truth for object metadata and spatial queries. Neo4j stores relationship graph, populated from PostgreSQL via sync process. Shared UUID links objects across databases.
6. **FastAPI API** -- REST endpoints for objects, search, tiles, graph traversal, pipeline status. WebSocket for real-time pipeline progress.
7. **Next.js Frontend** -- Sky viewer (OpenSeadragon), search/browse, object detail pages, graph explorer (react-force-graph), pipeline dashboard.

### Critical Pitfalls

1. **SAM produces garbage on astronomical images** -- SAM's training data has zero overlap with astronomy. Expect oversegmentation of galaxies, missed diffuse structures, noise/artifact detection. Mitigate by using traditional detection (SEP) as prompt source, properly scaling FITS to 8-bit RGB with asinh stretch, and validating against known catalogs before trusting output.

2. **WCS coordinate errors silently corrupt cross-matching** -- Wrong projections, missing SIP distortion, axis ordering confusion (NumPy y,x vs FITS x,y) produce subtle positional errors. Cross-matching then associates wrong catalog entries with detections. Mitigate by validating every WCS against reference catalog positions, computing RMS residuals, and running astrometry.net on images without reliable WCS.

3. **Memory exhaustion on trillion-pixel FITS images** -- Loading full images at 32-bit float requires terabytes of RAM. Even with memmap, operations that materialize arrays (np.std, np.median) will OOM. Mitigate by designing for tile-based processing from day one -- never operate on full images, use ImageHDU.section for partial reads, use streaming statistics algorithms.

4. **Catalog cross-matching produces systematic false associations** -- Naive nearest-neighbor matching has 10-40% false match rates in crowded fields due to source density variation, epoch differences (proper motion), and multi-resolution source definitions. Mitigate with probabilistic matching, catalog-specific match radii, proper motion correction, and photometric consistency checks.

5. **Knowledge graph schema lock-in before understanding the data** -- Designing the ontology from textbook astronomy rather than actual pipeline output leads to schemas that do not handle messy reality (unresolved blends, uncertain classifications, multi-catalog identities). Mitigate by processing real data through the pipeline before finalizing the schema, modeling classifications as probability distributions, and implementing identity resolution as a first-class concept.

6. **Storage costs explode before funding** -- Raw FITS + tiles + masks for even a modest JWST subset reaches 5-10 TB quickly. Mitigate with tiered storage (hot tiles, cold FITS), lazy tile generation, lossy compression for display tiles, and re-downloading from MAST rather than hoarding raw data.

## Implications for Roadmap

Based on research, the project naturally splits into 6 phases ordered by hard dependencies. The critical path runs through infrastructure -> ingestion -> tiling -> sky viewer, with SAM segmentation running in parallel.

### Phase 1: Foundation and Infrastructure
**Rationale:** Every other phase depends on databases, object storage, and the basic API skeleton. Docker Compose orchestrates Neo4j, PostgreSQL, Redis, and MinIO locally.
**Delivers:** Running infrastructure, PostgreSQL schema with Alembic migrations, MinIO buckets, FastAPI skeleton with health checks, project structure (pipeline/, api/, web/ separation).
**Addresses:** Data provenance metadata schema, pipeline state tracking.
**Avoids:** Monolithic pipeline without state tracking (anti-pattern), storing tiles in database.
**Features from FEATURES.md:** None directly user-facing, but enables all P1 features.

### Phase 2: Data Ingestion and Tiling Pipeline
**Rationale:** Cannot view, segment, or classify anything without ingested and tiled data. FITS ingestion and tile generation are the first two pipeline stages and produce the inputs for both the sky viewer and SAM.
**Delivers:** MAST downloader (astroquery), FITS metadata/WCS extraction, tile pyramid generation (pyvips -> DZI), Celery task chain for download -> validate -> tile, storage of raw FITS and tiles in MinIO.
**Addresses:** FITS ingestion, WCS coordinate extraction, image tiling.
**Avoids:** Memory exhaustion (tile-based processing from day one), WCS errors (validation built into ingestion).
**Features from FEATURES.md:** FITS file support, WCS coordinate support, data provenance.

### Phase 3: Sky Viewer and Basic Frontend
**Rationale:** Provides the first visible, testable deliverable. Once tiles exist, the frontend can render them. This validates the tile format and serving approach before investing in segmentation.
**Delivers:** OpenSeadragon tile viewer in Next.js, coordinate overlay on hover/click, tile serving via FastAPI or direct MinIO URLs, basic navigation (zoom, pan), Next.js app shell with routing.
**Addresses:** Zoomable sky map viewer, coordinate system support.
**Avoids:** Eager tile loading (load only visible tiles at current zoom).
**Features from FEATURES.md:** Zoomable sky map, coordinate display.

### Phase 4: Segmentation, Cross-Matching, and Classification
**Rationale:** This is the core differentiator phase. SAM segmentation, catalog cross-matching, and ML classification form the heart of the pipeline. These must work before objects can be browsed or explored. SAM validation is critical here -- run zero-shot first, measure quality, then decide on fine-tuning.
**Delivers:** SAM integration with overlapping tile segmentation + mask merging, SEP/photutils baseline detection as SAM prompt source, WCS pixel-to-sky coordinate transform per object, batch catalog cross-matching (SIMBAD, NED, SDSS, Gaia), ML classifier for unmatched objects (timm ConvNeXt or scikit-learn Random Forest), object records in PostgreSQL with PostGIS spatial indexing, segmentation quality validation against known catalogs.
**Addresses:** SAM segmentation pipeline, catalog cross-matching, ML classification, anomaly flagging (basic).
**Avoids:** SAM domain mismatch (validate before trusting), false cross-match associations (probabilistic matching), schema lock-in (schema informed by real pipeline output).
**Features from FEATURES.md:** Automated SAM segmentation, catalog cross-matching, object classification.

### Phase 5: Encyclopedia Frontend
**Rationale:** With objects classified and stored, the encyclopedia experience can be built. Search, browse, detail pages, and the knowledge graph all depend on having a populated object catalog.
**Delivers:** Object search (name via SIMBAD resolution, coordinates via cone search, type filter), object detail pages (cutout, mask overlay, catalog matches, properties), knowledge graph in Neo4j (spatial hierarchy, catalog cross-references, identity resolution), visual graph explorer (react-force-graph), multi-wavelength layer toggle (if multiple surveys tiled), pipeline status dashboard (Flower + custom UI), data export (FITS cutouts, CSV).
**Addresses:** Object search, object detail pages, knowledge graph, graph explorer, data export.
**Avoids:** Knowledge graph schema lock-in (schema designed from Phase 4 output), full graph dump (progressive disclosure, 1-2 hops only), raw identifiers in search results (show common names + thumbnails).
**Features from FEATURES.md:** Object search, object detail pages, knowledge graph, visual graph explorer, multi-wavelength layers, data export, pipeline dashboard.

### Phase 6: Intelligence Layer
**Rationale:** Anomaly detection, temporal analysis, and AI querying all require a mature, populated knowledge graph and a stable pipeline. These features build on everything prior and deliver the "discovery" layer.
**Delivers:** Anomaly detection (Isolation Forests on object feature vectors), AI natural language querying (RAG over knowledge graph + catalog data), structured smart query builder, temporal change tracking (when Rubin data available), statistical analysis dashboard.
**Addresses:** Advanced discovery and analysis capabilities.
**Avoids:** Building AI features before the data foundation exists.
**Features from FEATURES.md:** Anomaly detection, AI querying, smart query builder, temporal tracking, statistical dashboard.

### Phase Ordering Rationale

- **Phases 1-3 deliver a viewable product with zero ML risk.** Infrastructure, ingestion, tiling, and the sky viewer use well-understood, high-confidence technologies. This is the fastest path to something testable.
- **Phase 4 isolates the highest-risk work (SAM + cross-matching).** By deferring segmentation until the pipeline infrastructure exists, SAM quality can be evaluated in context -- cross-matching validates whether SAM found real objects.
- **Phase 5 depends on Phase 4 output.** The encyclopedia requires classified objects. The knowledge graph schema should be designed from actual pipeline data, not theoretical ontologies.
- **Phase 6 requires data density.** Anomaly detection needs baseline distributions. AI querying needs a queryable graph. Temporal tracking needs repeated observations. All require the pipeline to have processed substantial data.
- **The pipeline (Phases 1-2, 4) and frontend (Phases 3, 5) can be developed in parallel** because they share only databases and object storage. Phase 3 can start as soon as tiles exist, while Phase 4 segmentation work continues.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Tiling):** HiPS vs DZI tile format decision needs investigation. Research suggests pyvips DZI for simplicity, but HiPS is the IVOA standard with broader ecosystem support (Aladin Lite). The choice affects the viewer component in Phase 3.
- **Phase 4 (SAM Segmentation):** Highest uncertainty in the project. SAM's astronomical performance is uncharted. Need to research: optimal image preprocessing (asinh stretch parameters, band mapping to RGB channels), SAM model size vs quality tradeoffs (sam2_hiera_tiny vs larger), tile overlap strategy for mask merging, and whether SAM3-Adapter or fine-tuning is the better domain adaptation path.
- **Phase 4 (Cross-Matching):** Probabilistic cross-matching algorithms are well-documented in astronomy literature but implementing them correctly is non-trivial. Research the astropy matching utilities vs dedicated tools like STILTS/TOPCAT for the implementation approach.
- **Phase 5 (Knowledge Graph Schema):** Must be informed by Phase 4 output. Research Neo4j modeling patterns for astronomical hierarchies, identity resolution strategies, and how to handle uncertain/probabilistic classifications in a property graph.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure):** Docker Compose + PostgreSQL + Redis + MinIO is fully standard. FastAPI skeleton is well-documented.
- **Phase 3 (Sky Viewer):** OpenSeadragon integration with React is well-documented. Tile serving is a solved problem.
- **Phase 5 (Search/Browse/Detail Pages):** Standard CRUD + full-text search patterns in FastAPI + PostgreSQL + Next.js.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core technologies verified via official docs and PyPI. Versions confirmed compatible. Only SAM-on-astronomy is uncertain. |
| Features | MEDIUM-HIGH | Feature landscape well-mapped against 10+ existing platforms. Clear differentiation surface identified. MVP definition is sound. |
| Architecture | MEDIUM-HIGH | Pipeline-as-DAG and dual-database patterns are well-established. Build order dependencies are clear. Scaling path is documented. |
| Pitfalls | HIGH | Verified across official documentation, published research papers, and established astronomical computing community knowledge. Recovery strategies documented. |

**Overall confidence:** MEDIUM-HIGH

The stack, architecture, and pitfalls are well-researched with high-confidence sources. The primary uncertainty is SAM's performance on astronomical data -- this is genuinely uncharted territory that can only be resolved through experimentation in Phase 4.

### Gaps to Address

- **SAM astronomical performance:** No published benchmark exists for SAM 2.1 on JWST deep field imagery. The 2025 A&A paper validated SAM for galaxy size estimation in Euclid images (a narrower task than full segmentation). Must be validated empirically in Phase 4.
- **HiPS vs DZI tile format:** Research identified both as viable but did not resolve which is better for this project. HiPS has ecosystem advantages (Aladin Lite, IVOA standard); DZI has simplicity advantages (pyvips native output, OpenSeadragon native input). Resolve during Phase 2 planning.
- **healpix-alchemy maturity:** Identified as MEDIUM confidence. It is the right approach for celestial spatial indexing but may have limited documentation and edge cases. Validate during Phase 1 implementation.
- **Neo4j celestial coordinate handling:** Neo4j Spatial only supports WGS-84 (terrestrial). The workaround (spatial queries in PostgreSQL, relationship traversal in Neo4j) is architecturally sound but adds sync complexity. Monitor whether this dual-query pattern becomes a UX bottleneck.
- **SAM fine-tuning data:** If SAM zero-shot fails (likely for diffuse structures), fine-tuning requires annotated astronomical segmentation masks. No public dataset exists for this. Budget time for manual annotation of 50-200 cutouts from JWST deep fields.
- **Rubin Science Platform API stability:** Rubin data access APIs may still be evolving. Phase 2 should focus on JWST/MAST (stable, well-documented) and treat Rubin as a future data source.

## Sources

### Primary (HIGH confidence)
- [Astropy 7.2.0 docs](https://docs.astropy.org/en/stable/) -- FITS I/O, WCS, memory mapping, large file handling
- [astroquery 0.4.11 docs](https://astroquery.readthedocs.io/en/stable/) -- MAST, SIMBAD, NED catalog queries
- [SAM 2 GitHub](https://github.com/facebookresearch/sam2) -- Model architecture, installation, requirements
- [MAST API documentation](https://jwst-docs.stsci.edu/accessing-jwst-data/mast-api-access) -- JWST data access patterns
- [OpenSeadragon 5.0.1](https://openseadragon.github.io/) -- Deep zoom viewer capabilities
- [IVOA HiPS Recommendation](http://www.ivoa.net/documents/HiPS/) -- Tile pyramid standard
- [Neo4j Community Edition](https://neo4j.com/licensing/) -- Graph database capabilities and limitations
- [Gaia cross-match papers (A&A 2017, 2019)](https://www.aanda.org/articles/aa/full_html/2019/01/aa34142-18/aa34142-18.html) -- Cross-matching algorithms and false match rates

### Secondary (MEDIUM confidence)
- [SAM for galaxy segmentation (2025 A&A)](https://www.aanda.org/articles/aa/full_html/2025/01/aa52482-24/aa52482-24.html) -- SAM validated for galaxy sizes in Euclid data
- [healpix-alchemy (GitHub)](https://github.com/skyportal/healpix-alchemy) -- HEALPix spatial indexing for PostgreSQL
- [AstroSage-Llama (arXiv 2024)](https://arxiv.org/abs/2411.09012) -- Astronomy LLM achieving GPT-4o performance
- [Knowledge graphs in astronomy (arXiv 2024)](https://arxiv.org/html/2406.01391v2) -- LLM-driven knowledge graph construction
- [FitsMap (arXiv 2022)](https://arxiv.org/pdf/2201.12308v1) -- FITS-to-tile architecture reference

### Tertiary (LOW confidence)
- SAM fine-tuning for astronomical domain adaptation -- approach extrapolated from remote sensing applications, not validated on astronomical data
- Neo4j for astronomical hierarchies -- conceptually sound but no published reference implementation
- Rubin Science Platform API -- still evolving, plan for changes

---
*Research completed: 2026-02-21*
*Ready for roadmap: yes*
