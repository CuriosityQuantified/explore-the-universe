# Architecture Research

**Domain:** Astronomical data pipeline + interactive galactic encyclopedia
**Researched:** 2026-02-21
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA INGESTION LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │ MAST/JWST    │  │ Rubin/LSST   │  │ Manual FITS  │                     │
│  │ Downloader   │  │ Downloader   │  │ Upload       │                     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                     │
│         └─────────────────┼─────────────────┘                             │
│                           ▼                                               │
│                 ┌──────────────────┐                                       │
│                 │  Ingestion Queue │  (Celery + Redis)                     │
│                 └────────┬─────────┘                                       │
├──────────────────────────┼──────────────────────────────────────────────────┤
│                    PROCESSING LAYER                                        │
│                          ▼                                                │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │                  Pipeline Orchestrator                    │              │
│  │  (DAG: ingest → tile → segment → classify → store)       │              │
│  └──────────────────────────────────────────────────────────┘              │
│         │              │              │              │                     │
│         ▼              ▼              ▼              ▼                     │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐              │
│  │ Tiler     │  │ SAM       │  │ Catalog   │  │ ML        │              │
│  │ (cutout + │  │ Segmenter │  │ Cross-    │  │ Classifier│              │
│  │  HiPS gen)│  │           │  │ Matcher   │  │           │              │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘              │
│        └───────────────┼───────────────┼───────────────┘                   │
│                        ▼               ▼                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                       STORAGE LAYER                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │ Object Store │  │ PostgreSQL   │  │ Neo4j        │                     │
│  │ (MinIO/S3)   │  │ + PostGIS    │  │ Knowledge    │                     │
│  │ FITS, tiles, │  │ Metadata,    │  │ Graph        │                     │
│  │ thumbnails   │  │ spatial idx  │  │              │                     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                     │
│         └─────────────────┼─────────────────┘                             │
│                           ▼                                               │
├───────────────────────────────────────────────────────────────────────────┤
│                         API LAYER                                          │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │                     FastAPI Backend                       │              │
│  │  /objects  /search  /tiles  /graph  /pipeline  /chat     │              │
│  └──────────────────────────┬───────────────────────────────┘              │
│                             ▼                                             │
├───────────────────────────────────────────────────────────────────────────┤
│                      PRESENTATION LAYER                                    │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │                    Next.js Frontend                       │              │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │              │
│  │  │ Sky      │ │ Search/  │ │ Object   │ │ Graph    │    │              │
│  │  │ Viewer   │ │ Browse   │ │ Detail   │ │ Explorer │    │              │
│  │  │ (tiles)  │ │          │ │ Pages    │ │          │    │              │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │              │
│  └──────────────────────────────────────────────────────────┘              │
└───────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Archive Downloaders** | Authenticate with MAST/Rubin APIs, query for new observations, download FITS files, track what has been ingested | Python with `astroquery.mast` for JWST, Rubin Science Platform client for LSST data |
| **Ingestion Queue** | Decouple download from processing, manage backpressure, retry failed tasks, distribute work across workers | Celery with Redis broker. Each FITS file becomes a task message |
| **Pipeline Orchestrator** | Define and execute the DAG of processing steps per observation, track state, handle partial failures | Celery chains/chords or a lightweight DAG runner (Prefect). NOT Airflow — overkill for this scale |
| **Tiler** | Extract WCS from FITS headers, generate multi-resolution tile pyramids (HiPS or DZI format), produce cutouts for SAM input | Astropy for FITS/WCS, custom tiling code using HEALPix tessellation, `hips` Python package |
| **SAM Segmenter** | Run Segment Anything automatic mask generation on image tiles/cutouts, produce per-object masks with pixel boundaries | Meta SAM (latest version), PyTorch, GPU workers. Process tile-by-tile with overlap for boundary objects |
| **Catalog Cross-Matcher** | Convert pixel coordinates to sky coordinates (RA/Dec) via WCS, query Simbad/NED/SDSS/Gaia for matches within angular tolerance | `astroquery` for catalog APIs, `astropy.coordinates` for coordinate transforms, cone-search matching |
| **ML Classifier** | Classify objects not found in catalogs using photometric/morphological features, flag truly unknown objects as anomalies | scikit-learn or PyTorch classifier trained on labeled catalog data. Start simple (Random Forest), upgrade later |
| **Object Store** | Store raw FITS files, generated tile pyramids, thumbnails, SAM mask outputs as binary blobs | MinIO (self-hosted S3-compatible) for POC, migrate to S3 with funding |
| **PostgreSQL + PostGIS** | Relational metadata: observations, processing state, object properties, spatial indexing for coordinate queries | PostgreSQL 16+ with PostGIS extension for spatial queries (cone search, region containment) |
| **Neo4j Knowledge Graph** | Hierarchical relationships (galaxy contains star system contains star), cross-catalog links, semantic queries | Neo4j Community Edition. Nodes = astronomical objects, edges = spatial/physical relationships |
| **FastAPI Backend** | REST + WebSocket API serving all frontend needs: tile serving, object queries, graph traversal, search, pipeline status | FastAPI with async endpoints, Pydantic models, SQLAlchemy for Postgres, neo4j Python driver |
| **Next.js Frontend** | Interactive encyclopedia UI: sky viewer with deep zoom, search/browse, object detail pages, graph explorer, admin/pipeline dashboard | Next.js 14+ App Router, React, Tailwind CSS, client-side tile viewer library |

## Recommended Project Structure

```
explore-the-universe/
├── pipeline/                    # Python data pipeline (standalone service)
│   ├── ingest/                  # Archive downloaders (MAST, Rubin)
│   │   ├── mast.py              # JWST download via astroquery
│   │   ├── rubin.py             # Rubin/LSST download
│   │   └── scheduler.py         # Polling/scheduling for new data
│   ├── processing/              # Core pipeline stages
│   │   ├── tiler.py             # FITS → tile pyramid generation
│   │   ├── segmenter.py         # SAM inference wrapper
│   │   ├── crossmatch.py        # Catalog cross-matching
│   │   ├── classifier.py        # ML classification
│   │   └── orchestrator.py      # DAG definition and execution
│   ├── models/                  # ML model definitions and weights
│   ├── tasks/                   # Celery task definitions
│   ├── storage/                 # Storage adapters (S3, Postgres, Neo4j)
│   └── config.py                # Pipeline configuration
├── api/                         # FastAPI backend (serves frontend)
│   ├── routers/                 # API route modules
│   │   ├── objects.py           # /objects CRUD and search
│   │   ├── tiles.py             # /tiles tile serving
│   │   ├── graph.py             # /graph knowledge graph queries
│   │   ├── search.py            # /search full-text and spatial
│   │   ├── pipeline.py          # /pipeline status and control
│   │   └── chat.py              # /chat AI-assisted queries
│   ├── models/                  # Pydantic schemas
│   ├── services/                # Business logic
│   ├── db/                      # Database connections and queries
│   └── main.py                  # FastAPI app entry point
├── web/                         # Next.js frontend
│   ├── app/                     # App Router pages
│   │   ├── explore/             # Sky viewer with deep zoom
│   │   ├── search/              # Search and browse
│   │   ├── objects/[id]/        # Object detail pages
│   │   ├── graph/               # Knowledge graph explorer
│   │   └── admin/               # Pipeline dashboard
│   ├── components/              # React components
│   │   ├── viewer/              # Tile viewer (OpenSeadragon/Leaflet)
│   │   ├── graph/               # Graph visualization (D3/Cytoscape)
│   │   └── ui/                  # Shared UI components
│   └── lib/                     # API client, utilities
├── docker/                      # Docker Compose for local dev
│   ├── docker-compose.yml
│   ├── postgres/
│   ├── redis/
│   ├── minio/
│   └── neo4j/
└── .planning/                   # Project planning docs
```

### Structure Rationale

- **pipeline/ separate from api/:** The data pipeline is compute-heavy, runs asynchronously, and has different scaling needs than the API server. Keeping them as separate Python packages with shared models prevents tight coupling. The pipeline runs Celery workers; the API runs FastAPI uvicorn.
- **web/ as standalone Next.js:** Frontend is a separate deployment unit. Communicates exclusively through the FastAPI API. No server-side coupling to Python backend.
- **docker/ for local orchestration:** All infrastructure (Postgres, Redis, MinIO, Neo4j) runs in Docker for local development. Production can use managed services.

## Architectural Patterns

### Pattern 1: HiPS Tile Pyramid for Multi-Resolution Browsing

**What:** Astronomical images are tessellated using the HEALPix scheme into a hierarchical tile pyramid (the HiPS standard from IVOA). Each zoom level doubles resolution, and only visible tiles are fetched by the frontend viewer. This is the same concept as slippy map tiles (like Google Maps) but projected onto the celestial sphere.

**When to use:** Any time you need map-like zooming on astronomical imagery. HiPS is the astronomy-specific standard and is supported by Aladin Lite, which can be embedded directly.

**Trade-offs:** HiPS generation is compute-intensive upfront but makes browsing instant. Pre-generated tiles consume disk space (expect 3-10x the original FITS size for full pyramid). Alternative: generate tiles on-demand and cache, but this adds latency on first view.

**Build order implication:** Tile generation must work before the sky viewer can display anything. This is one of the earliest components to build.

### Pattern 2: Pipeline-as-DAG with Celery Chains

**What:** Each observation flows through a directed acyclic graph of processing steps: download → validate → tile → segment → cross-match → classify → store. Implemented as Celery chains where each step's output feeds the next. Failed steps retry independently without reprocessing prior steps.

**When to use:** For the core ingestion pipeline. Every FITS file follows this path.

**Trade-offs:** Celery is battle-tested and well-understood but adds operational complexity (broker, workers, monitoring). Prefect is a more modern alternative with better DAG visualization and retry semantics. For a POC, Celery is sufficient and avoids another dependency. If DAG complexity grows, consider migrating to Prefect.

**Example:**
```python
from celery import chain

pipeline = chain(
    download_fits.s(observation_id),
    validate_fits.s(),
    generate_tiles.s(),
    run_sam_segmentation.s(),
    crossmatch_catalogs.s(),
    classify_unknowns.s(),
    store_results.s(),
)
pipeline.apply_async()
```

### Pattern 3: Dual Database Strategy (Postgres + Neo4j)

**What:** PostgreSQL with PostGIS handles structured metadata, spatial indexing (cone searches, region queries), processing state, and serves as the source of truth for object properties. Neo4j handles the knowledge graph: hierarchical containment (galaxy → cluster → star), cross-catalog identity links, and graph traversal queries ("show all objects within 2 hops of this quasar").

**When to use:** When you need both SQL-style queries (find all objects brighter than magnitude 15 in this region) AND graph traversal (what is this object related to, what contains it, what catalogs reference it).

**Trade-offs:** Running two databases adds operational cost. The alternative is to use PostgreSQL with Apache AGE extension for graph queries in a single database. This is simpler but AGE is less mature than Neo4j for complex graph operations. Recommendation: start with Postgres-only using JSONB for relationships during POC, add Neo4j when graph queries become the bottleneck or when the knowledge graph features are the focus.

### Pattern 4: Tile-Based SAM Segmentation with Overlap

**What:** Large astronomical images are cut into overlapping tiles (e.g., 1024x1024 with 128px overlap). SAM's automatic mask generator runs on each tile independently. Post-processing merges masks that span tile boundaries using IoU (Intersection over Union) matching on the overlap region. Each merged mask becomes one astronomical object entry.

**When to use:** SAM cannot process trillion-pixel images directly. It has an effective input range of roughly 1024x1024 pixels. Tiling with overlap is required.

**Trade-offs:** Overlap increases compute by ~25% but prevents losing objects at tile boundaries. The merge step adds complexity and can produce artifacts for very large extended objects (nebulae) that span many tiles. For extended objects, consider a hierarchical approach: coarse segmentation at low resolution, then refined segmentation at high resolution.

**Build order implication:** This depends on both the tiler (to produce cutouts) and the SAM model (loaded and running). It is the most GPU-intensive component and should be validated early on a small dataset.

## Data Flow

### Primary Pipeline Flow (Ingestion → Storage)

```
Archive API (MAST)
    │
    ▼  [astroquery download]
Raw FITS File
    │
    ▼  [astropy.io.fits parse headers]
FITS Metadata + WCS Extracted
    │
    ├──▶ Object Store (raw FITS preserved)
    │
    ▼  [HEALPix tessellation + tile generation]
Tile Pyramid (HiPS format)
    │
    ├──▶ Object Store (tile images: JPEG/PNG per zoom level)
    │
    ▼  [cutout extraction for SAM input]
Image Cutouts (1024x1024 overlapping tiles)
    │
    ▼  [SAM automatic mask generation, GPU]
Segmentation Masks (per-object polygons + bounding boxes)
    │
    ├──▶ Object Store (mask images)
    │
    ▼  [WCS pixel-to-sky coordinate transform]
Sky Coordinates per Object (RA, Dec)
    │
    ├──▶ PostgreSQL (object record + coordinates + PostGIS geometry)
    │
    ▼  [astroquery cone-search: Simbad, NED, SDSS, Gaia]
Catalog Matches (name, type, properties from existing catalogs)
    │
    ├──▶ PostgreSQL (update object with catalog data)
    ├──▶ Neo4j (create catalog-link edges)
    │
    ▼  [for unmatched objects: ML classification]
ML Classification (star/galaxy/nebula/artifact + confidence)
    │
    ├──▶ PostgreSQL (classification result + anomaly flag)
    └──▶ Neo4j (create containment edges: region → object)
```

### Frontend Data Flow (User Interaction)

```
User navigates sky viewer
    │
    ▼  [viewport change event]
Tile Request (zoom level + x,y coordinates)
    │
    ▼  [FastAPI /tiles endpoint or direct MinIO URL]
Tile Image Returned (JPEG/PNG)
    │
    ▼  [user clicks on object in viewer]
Object ID lookup (from pre-computed click map or spatial query)
    │
    ▼  [FastAPI /objects/{id}]
Object Detail (properties, classification, source imagery, catalog links)
    │
    ▼  [FastAPI /graph/neighbors/{id}]
Related Objects (Neo4j traversal: parent region, sibling objects, catalog cross-refs)
    │
    ▼  [rendered as interactive graph + detail panel]
```

### Search Data Flow

```
User enters search query ("Crab Nebula" or "magnitude < 12 AND type = galaxy")
    │
    ├──▶ [text search] PostgreSQL full-text search on names + catalog IDs
    ├──▶ [property search] PostgreSQL WHERE clauses on object properties
    ├──▶ [spatial search] PostGIS ST_DWithin for cone search around coordinates
    │
    ▼  [results merged, ranked, paginated]
Search Results → Object Cards → Click → Detail Page → Graph Explorer
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| POC (10-100 FITS images, ~10K objects) | Single machine: all services in Docker Compose. SQLite could even work instead of Postgres. MinIO on local disk. Single Celery worker with GPU. Neo4j optional — use JSONB in Postgres for graph-like queries. |
| Medium (1K-10K images, ~1M objects) | Separate pipeline workers from API server. Multiple Celery workers (1-2 GPU for SAM, CPU for cross-matching). Managed Postgres (RDS or equivalent). MinIO on dedicated storage or S3. Neo4j becomes valuable for graph exploration. |
| Full LSST scale (20TB/night, billions of objects) | Distributed processing: Dask or Ray instead of Celery. Partitioned Postgres with Citus or move spatial queries to Apache Spark AXS. Distributed object store (S3). Neo4j Enterprise with clustering. Tile serving via CDN. This scale requires dedicated infrastructure engineering and is explicitly out of scope for the POC. |

### Scaling Priorities

1. **First bottleneck: SAM GPU inference.** A single JWST deep field image can produce thousands of cutouts. At ~0.5-2 seconds per cutout on consumer GPU, processing a single large mosaic takes hours. Mitigation: batch processing, SAM ViT-B (smaller/faster model) for initial pass, queue management to process in background.
2. **Second bottleneck: Catalog cross-matching latency.** Querying Simbad/NED for each of thousands of objects involves network round-trips. Mitigation: batch queries using `astroquery`, local mirror of key catalogs (VizieR TAP service), cache results aggressively in Postgres.
3. **Third bottleneck: Tile storage volume.** A full HiPS pyramid for a large mosaic can reach tens of GB. Mitigation: generate tiles lazily on-demand for less-visited regions, aggressive JPEG compression for display tiles, keep FITS tiles only for analysis-mode requests.

## Anti-Patterns

### Anti-Pattern 1: Processing FITS Files Synchronously in API Requests

**What people do:** Upload a FITS file via the API and try to tile + segment + classify in the same HTTP request.
**Why it's wrong:** FITS processing takes minutes to hours. The request will timeout, the user gets no feedback, and server resources are blocked.
**Do this instead:** Accept the upload, return a job ID immediately, process asynchronously via the task queue, provide status polling or WebSocket updates.

### Anti-Pattern 2: Storing Tile Pyramids in the Database

**What people do:** Store tile image bytes as BLOBs in PostgreSQL.
**Why it's wrong:** Databases are optimized for structured queries, not serving binary blobs. Tile serving becomes the bottleneck, and database backups balloon in size.
**Do this instead:** Store tiles in object storage (MinIO/S3). Store tile metadata (zoom level, coordinates, URL) in Postgres. Serve tiles directly from object storage, optionally through a CDN.

### Anti-Pattern 3: Monolithic Pipeline Without State Tracking

**What people do:** Write a single Python script that does download → tile → segment → classify in sequence with no persistent state.
**Why it's wrong:** If the script crashes at the classification step, you must re-download and re-tile everything. No visibility into what has been processed.
**Do this instead:** Each pipeline step records its state in Postgres (status: pending/running/complete/failed per step per observation). Failed steps can be retried individually. Pipeline dashboard shows progress.

### Anti-Pattern 4: Using Only Graph Database for Everything

**What people do:** Store all object properties, metadata, and spatial data in Neo4j because "it's a knowledge graph project."
**Why it's wrong:** Neo4j is not optimized for spatial range queries, aggregations, or full-text search. Query performance degrades for operations that relational databases handle natively.
**Do this instead:** Use Postgres for structured queries and spatial indexing (PostGIS). Use Neo4j specifically for relationship traversal and graph exploration. Sync relevant data between them.

### Anti-Pattern 5: Fine-Tuning SAM Before Validating the Pipeline

**What people do:** Spend weeks fine-tuning SAM on astronomical images before building the rest of the pipeline.
**Why it's wrong:** SAM zero-shot performance may be sufficient for many object types. You cannot evaluate segmentation quality without the full pipeline (cross-matching validates whether SAM found real objects). Fine-tuning is optimization — do it after the pipeline works end-to-end.
**Do this instead:** Run SAM zero-shot first. Evaluate against known catalogs. Fine-tune only after quantifying where it fails.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| MAST Archive (JWST) | `astroquery.mast` Python client, async downloads | Rate-limited. Batch queries. Cloud access available (`cloud_only=True`). Supports `missions_mast_search` for mission-specific metadata |
| Rubin Science Platform | Rubin client libraries (TAP queries, Butler data access) | Not fully operational yet. Plan for API changes. Start with commissioning data |
| Simbad (CDS) | `astroquery.simbad` TAP/ADQL queries | Cone search by RA/Dec. Returns object type, identifiers, bibliography. Rate-limited — batch and cache |
| NED (NASA/IPAC) | `astroquery.ned` | Extragalactic focus. Cone search + name resolution |
| SDSS | `astroquery.sdss` | Photometric + spectroscopic data. SQL-based queries via CasJobs |
| Gaia | `astroquery.gaia` TAP service | Stellar positions, parallax, proper motion. Very large catalog — query by region |
| SAM Model | PyTorch model loading, GPU inference | Download weights once, cache locally. ~2.5 GB for ViT-H. Use ONNX export for production inference |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Pipeline ↔ Object Store | S3 API (boto3/MinIO client) | Pipeline writes FITS + tiles + masks. API reads tiles for serving. Use presigned URLs for direct frontend access |
| Pipeline ↔ PostgreSQL | SQLAlchemy ORM or raw SQL | Pipeline writes processing state + object metadata. API reads for queries. Shared Alembic migrations |
| Pipeline ↔ Neo4j | neo4j Python driver, Cypher queries | Pipeline writes nodes + edges after classification. API reads for graph traversal |
| Pipeline ↔ Redis | Celery task protocol | Task dispatch, result storage, progress tracking. API can query task status via Celery result backend |
| API ↔ Frontend | REST (JSON) + WebSocket | REST for CRUD/queries. WebSocket for real-time pipeline status updates. Tile serving can bypass API entirely (direct MinIO URLs) |
| Frontend ↔ Tile Store | HTTP GET (tile URL pattern) | `/tiles/{survey}/{zoom}/{x}/{y}.jpg` pattern. Browser caches tiles aggressively. Consider CDN for production |

## Build Order (Dependencies Between Components)

The following build order reflects hard dependencies — each step requires the previous ones.

```
Phase 1: Foundation
├── Docker Compose infrastructure (Postgres, Redis, MinIO, Neo4j)
├── PostgreSQL schema + migrations (observations, objects, processing_state)
├── MinIO bucket setup
└── FastAPI skeleton with health checks

Phase 2: Ingestion + Tiling
├── MAST downloader (astroquery → FITS → MinIO)         ← needs MinIO
├── FITS metadata extraction (astropy WCS parsing)       ← needs downloader
├── Tile pyramid generation (FITS → HiPS/DZI tiles)     ← needs FITS + MinIO
└── Celery task wiring for download + tile pipeline      ← needs Redis

Phase 3: Sky Viewer
├── Tile serving API endpoint or direct MinIO access     ← needs tiles
├── Frontend sky viewer component (OpenSeadragon/Leaflet/Aladin Lite)
└── Basic navigation: zoom, pan, coordinate display      ← needs tile serving

Phase 4: Segmentation + Classification
├── SAM integration (automatic mask generation on cutouts) ← needs tiler
├── Mask → object extraction (contours, bounding boxes)    ← needs SAM
├── WCS coordinate assignment per object                   ← needs FITS WCS
├── Catalog cross-matching (Simbad, NED, SDSS)            ← needs coordinates
├── ML classifier for unmatched objects                    ← needs training data from cross-match
└── Object records in PostgreSQL + PostGIS                 ← needs all above

Phase 5: Encyclopedia Frontend
├── Search/browse interface                                ← needs object records
├── Object detail pages                                    ← needs object records + tiles
├── Knowledge graph in Neo4j                               ← needs classified objects
├── Graph explorer UI                                      ← needs Neo4j populated
└── Pipeline status dashboard                              ← needs Celery state

Phase 6: Intelligence Layer
├── Anomaly detection                                      ← needs classified objects
├── Temporal analysis (multi-epoch comparison)             ← needs multiple observations
├── AI chat interface (natural language → structured query) ← needs search working
└── Smart query builder                                    ← needs property schema
```

**Critical path:** Infrastructure → FITS download → Tile generation → Sky viewer. This is the shortest path to something visible and testable. SAM segmentation can run in parallel with sky viewer development because tiles serve both purposes.

**Decouple early:** The pipeline (Python, Celery workers) and the frontend (Next.js, API) should be independently deployable from Phase 1. They communicate only through shared databases and object storage. This allows parallel development and independent scaling.

## Sources

- [JWST Science Calibration Pipeline](https://jwst-docs.stsci.edu/jwst-science-calibration-pipeline) — JWST's official multi-stage pipeline architecture (HIGH confidence)
- [MAST Archive API](https://jwst-docs.stsci.edu/accessing-jwst-data/mast-api-access) — JWST data access patterns (HIGH confidence)
- [astroquery MAST module](https://astroquery.readthedocs.io/en/latest/mast/mast.html) — Python client for MAST queries and downloads (HIGH confidence)
- [IVOA HiPS Recommendation](http://www.ivoa.net/documents/HiPS/) — Hierarchical Progressive Survey standard for tile pyramids (HIGH confidence)
- [Aladin Lite](https://github.com/cds-astro/aladin-lite) — Rust/WebAssembly HiPS viewer, reference implementation (HIGH confidence)
- [FitsMap](https://arxiv.org/pdf/2201.12308v1) — Lightweight FITS-to-tiled-map tool (MEDIUM confidence — paper architecture, not production-validated at scale)
- [SAM Repository](https://github.com/facebookresearch/segment-anything) — SAM model architecture and inference API (HIGH confidence)
- [Celery + Redis + FastAPI production guide](https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7) — Async pipeline pattern (MEDIUM confidence)
- [Knowledge Graph in Astronomical Research](https://arxiv.org/html/2406.01391v2) — LLM-based astronomical knowledge graph construction (MEDIUM confidence)
- [Neo4j Graph of the Universe](https://neo4j.com/blog/neo4j-3-0-graph-universe/) — Neo4j for astronomical data modeling (MEDIUM confidence)
- [OpenSeadragon](https://openseadragon.github.io/) — JavaScript deep zoom viewer for tiled images (HIGH confidence)
- [AXS Astronomical Extensions for Spark](https://ipg.fer.hr/ipg/resources/astronomical_cross-matching) — Cross-matching architecture at scale (MEDIUM confidence)

---
*Architecture research for: Astronomical data pipeline + interactive galactic encyclopedia*
*Researched: 2026-02-21*
