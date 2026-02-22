# Roadmap: Explore the Universe

## Overview

This roadmap delivers a galactic encyclopedia that ingests JWST imagery, segments every distinguishable object with SAM, classifies them against existing catalogs, and presents everything through an interactive explorer. The critical path runs through infrastructure, ingestion, tiling, and the sky viewer -- delivering something visible and testable before investing in the highest-risk work (SAM segmentation). The pipeline and frontend develop in parallel where possible, with classification populating the data that powers search, knowledge graph, and AI-assisted research.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Infrastructure** - Docker Compose services, database schemas, pipeline skeleton, and API framework
- [x] **Phase 2: Data Ingestion & Tiling** - FITS download from MAST, WCS extraction, multi-resolution tile pyramid generation
- [ ] **Phase 3: Sky Viewer** - Deep-zoom tile viewer with pan, zoom, and coordinate overlay
- [ ] **Phase 4: Segmentation** - SAM-based object detection with tile boundary merging and per-object cutouts
- [ ] **Phase 5: Classification & Cross-Matching** - Catalog cross-matching, ML classification for unknowns, anomaly flagging
- [ ] **Phase 6: Search, Browse & Object Pages** - Object search, filtering, detail pages, data export, pipeline dashboard
- [ ] **Phase 7: Knowledge Graph** - Neo4j spatial hierarchy, catalog linking, property queries, graph navigation
- [ ] **Phase 8: Intelligence Layer** - AI conversational queries, structured query builder, AI-linked visualizations

## Phase Details

### Phase 1: Foundation & Infrastructure
**Goal**: All backend services are running and the pipeline framework can accept and track work
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. Docker Compose brings up PostgreSQL, Redis, MinIO, and Neo4j with a single command
  2. Celery worker processes a no-op test task through the full chain (enqueue, execute, report status)
  3. FastAPI health endpoint confirms all service connections are live
  4. Raw file upload to MinIO succeeds and metadata record appears in PostgreSQL
**Plans**: Complete

Plans:
- [x] 01-01: Foundation infrastructure (design + implementation, 10 tasks, 13 commits)

UAT: 6/6 passed, 0 issues

### Phase 2: Data Ingestion & Tiling
**Goal**: A JWST observation goes in by ID and comes out as validated, tiled imagery ready for viewing and processing
**Depends on**: Phase 1
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04, INGEST-05
**Success Criteria** (what must be TRUE):
  1. User triggers ingestion of a JWST observation by ID and the system downloads FITS files from MAST
  2. System extracts WCS coordinates from FITS headers and validates them against reference positions
  3. Ingested images are tiled into multi-resolution pyramids viewable at any zoom level
  4. Provenance metadata (telescope, instrument, filter, exposure time, observation ID) is stored and queryable
  5. A trillion-pixel-class FITS image processes through tiling without memory exhaustion
**Plans**: Complete

Plans:
- [x] 02-01: Shared S3 client, astronomy dependencies, MAST download task (2 tasks, 2 commits)
- [x] 02-02: WCS validation and DZI tile pyramid generation (2 tasks, 2 commits)
- [x] 02-03: Pipeline orchestration, API endpoint, integration tests (2 tasks, 2 commits)

### Phase 3: Sky Viewer
**Goal**: Users can visually explore ingested imagery by panning and zooming like a map, with sky coordinates displayed
**Depends on**: Phase 2
**Requirements**: BROWSE-01, BROWSE-02
**Success Criteria** (what must be TRUE):
  1. User can pan and zoom smoothly across an ingested JWST image from full field down to individual pixel scale
  2. User sees RA/Dec sky coordinates update on hover or click within the viewer
  3. Tile loading is lazy -- only visible tiles at the current zoom level are fetched
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md -- Backend APIs: tile proxy, WCS extraction, observation detail + TypeScript types/client
- [ ] 03-02-PLAN.md -- Core viewer: OpenSeadragon deep-zoom, WCS coordinate overlay, toolbar, scale bar, dark theme
- [ ] 03-03-PLAN.md -- UI panels: observation info sidebar, image adjustments, band selector, coordinate grid + verification

### Phase 4: Segmentation
**Goal**: Every distinguishable object in an ingested image is detected, segmented, and stored with pixel-level masks and cutout images
**Depends on**: Phase 2
**Requirements**: SEG-01, SEG-02, SEG-03, SEG-04
**Success Criteria** (what must be TRUE):
  1. SAM processes tiled images and produces segmentation masks for all distinguishable objects
  2. Objects spanning tile boundaries are correctly merged into single masks
  3. Each segmented object has a cutout image and pixel-level mask stored and retrievable
  4. Traditional source detection (SEP/photutils) runs as baseline and provides prompt positions for SAM
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Classification & Cross-Matching
**Goal**: Every segmented object is identified against known catalogs or classified by ML, with truly novel objects flagged for review
**Depends on**: Phase 4
**Requirements**: CLASS-01, CLASS-02, CLASS-03, CLASS-04, CLASS-05, CLASS-06, INTEL-01
**Success Criteria** (what must be TRUE):
  1. Segmented objects are cross-matched against SIMBAD, NED, SDSS, and Gaia catalogs with match probabilities
  2. Objects not found in any catalog are classified by ML with a predicted type and confidence score
  3. Objects that do not match known categories are automatically flagged as anomalies with confidence scores
  4. Cross-match and classification results are stored per-object and retrievable via API
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD
- [ ] 05-03: TBD

### Phase 6: Search, Browse & Object Pages
**Goal**: Users can find any classified object by name, coordinates, or type, view its full detail page, and export data
**Depends on**: Phase 3, Phase 5
**Requirements**: BROWSE-03, BROWSE-04, BROWSE-05, BROWSE-06, BROWSE-07, INFRA-04
**Success Criteria** (what must be TRUE):
  1. User can search for an object by name (resolved via SIMBAD) and navigate to it
  2. User can search by sky coordinates (cone search) and see results ranked by proximity
  3. User can filter the object catalog by classification type
  4. Object detail page displays cutout image, segmentation mask overlay, catalog matches, and physical properties
  5. User can export object data as FITS cutouts, CSV, or VOTable
  6. Pipeline status dashboard shows processing progress per observation
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD

### Phase 7: Knowledge Graph
**Goal**: Objects are connected in a navigable spatial hierarchy with catalog links, enabling property-based queries and graph traversal
**Depends on**: Phase 5
**Requirements**: GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04
**Success Criteria** (what must be TRUE):
  1. Objects are stored in Neo4j with spatial hierarchy relationships (galaxy contains system contains star)
  2. Catalog cross-match entries are linked to their objects in the graph
  3. User can query objects by properties (brightness, size, spectral type, redshift, morphology) and get results
  4. User can click a galaxy and drill down through its constituent objects via the spatial hierarchy
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: Intelligence Layer
**Goal**: Users can ask natural language questions and build structured queries to discover patterns across the catalog
**Depends on**: Phase 6, Phase 7
**Requirements**: INTEL-02, INTEL-03, INTEL-04
**Success Criteria** (what must be TRUE):
  1. User can ask a natural language question about the data and receive a relevant answer via AI chat
  2. User can build structured queries with visual filters for precision analysis across the catalog
  3. AI chat responses include relevant object visualizations and links to detail pages
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8
Note: Phases 3 and 4 can execute in parallel (both depend on Phase 2, not each other).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Infrastructure | 1/1 | Complete | 2026-02-21 |
| 2. Data Ingestion & Tiling | 3/3 | Complete    | 2026-02-22 |
| 3. Sky Viewer | 0/3 | Not started | - |
| 4. Segmentation | 0/2 | Not started | - |
| 5. Classification & Cross-Matching | 0/3 | Not started | - |
| 6. Search, Browse & Object Pages | 0/3 | Not started | - |
| 7. Knowledge Graph | 0/2 | Not started | - |
| 8. Intelligence Layer | 0/2 | Not started | - |
