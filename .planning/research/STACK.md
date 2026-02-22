# Stack Research

**Domain:** Astronomical data pipeline + galactic encyclopedia (FITS ingestion, SAM segmentation, object classification, knowledge graph, interactive explorer)
**Researched:** 2026-02-21
**Confidence:** MEDIUM-HIGH (most components verified via official docs/PyPI; SAM-for-astronomy domain adaptation is LOW confidence -- uncharted territory)

---

## Recommended Stack

### Data Ingestion & Astronomical Processing (Python)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Astropy** | 7.2.0 | FITS I/O, WCS coordinate handling, image cutouts, unit conversions | The standard library for astronomical computing in Python. No alternative comes close for FITS parsing, WCS extraction (`astropy.wcs`), and coordinate transformations. `Cutout2D` handles sub-image extraction with WCS preservation. | HIGH |
| **astroquery** | 0.4.11 | Querying MAST (JWST), Simbad, NED, SDSS, Gaia catalogs | Official Astropy-affiliated package. `astroquery.mast.MastMissions` provides direct JWST data discovery and download. `astroquery.simbad`, `astroquery.ipac.ned` handle catalog cross-matching. No alternative exists with this breadth. | HIGH |
| **reproject** | 0.19.0 | Image reprojection, mosaicking, coordinate system alignment | Astropy-affiliated. Handles re-gridding FITS images between WCS frames. `reproject_and_coadd()` for mosaic construction. Required when combining multi-band JWST data into composites. | HIGH |
| **pyvips** | 3.1.1 | FITS-to-DeepZoom tile pyramid generation | libvips natively reads FITS and writes DeepZoom (DZI) tiles with `dzsave()`. Processes images larger than memory via streaming. Orders of magnitude faster and more memory-efficient than PIL/Pillow for trillion-pixel images. This is the critical bridge between astronomical FITS and web-viewable tiles. | HIGH |
| **NumPy** | 2.2+ | Array operations on image data | Astropy FITS data is NumPy arrays. Universal dependency. | HIGH |
| **SciPy** | 1.15+ | Signal processing, filtering, statistical analysis on image/catalog data | Standard scientific computing companion to NumPy. Used for image filtering, interpolation, and statistical analysis of object properties. | HIGH |

### Segmentation (Python/PyTorch)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **SAM 2.1** (segment-anything-2) | Latest from GitHub | Zero-shot and fine-tuned segmentation of astronomical objects | Project requirement. SAM 2.1 is the latest release with improved architecture. Install from `github.com/facebookresearch/sam2` (not PyPI -- official recommendation). Requires `torch>=2.5.1`. SAM was NOT trained on astronomical images; expect domain adaptation work. | MEDIUM |
| **PyTorch** | 2.10.0 | Deep learning framework (SAM runtime + classification models) | SAM 2 requires PyTorch. Also needed for classification models. The dominant framework for research and production ML. | HIGH |
| **torchvision** | 0.21+ | Image transforms, pretrained model zoo | Companion to PyTorch. Provides standard augmentation pipelines and pretrained backbones useful for classification. | HIGH |

### Object Classification (Python/PyTorch)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **timm** (PyTorch Image Models) | 1.0.22 | Transfer learning backbone for astronomical object classification | 1000+ pretrained architectures. Use ConvNeXt or EfficientNetV2 as backbone, fine-tune on astronomical classification datasets. Far more practical than training from scratch. Recommend starting with `convnext_base` or `efficientnetv2_m`. | MEDIUM |
| **scikit-learn** | 1.6+ | Classical ML classification, feature engineering, evaluation metrics | For tabular/photometric classification (star vs galaxy vs quasar from catalog features like redshift, magnitudes). Random forests consistently perform well on SDSS-style classification. Not all classification needs deep learning. | HIGH |

### Knowledge Graph (Database)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Neo4j Community Edition** | 5.x (latest) | Knowledge graph storage: spatial hierarchy, object relationships, catalog cross-references | Purpose-built graph database. Cypher query language is intuitive for traversing galaxy-to-system-to-star hierarchies. Neo4j Spatial plugin adds geospatial indexing (though limited to terrestrial CRS -- will need adaptation for celestial coordinates). Community Edition is free, single-node, GPLv3. Sufficient for POC scale. | MEDIUM |
| **neo4j Python driver** | 6.1.0 | Python interface to Neo4j | Official driver. Async support. Well-maintained. | HIGH |
| **PostgreSQL + healpix-alchemy** | PostgreSQL 17 + healpix-alchemy 1.0+ | Relational storage + HEALPix spatial indexing for astronomical coordinate queries | PostgreSQL handles structured catalog data, observation metadata, pipeline state. healpix-alchemy adds HEALPix-based all-sky spatial indexing -- the IVOA standard for astronomical spatial queries. Much better than trying to force celestial coordinates into Neo4j's WGS-84 spatial plugin. Use PostgreSQL for spatial queries, Neo4j for relationship traversal. | MEDIUM |

### Object Storage

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **MinIO** | Latest | S3-compatible object storage for FITS files, tile pyramids, model artifacts | Self-hosted, S3 API compatible. Store raw FITS, processed composites, and DeepZoom tile pyramids. Use `boto3` or `minio` Python SDK. Keeps cloud costs at zero during POC. Swap to AWS S3 when scaling. | MEDIUM |
| **Local filesystem** (fallback) | -- | POC-stage file storage | For initial development, a structured local directory is simpler. Move to MinIO when multi-service access is needed. | HIGH |

### Pipeline Orchestration (Python)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Celery** | 5.5.3 | Distributed task queue for pipeline stages (ingestion, tiling, segmentation, classification) | Production-proven for Python async task execution. Each pipeline stage (download FITS, tile image, run SAM, classify, index to graph) becomes a Celery task. Supports task chaining, retries, priority queues. Integrates natively with FastAPI. | HIGH |
| **Redis** | 7.x | Message broker + result backend for Celery; caching layer | Standard Celery broker. Also useful as a cache for frequently accessed catalog data and API responses. Lightweight, fast, well-understood. | HIGH |

### Backend API (Python)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **FastAPI** | 0.115+ | REST/WebSocket API serving the frontend | Project constraint (Python backend). Async-native, automatic OpenAPI docs, Pydantic validation. Dominant Python API framework. Handles both REST endpoints and WebSocket connections for real-time pipeline status. | HIGH |
| **Pydantic** | 2.x (v3 when stable) | Data validation and serialization | FastAPI dependency. Defines schemas for astronomical objects, catalog entries, pipeline events. | HIGH |
| **SQLAlchemy** | 2.0+ | ORM for PostgreSQL access | Standard Python ORM. Async support. Works with healpix-alchemy for spatial queries. | HIGH |
| **Uvicorn** | 0.34+ | ASGI server | Standard FastAPI deployment server. | HIGH |

### Frontend (TypeScript/React)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Next.js** | 16.x | React framework for the encyclopedia frontend | Project constraint. Latest stable is 16.1 with Turbopack stable, cache components, and PPR. App Router is the standard. Server components reduce client bundle size for data-heavy pages. | HIGH |
| **React** | 19.x | UI library | Bundled with Next.js 16. Server components for data fetching, client components for interactivity. | HIGH |
| **TypeScript** | 5.7+ | Type safety | Non-negotiable for a project of this complexity. | HIGH |
| **Tailwind CSS** | 4.x | Styling | Project constraint (per dev stack). Utility-first, fast iteration. | HIGH |
| **OpenSeadragon** | 5.0.1 | Deep-zoom image viewer for astronomical imagery | Purpose-built for trillion-pixel image viewing. Supports DZI tiles (matches pyvips output). Pure JavaScript, no dependencies. Proven in astronomy (used for large mosaic viewing). Wrap in React component with `useEffect` + ref pattern. | HIGH |
| **react-force-graph** | 1.48.2 | Knowledge graph visualization (2D/3D force-directed graphs) | Best React binding for force-directed graph rendering. Uses WebGL via Three.js for 3D. Supports zoom/pan, node dragging, hover/click. Direct fit for "click object, see relationships" requirement. Use `react-force-graph-2d` for performance, `react-force-graph-3d` for wow factor. | MEDIUM |
| **D3.js** | 7.x | Charts, statistical visualizations, custom data graphics | For property distributions, spectral plots, scatter plots of object properties. Not for the graph visualization (react-force-graph handles that). | HIGH |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Python package manager | Fast, replaces pip + venv. Use `uv venv` and `uv pip install`. |
| **Docker Compose** | Local development environment | Run Neo4j, PostgreSQL, Redis, MinIO as containers. Reproducible setup. |
| **Alembic** | Database migrations for PostgreSQL | Standard SQLAlchemy migration tool. |
| **pytest** | Python testing | With `pytest-asyncio` for async FastAPI tests. |
| **Vitest** | Frontend testing | Fast, native ESM support, works with Next.js. |
| **Flower** | Celery monitoring dashboard | Real-time task monitoring during pipeline development. |

---

## Installation

### Python (Backend + Pipeline)

```bash
# Create environment
uv venv && source .venv/bin/activate

# Core astronomy
uv pip install astropy==7.2.0 astroquery==0.4.11 reproject==0.19.0 pyvips==3.1.1

# ML / Segmentation
uv pip install torch==2.10.0 torchvision timm==1.0.22 scikit-learn

# SAM 2.1 (install from source -- official method)
git clone https://github.com/facebookresearch/sam2.git
cd sam2 && pip install -e . && cd ..

# API + Database
uv pip install "fastapi[standard]" sqlalchemy[asyncio] asyncpg alembic pydantic
uv pip install neo4j==6.1.0 healpix-alchemy

# Pipeline
uv pip install celery[redis] redis flower

# Storage
uv pip install boto3 minio

# Dev
uv pip install pytest pytest-asyncio httpx ruff
```

### Node.js (Frontend)

```bash
# Create Next.js project
npx create-next-app@latest encyclopedia --typescript --tailwind --app --src-dir

# Core dependencies
npm install openseadragon @types/openseadragon
npm install react-force-graph-2d react-force-graph-3d
npm install d3 @types/d3

# Dev dependencies
npm install -D vitest @testing-library/react
```

### Infrastructure (Docker Compose)

```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5-community
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/password
  postgres:
    image: postgres:17
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: explore_universe
      POSTGRES_PASSWORD: password
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  minio:
    image: quay.io/minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not the Alternative |
|----------|-------------|-------------|------------------------|
| **FITS I/O** | Astropy | fitsio | fitsio is faster for raw reads but lacks WCS handling, coordinate transforms, and cutout utilities. Astropy is the ecosystem standard. |
| **Image Tiling** | pyvips/libvips | Pillow/PIL | Pillow loads entire images into memory. Trillion-pixel JWST mosaics will OOM. libvips streams and processes tiles with constant memory. |
| **Image Tiling** | pyvips/libvips | STIFF (FITS-to-TIFF) + vips | Extra conversion step. pyvips reads FITS natively, skip the middleman. |
| **Segmentation** | SAM 2.1 | SExtractor / SEP | SExtractor is the traditional astronomy tool for source extraction. It detects point/extended sources but does NOT produce pixel-level segmentation masks. SAM produces masks. Different tools for different jobs -- may use SEP for initial source detection to feed SAM prompts. |
| **Segmentation** | SAM 2.1 | U-Net custom trained | Would require large labeled astronomical segmentation dataset. SAM's zero-shot capability + fine-tuning is more practical for a POC. |
| **Graph Database** | Neo4j | ArangoDB | ArangoDB is faster in benchmarks and multi-model (doc+graph). But Neo4j has far better graph-specific tooling, Cypher is more intuitive than AQL for graph traversal, and the Python ecosystem (driver, GraphRAG) is more mature. For a graph-first use case, Neo4j wins. |
| **Graph Database** | Neo4j | Apache AGE (PostgreSQL extension) | AGE adds graph capabilities to PostgreSQL, avoiding a separate database. But it is less mature, fewer features, and graph query performance is inferior to a native graph engine. Dual-database (Neo4j + PostgreSQL) is worth the operational complexity. |
| **Spatial Indexing** | PostgreSQL + healpix-alchemy | Neo4j Spatial | Neo4j Spatial only supports WGS-84 (terrestrial) and Cartesian CRS. Celestial coordinates (RA/Dec) on the sphere require HEALPix tessellation, which is the IVOA standard. PostgreSQL + healpix-alchemy is purpose-built for this. |
| **Pipeline Orchestration** | Celery + Redis | Prefect 3 | Prefect (3.6.17) is more modern and developer-friendly. But it adds significant infrastructure (Prefect server/cloud). Celery is simpler for a single-developer POC, integrates directly with FastAPI, and the pipeline tasks (download, tile, segment, classify) map cleanly to Celery task chains. Upgrade to Prefect if pipeline complexity grows. |
| **Pipeline Orchestration** | Celery + Redis | Apache Airflow | Overkill for POC. Airflow's DAG-first model is rigid for image processing pipelines that need dynamic task graphs. Celery is more flexible for "process this image, then fan out to N segments." |
| **Deep Zoom Viewer** | OpenSeadragon | Leaflet + tile layer | Leaflet is map-focused (geographic tiles). OpenSeadragon is purpose-built for arbitrary deep-zoom images. Better fit for astronomical imagery that isn't on a map projection. |
| **Deep Zoom Viewer** | OpenSeadragon | deck.gl | deck.gl is powerful for geospatial data overlays but overkill for image viewing. OpenSeadragon does deep-zoom image viewing better and simpler. Consider deck.gl later for sky-map overlays if needed. |
| **Graph Viz** | react-force-graph | vis.js / vis-network | react-force-graph is React-native, supports 2D/3D/VR, uses WebGL for performance. vis.js has no React bindings and uses canvas (slower for large graphs). |
| **Object Storage** | MinIO | AWS S3 | S3 costs money. MinIO is free and S3-compatible. Use MinIO for POC, swap to S3 for production with zero code changes (same API). |
| **Backend** | FastAPI | Django REST Framework | Django is heavier, synchronous by default. FastAPI's async-native design is better for streaming pipeline results and handling concurrent API requests. Project constraint is FastAPI anyway. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Pillow/PIL for large FITS** | Loads entire image into memory. JWST mosaics will cause OOM crashes. Cannot handle FITS natively. | pyvips (streams from disk, reads FITS, generates DZI tiles) |
| **MongoDB for the knowledge graph** | Document stores are terrible for relationship traversal. "Find all objects within 3 hops of Galaxy X" is O(n) in MongoDB, O(1) per hop in Neo4j. | Neo4j for graph relationships, PostgreSQL for structured data |
| **SAM without fine-tuning** | SAM was trained on natural images (people, cars, animals). Astronomical images have radically different characteristics (noise profiles, dynamic range, morphology). Expect poor out-of-box segmentation on nebulae, faint galaxies. | Fine-tune SAM 2.1 on annotated astronomical image subsets. Use SAM3-Adapter pattern for efficient domain adaptation. |
| **SExtractor as sole segmentation** | SExtractor detects sources and produces elliptical apertures, not pixel-level masks. Cannot segment complex morphologies (spiral arms, nebula structures). | Use SExtractor/SEP for initial source detection (point prompts for SAM), then SAM for pixel-level segmentation |
| **Neo4j Spatial for celestial coordinates** | Only supports WGS-84 (lat/lon on Earth) and Cartesian. Cannot do proper spherical geometry for RA/Dec. | PostgreSQL + healpix-alchemy for spatial queries on celestial coordinates |
| **GraphQL API** | Adds complexity without clear benefit for this project. The frontend needs a mix of REST (CRUD) and WebSocket (pipeline status). GraphQL's flexibility isn't needed when the API consumer is a single frontend you control. | REST (FastAPI) + WebSocket for real-time updates |
| **Elasticsearch for search** | Premature optimization. PostgreSQL full-text search handles catalog search at POC scale. Add Elasticsearch only if search becomes a bottleneck at 1M+ objects. | PostgreSQL `tsvector` + `GIN` indexes for full-text search |

---

## Stack Patterns by Variant

**If scaling beyond POC (funded, full Rubin ingestion):**
- Replace Celery with **Prefect 3** or **Apache Airflow** for more sophisticated pipeline orchestration with monitoring
- Replace MinIO with **AWS S3** or **Google Cloud Storage** for managed object storage
- Add **Kubernetes** for auto-scaling pipeline workers
- Consider **Neo4j Enterprise** for clustering if graph queries become a bottleneck
- Add **Elasticsearch** for full-text search across billions of objects

**If GPU budget is limited:**
- Use SAM 2.1 `sam2_hiera_tiny` checkpoint (smallest model, fastest inference)
- Run segmentation in batches during off-peak hours
- Consider **ONNX Runtime** export of SAM for CPU inference (slower but no GPU needed)

**If the knowledge graph proves unnecessary:**
- PostgreSQL with JSONB columns can handle moderate relationship queries
- Use recursive CTEs for hierarchy traversal instead of a graph database
- This simplifies infrastructure but caps relationship query complexity

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| SAM 2.1 (from GitHub) | PyTorch >= 2.5.1, Python >= 3.10 | SAM 2.1 pins minimum PyTorch version. Do not use PyTorch < 2.5.1. |
| timm 1.0.22 | PyTorch >= 2.0 | timm 1.x works with PyTorch 2.10.0. |
| Astropy 7.2.0 | NumPy >= 1.24, Python >= 3.10 | Astropy 7.x dropped Python 3.9 support. |
| healpix-alchemy | PostgreSQL >= 14, SQLAlchemy >= 2.0 | Requires PostgreSQL 14+ for multirange types. |
| Next.js 16.x | React 19, Node.js >= 18.18 | Next.js 16 requires React 19. Cannot use React 18. |
| OpenSeadragon 5.0.1 | Any modern browser | Pure JS, no framework dependencies. Wrap in React useEffect. |
| neo4j (Python) 6.1.0 | Neo4j Server 5.x, Python 3.10-3.14 | Driver 6.x targets Neo4j 5.x server. |
| Celery 5.5.3 | Redis 6+, Python 3.10+ | Use Redis 7.x for latest features. |
| FastAPI 0.115+ | Pydantic 2.x, Python 3.10+ | FastAPI has moved to Pydantic v2. Do not use Pydantic v1. |

---

## Architecture Decision: Dual Database

This project warrants **two databases** serving distinct purposes:

1. **Neo4j** -- Knowledge graph: Object relationships (galaxy contains star system, star system contains planets), catalog cross-references (Simbad ID <-> NED ID <-> internal ID), hierarchical navigation (drill down from survey to field to object).

2. **PostgreSQL** -- Operational data: Pipeline state, user data, observation metadata, catalog properties (magnitudes, redshifts, spectral types). Plus HEALPix spatial indexing for coordinate-based queries ("find all objects within 5 arcminutes of RA=180, Dec=-30").

**Why not just one?** PostgreSQL cannot efficiently traverse deep relationship chains. Neo4j cannot efficiently do spatial queries on celestial coordinates, full-text search, or serve as a transactional store. Each database does what it does best.

**Sync strategy:** PostgreSQL is the source of truth for object metadata. Neo4j is populated from PostgreSQL via a sync process during the classification/indexing pipeline stage. Objects are linked by a shared UUID.

---

## Critical Risk: SAM on Astronomical Images

SAM 2.1 was trained on SA-V dataset (natural images and video). Astronomical images differ fundamentally:

- **Dynamic range:** Astronomical images span 5+ orders of magnitude in brightness. Natural images do not.
- **Noise characteristics:** Poisson noise from photon counting, cosmic ray artifacts, detector artifacts. SAM has never seen these.
- **Object morphology:** Spiral arms, diffuse nebulae, tidal tails have no analogue in natural images.
- **Scale invariance:** A galaxy can be 3 pixels or 3000 pixels depending on distance.

**Mitigation plan:**
1. Start with SAM zero-shot on preprocessed (stretched, normalized) JWST composites
2. Evaluate segmentation quality manually on ~50 images
3. If inadequate (likely), fine-tune SAM 2.1 on manually annotated astronomical segmentation masks
4. Use SEP (Source Extractor in Python) for initial source detection to generate point prompts for SAM
5. Consider SAM3-Adapter pattern for efficient domain adaptation with minimal data

This is the highest-risk technical component. Budget significant time for it.

---

## Sources

- [Astropy 7.2.0 docs](https://docs.astropy.org/en/stable/) -- FITS I/O, WCS, Cutout2D (HIGH confidence)
- [astroquery 0.4.11 docs](https://astroquery.readthedocs.io/en/stable/) -- MAST, Simbad, NED queries (HIGH confidence)
- [reproject 0.19.0 docs](https://reproject.readthedocs.io/en/stable/) -- Image reprojection and mosaicking (HIGH confidence)
- [pyvips 3.1.1 on PyPI](https://pypi.org/project/pyvips/) -- FITS reading, DZI tile generation (HIGH confidence)
- [SAM 2 GitHub](https://github.com/facebookresearch/sam2) -- Installation, model checkpoints, requirements (HIGH confidence)
- [PyTorch 2.10.0](https://pytorch.org/) -- Latest stable release (HIGH confidence)
- [timm 1.0.22 on PyPI](https://pypi.org/project/timm/) -- Pretrained image classification models (HIGH confidence)
- [Neo4j Community Edition](https://neo4j.com/licensing/) -- Licensing, limitations (HIGH confidence)
- [neo4j Python driver 6.1.0 on PyPI](https://pypi.org/project/neo4j/) -- Python driver version (HIGH confidence)
- [healpix-alchemy on GitHub](https://github.com/skyportal/healpix-alchemy) -- HEALPix spatial indexing for PostgreSQL (MEDIUM confidence)
- [Neo4j Spatial plugin](https://neo4j-contrib.github.io/spatial/) -- Geospatial capabilities and CRS limitations (MEDIUM confidence)
- [OpenSeadragon 5.0.1](https://openseadragon.github.io/) -- Deep zoom viewer (HIGH confidence)
- [react-force-graph 1.48.2](https://github.com/vasturiano/react-force-graph) -- React graph visualization (HIGH confidence)
- [Next.js 16 blog](https://nextjs.org/blog) -- Latest version, features (HIGH confidence)
- [FastAPI releases](https://github.com/fastapi/fastapi/releases) -- Latest version (HIGH confidence)
- [Celery 5.5.3](https://github.com/celery/celery) -- Task queue version (HIGH confidence)
- [Prefect 3.6.17](https://github.com/PrefectHQ/prefect/releases) -- Alternative orchestration (MEDIUM confidence)
- [SAM fine-tuning tutorials](https://blog.roboflow.com/fine-tune-sam-2-1/) -- Domain adaptation approach (MEDIUM confidence)
- [MAST API for JWST](https://jwst-docs.stsci.edu/accessing-jwst-data/mast-api-access) -- JWST data access (HIGH confidence)
- [Astroquery MAST newsletter Feb 2025](https://archive.stsci.edu/contents/newsletters/february-2025/astroquery-now-supports-downloads-through-hst-and-jwst-search-interfaces) -- Recent MAST integration updates (HIGH confidence)

---
*Stack research for: Explore the Universe -- Astronomical Data Pipeline + Galactic Encyclopedia*
*Researched: 2026-02-21*
