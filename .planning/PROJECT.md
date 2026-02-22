# Explore the Universe

## What This Is

A galactic encyclopedia that ingests imagery from the James Webb Space Telescope (JWST) and the Vera C. Rubin Observatory (LSST), segments every distinguishable astronomical object using Meta's Segment Anything Model (SAM), classifies them by cross-referencing existing catalogs and ML classification, and presents everything through an interactive explorer with map-like zooming, search/browse, and knowledge graph navigation. It's a personal research tool that could eventually go public — combining automated discovery with a polished browsing experience.

## Core Value

Any astronomical image goes in, every object comes out segmented, classified, and explorable — turning raw telescope data into a navigable, queryable encyclopedia of the universe.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Ingest JWST and Rubin Observatory imagery (FITS raw + processed composites)
- [ ] Continuous ingestion pipeline for new data as it becomes available
- [ ] Tile/cutout massive images (trillion+ pixel) into SAM-processable segments
- [ ] Segment all distinguishable objects using SAM
- [ ] Cross-match object coordinates with existing catalogs (Simbad, NED, SDSS)
- [ ] ML classification for objects not found in catalogs
- [ ] Flag truly novel/unknown detections for review
- [ ] Knowledge graph with spatial hierarchy (galaxy → system → star → planet)
- [ ] Property-based queries across the knowledge graph (brightness, size, spectral data)
- [ ] External catalog cross-referencing linked in the graph
- [ ] Map-like zooming UI (full sky → region → galaxy → individual objects)
- [ ] Search and browse interface with catalog-style listings
- [ ] Visual knowledge graph explorer (click object, see relationships)
- [ ] Individual object detail pages with properties, classification, source imagery
- [ ] Anomaly detection — automatically flag objects that don't match known categories
- [ ] Temporal analysis — track changes over time across repeated observations
- [ ] Statistical analysis — distributions, clustering, correlations across object properties
- [ ] AI-assisted research — conversational chat interface for natural language queries
- [ ] AI-assisted research — structured smart query builder for precision analysis
- [ ] Both raw FITS data (for analysis) and processed composites (for display)

### Out of Scope

- Mobile native app — web-first, responsive later
- Real-time telescope control or observation scheduling — passive data consumer only
- Full-scale Rubin LSST ingestion (20TB/night) — POC with subset, scale with funding

## Context

**Data Sources:**
- JWST: Available via MAST (Mikulski Archive for Space Telescopes). Images in FITS format with multiple spectral bands, WCS coordinates. Individual images can be extremely large but are released periodically.
- Vera C. Rubin Observatory / LSST: Will produce the Legacy Survey of Space and Time — repeat imaging of the entire southern sky every ~3 nights. ~20TB raw per night when fully operational. Ideal for temporal analysis and transient detection.

**Technical Challenges:**
- Image scale: Some JWST mosaics exceed a trillion pixels. Must tile/cutout before processing.
- SAM was trained on natural images, not astronomical data. May need fine-tuning or domain adaptation for astronomical segmentation.
- Catalog cross-matching requires accurate WCS (World Coordinate System) extraction from FITS headers to map pixel coordinates to sky coordinates.
- Knowledge graph must handle billions of objects at full scale but start manageable for POC.

**Existing Catalogs for Cross-Reference:**
- Simbad (CDS) — comprehensive astronomical object database
- NED (NASA/IPAC Extragalactic Database) — extragalactic focus
- SDSS (Sloan Digital Sky Survey) — extensive photometric/spectroscopic catalog
- Gaia — stellar positions and motions

**Approach:**
- Start with a curated subset of JWST deep field images and (when available) Rubin commissioning data
- Build the full pipeline end-to-end on this subset
- Design for scale from the start but don't premature-optimize storage/compute
- Seek funding to expand to full-scale continuous ingestion

## Constraints

- **Stack**: Python (FastAPI, ML/data pipeline) + Next.js (encyclopedia frontend)
- **Model**: Meta SAM (Segment Anything Model) — latest version for segmentation
- **Scale**: POC with data subset — architecture must support eventual scaling
- **Budget**: Self-funded POC — cloud costs must stay reasonable until funding secured
- **Data Access**: Dependent on public archive APIs (MAST, Rubin Science Platform) — no proprietary data access

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SAM for segmentation | User specified; general-purpose segmentation that finds all boundaries without domain-specific training | — Pending (may need fine-tuning for astronomical images) |
| Cross-match then ML classify | Leverage existing astronomical knowledge first, ML fills gaps, truly unknown objects get flagged | — Pending |
| Knowledge graph for relationships | Spatial hierarchy + properties + catalog links requires graph structure, not just relational DB | — Pending |
| Both FITS and processed images | Raw for scientific analysis, processed for display — dual-layer approach | — Pending |
| Python + Next.js | Python ecosystem is dominant for astronomy/ML; Next.js for rich interactive frontend | — Pending |
| POC-first with subset | Validate approach before committing to full-scale infrastructure | — Pending |

---
*Last updated: 2026-02-21 after initialization*
