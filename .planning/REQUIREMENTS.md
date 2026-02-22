# Requirements: Explore the Universe

**Defined:** 2026-02-21
**Core Value:** Any astronomical image goes in, every object comes out segmented, classified, and explorable -- turning raw telescope data into a navigable, queryable encyclopedia of the universe.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Ingestion

- [x] **INGEST-01**: User can trigger ingestion of JWST observations from MAST by observation ID or program ID
- [x] **INGEST-02**: System extracts and validates WCS coordinates from FITS headers for accurate sky positioning
- [x] **INGEST-03**: System tiles ingested images into multi-resolution pyramids for web viewing and SAM processing
- [x] **INGEST-04**: System stores data provenance metadata (telescope, instrument, filter, exposure time, observation ID, program ID)
- [x] **INGEST-05**: System handles trillion-pixel FITS images via tile-based processing without memory exhaustion

### Segmentation

- [ ] **SEG-01**: System segments every distinguishable object in tiled images using SAM
- [ ] **SEG-02**: System merges segmentation masks across tile boundaries for objects that span multiple tiles
- [ ] **SEG-03**: System produces per-object cutout images and pixel-level masks
- [ ] **SEG-04**: System uses traditional source detection (SEP/photutils) as baseline and SAM prompt source

### Classification

- [ ] **CLASS-01**: System cross-matches segmented object coordinates against SIMBAD catalog
- [ ] **CLASS-02**: System cross-matches segmented object coordinates against NED catalog
- [ ] **CLASS-03**: System cross-matches segmented object coordinates against SDSS catalog
- [ ] **CLASS-04**: System cross-matches segmented object coordinates against Gaia catalog
- [ ] **CLASS-05**: System classifies objects not found in any catalog using ML classifier
- [ ] **CLASS-06**: System flags truly novel/unknown objects for human review with anomaly confidence scores

### Browsing & Visualization

- [x] **BROWSE-01**: User can pan and zoom across ingested imagery like a map, from full field down to individual objects
- [x] **BROWSE-02**: User sees sky coordinates (RA/Dec) on hover or click within the viewer
- [ ] **BROWSE-03**: User can search for objects by name (resolved via SIMBAD)
- [ ] **BROWSE-04**: User can search for objects by sky coordinates (cone search)
- [ ] **BROWSE-05**: User can filter objects by classification type
- [ ] **BROWSE-06**: User can view individual object detail pages showing cutout image, segmentation mask overlay, catalog matches, and physical properties
- [ ] **BROWSE-07**: User can export object data as FITS cutouts, CSV, or VOTable

### Knowledge Graph

- [ ] **GRAPH-01**: System stores objects in a knowledge graph with spatial hierarchy (galaxy → system → star → planet)
- [ ] **GRAPH-02**: System links objects to their cross-matched catalog entries in the graph
- [ ] **GRAPH-03**: User can query objects by properties (brightness, size, spectral type, redshift, morphology)
- [ ] **GRAPH-04**: User can navigate spatial hierarchy (click galaxy, see constituent objects)

### Intelligence & Analysis

- [ ] **INTEL-01**: System automatically flags objects that don't match known categories using anomaly detection (Isolation Forests on feature vectors)
- [ ] **INTEL-02**: User can ask natural language questions about the data via conversational AI chat interface
- [ ] **INTEL-03**: User can build structured queries with visual filters for precision analysis
- [ ] **INTEL-04**: AI chat interface returns answers with relevant object visualizations and links to detail pages

### Infrastructure

- [x] **INFRA-01**: System runs via Docker Compose with PostgreSQL, Redis, MinIO, and Neo4j services
- [x] **INFRA-02**: Pipeline processes observations as Celery task chains (download → validate → tile → segment → classify → store)
- [x] **INFRA-03**: System stores raw FITS in object storage (MinIO) and metadata in PostgreSQL
- [ ] **INFRA-04**: System provides pipeline status dashboard showing processing progress per observation

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Continuous Ingestion

- **CINGEST-01**: System automatically discovers and ingests new JWST observations as they are released
- **CINGEST-02**: System ingests Vera C. Rubin Observatory / LSST data when available

### Visualization

- **VIS-01**: User can navigate objects visually via interactive force-directed knowledge graph explorer
- **VIS-02**: User can toggle between multi-wavelength image layers (optical, infrared, X-ray) for the same sky region

### Temporal Analysis

- **TEMP-01**: System tracks how individual segmented objects change across repeated observations
- **TEMP-02**: User can compare before/after imagery of the same sky region with blink comparison UI
- **TEMP-03**: System detects transient events and variable objects automatically

### Statistical Analysis

- **STAT-01**: User can view statistical distributions and clustering across object properties
- **STAT-02**: User can explore correlations between object properties across the catalog

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile native app | Web-first, responsive later -- astronomical images require large screens |
| Telescope control / observation scheduling | Completely different domain -- remain a passive data consumer |
| Full LSST real-time ingestion (20TB/night) | Requires massive infrastructure unsustainable for self-funded POC |
| Citizen science platform (Zooniverse-style) | Building a full citizen science platform is a separate product -- lightweight flagging only |
| 3D universe navigation | Technically demanding and often scientifically misleading -- 2D map with depth as filterable property |
| Raw SQL/ADQL query interface | Exposes database internals, creates security surface -- use structured query builder and AI chat instead |
| Real-time collaborative editing | Requires WebSocket infrastructure, conflict resolution -- single-user for v1 |
| Spectral analysis tools | Deep domain-specific tooling -- display basic spectral info, link to specialist tools |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 2 | Complete |
| INGEST-02 | Phase 2 | Complete |
| INGEST-03 | Phase 2 | Complete |
| INGEST-04 | Phase 2 | Complete |
| INGEST-05 | Phase 2 | Complete |
| SEG-01 | Phase 4 | Pending |
| SEG-02 | Phase 4 | Pending |
| SEG-03 | Phase 4 | Pending |
| SEG-04 | Phase 4 | Pending |
| CLASS-01 | Phase 5 | Pending |
| CLASS-02 | Phase 5 | Pending |
| CLASS-03 | Phase 5 | Pending |
| CLASS-04 | Phase 5 | Pending |
| CLASS-05 | Phase 5 | Pending |
| CLASS-06 | Phase 5 | Pending |
| BROWSE-01 | Phase 3 | Complete |
| BROWSE-02 | Phase 3 | Complete |
| BROWSE-03 | Phase 6 | Pending |
| BROWSE-04 | Phase 6 | Pending |
| BROWSE-05 | Phase 6 | Pending |
| BROWSE-06 | Phase 6 | Pending |
| BROWSE-07 | Phase 6 | Pending |
| GRAPH-01 | Phase 7 | Pending |
| GRAPH-02 | Phase 7 | Pending |
| GRAPH-03 | Phase 7 | Pending |
| GRAPH-04 | Phase 7 | Pending |
| INTEL-01 | Phase 5 | Pending |
| INTEL-02 | Phase 8 | Pending |
| INTEL-03 | Phase 8 | Pending |
| INTEL-04 | Phase 8 | Pending |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after Phase 1 completion*
