# Graph Report - explore-the-universe  (2026-07-30)

## Corpus Check
- 119 files · ~121,708 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 578 nodes · 871 edges · 62 communities (41 shown, 21 thin omitted)
- Extraction: 93% EXTRACTED · 6% INFERRED · 1% AMBIGUOUS · INFERRED: 54 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `127b5e42`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Sky Viewer Pages
- Project Research Summary
- Phase 5 Research: Classification & Cross-Matching
- Knowledge Graph With Spatial Hierarchy
- devDependencies
- TypeScript Config
- detect_sources.py
- Phase 5 Plan 01: Schema, Config, Catalog Clients
- Phase 1-2 Planning Docs
- tiles.py
- ProcessingStep
- segment_sam
- segment_sam.py
- Ingest Pipeline Tests
- generate_cutouts
- _process_fits_to_tiff
- Graphify Skill Docs
- graph-refresh.sh
- WCS Validation & Provenance
- Coordinate Overlay UI
- Phase 3 Viewer Planning Docs
- Docker Compose Services
- models.py
- Phase 4 Segmentation Planning Docs
- MAST Ingestion Task Pattern
- upload_test_file
- Next.js Root Layout
- Pipeline Architecture Overview
- Project Concept Overview
- main
- ESLint Config
- Next.js Config
- PostCSS Config
- Root Graphify Rules
- Project Root
- Phase 3 Plan Summary
- Phase 4 Plan Summary
- Phase 4 UAT Report
- Phase 4 Verification Report
- Anti-feature: Mobile App
- Anti-feature: Realtime Collab
- Data Export Feature
- Data Provenance Metadata
- D3.js Dependency
- Knowledge Graph (graphify)
- test_knowledge_graph.py
- graphify
- cross_match_all_catalogs
- Phase 5 Plan 02: Cross-Match & Classification Tasks
- Phase 5 Plan 03: Anomaly Detection & API Endpoints
- get_ingest_status
- Settings

## God Nodes (most connected - your core abstractions)
1. `ProcessingStep` - 22 edges
2. `Observation` - 19 edges
3. `get_s3_client()` - 18 edges
4. `compilerOptions` - 16 edges
5. `Phase 5 Research: Classification & Cross-Matching` - 15 edges
6. `Project Research Summary` - 15 edges
7. `segment_sam()` - 14 edges
8. `generate_cutouts()` - 13 edges
9. `PipelineStatus` - 13 edges
10. `WcsParams` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Multi-wavelength Image Layers` --conceptually_related_to--> `openseadragon`  [INFERRED]
  .planning/research/FEATURES.md → web/package.json
- `Project Research Summary` --references--> `openseadragon`  [EXTRACTED]
  .planning/research/SUMMARY.md → web/package.json
- `file.svg Icon` --conceptually_related_to--> `Next.js Web README`  [AMBIGUOUS]
  web/public/file.svg → web/README.md
- `globe.svg Icon` --conceptually_related_to--> `Next.js Web README`  [AMBIGUOUS]
  web/public/globe.svg → web/README.md
- `next.svg Logo` --conceptually_related_to--> `Next.js Web README`  [AMBIGUOUS]
  web/public/next.svg → web/README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Roadmap Phase 1-5 Execution Order** — _planning_roadmap_phase1_foundation_infrastructure, _planning_roadmap_phase2_data_ingestion_tiling, _planning_roadmap_phase3_sky_viewer, _planning_roadmap_phase4_segmentation, _planning_roadmap_phase5_classification_crossmatching [EXTRACTED 0.90]
- **JWST Ingestion Celery Task Chain** — _planning_phases_02_data_ingestion_tiling_02_03_summary_ingest_observation_task, _planning_phases_02_data_ingestion_tiling_02_01_summary_download_fits_task, _planning_phases_02_data_ingestion_tiling_02_02_summary_wcs_validation_task, _planning_phases_02_data_ingestion_tiling_02_02_summary_generate_tiles_task [EXTRACTED 0.90]
- **Phase 3 Sky Viewer Planning Cycle** — planning_phases_03-sky-viewer_03-CONTEXT, planning_phases_03-sky-viewer_03-RESEARCH, planning_phases_03-sky-viewer_03-01-PLAN, planning_phases_03-sky-viewer_03-02-PLAN, planning_phases_03-sky-viewer_03-03-PLAN, planning_phases_03-sky-viewer_03-VERIFICATION [INFERRED 0.75]
- **Docker Compose Infrastructure Stack** — docker_compose, docker_compose_postgres, docker_compose_redis, docker_compose_minio, docker_compose_neo4j [EXTRACTED 0.90]
- **Phase 5 Locked Decision Set** — planning_phases_05_classification_cross_matching_05_context_cross_match_behavior, planning_phases_05_classification_cross_matching_05_context_classification_taxonomy, planning_phases_05_classification_cross_matching_05_context_anomaly_sensitivity, planning_phases_05_classification_cross_matching_05_context_result_storage_api [EXTRACTED 0.90]
- **SAM Segmentation Pipeline and Domain-Adaptation Risk** — planning_research_features_sam_segmentation, planning_research_stack_sam2, planning_research_stack_pytorch, planning_research_pitfalls_sam_domain_mismatch [INFERRED 0.75]
- **Dual-database Knowledge Graph Architecture** — planning_research_features_knowledge_graph, planning_research_stack_neo4j, planning_research_pitfalls_kg_schema_lock_in [EXTRACTED 0.85]
- **Core Pipeline Dependency Chain (Ingest to Encyclopedia)** — planning_research_features_fits_ingestion, planning_research_features_wcs_coordinate_support, planning_research_features_image_tiling, planning_research_features_sam_segmentation, planning_research_features_catalog_cross_matching, planning_research_features_knowledge_graph [EXTRACTED 0.85]
- **FastAPI Health Check Verification Flow** — api_routers_health, concept_postgresql, concept_redis, concept_minio, concept_neo4j [EXTRACTED 0.85]
- **Astronomical Data Pipeline Core Stack** — concept_sam, concept_astropy, concept_astroquery, concept_pyvips [INFERRED 0.70]

## Communities (62 total, 21 thin omitted)

### Community 0 - "Sky Viewer Pages"
Cohesion: 0.07
Nodes (42): ViewerPage(), ViewerPageProps, NOTE: Currently all bands share the same tile prefix in MinIO due to, ViewerClient(), ViewerClientProps, ViewerClient, ViewerLoader(), ViewerLoaderProps (+34 more)

### Community 1 - "Project Research Summary"
Cohesion: 0.05
Nodes (36): check_service_health(), get, Astropy, astroquery, Celery, FastAPI, healpix-alchemy, MinIO (+28 more)

### Community 2 - "Phase 5 Research: Classification & Cross-Matching"
Cohesion: 0.10
Nodes (25): Phase 5 Context: Classification & Cross-Matching, Anomaly Sensitivity Decisions, Classification Taxonomy Decisions, Cross-Match Behavior Decisions, Result Storage & API Decisions, Phase 5 Research: Classification & Cross-Matching, Gaia DR3 Catalog, joblib (+17 more)

### Community 3 - "Knowledge Graph With Spatial Hierarchy"
Cohesion: 0.08
Nodes (34): react-force-graph, openseadragon, AI-assisted Natural Language Querying, Anomaly Detection and Novel Object Flagging, Anti-feature: 3D Universe Navigation, Anti-feature: Full Citizen Science Platform, Anti-feature: Full LSST Real-time Ingestion, Anti-feature: Raw SQL/ADQL Query Interface (+26 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (35): eslint, eslint-config-next, next, react, react-dom, tailwindcss, @tailwindcss/postcss, @types/node (+27 more)

### Community 5 - "TypeScript Config"
Cohesion: 0.07
Nodes (28): dom, dom.iterable, esnext, **/*.mts, .next/dev/types/**/*.ts, next-env.d.ts, .next/types/**/*.ts, node_modules (+20 more)

### Community 6 - "detect_sources.py"
Cohesion: 0.13
Nodes (26): _assign_confidence_tiers(), _compute_kron_photometry(), _detect_and_store(), detect_sources(), _detect_sources_in_array(), _extract_sub_regions(), _find_sci_extension(), _fix_byte_order() (+18 more)

### Community 8 - "Phase 1-2 Planning Docs"
Cohesion: 0.12
Nodes (19): Phase 1 UAT, Phase 2 Plan 01 (MAST download), Phase 2 Plan 01 Summary, Phase 2 Plan 02 (WCS + Tiling), Phase 2 Plan 02 Summary, Phase 2 Plan 03 (Orchestration), Phase 2 Plan 03 Summary, Phase 2 UAT (+11 more)

### Community 9 - "tiles.py"
Cohesion: 0.13
Nodes (19): get_database_session(), _find_sci_extension(), get_observation_detail(), get_tile(), get_wcs_params(), ObservationDetailResponse, BaseModel, get (+11 more)

### Community 10 - "ProcessingStep"
Cohesion: 0.20
Nodes (16): IngestRequest, IngestResponse, IngestStatusResponse, BaseModel, post, Ingest API endpoints for triggering and monitoring the pipeline. POST…, Request body for POST /api/ingest., Response body for POST /api/ingest (202 Accepted). (+8 more)

### Community 11 - "segment_sam"
Cohesion: 0.11
Nodes (21): _compute_normalization_parameters(), _encode_mask_to_rle(), _find_sci_extension(), _fits_to_sam_rgb(), _generate_elliptical_mask(), _generate_sam_masks(), _get_sam_processor(), _merge_boundary_masks() (+13 more)

### Community 12 - "segment_sam.py"
Cohesion: 0.16
Nodes (20): download_fits(), task, MAST download Celery task for JWST observations. Queries the Mikulski Archive…, Download calibrated FITS files from MAST and upload to MinIO. Receives a pre-…, Cutout generation and pipeline finalization Celery task. Extracts per-object…, Pipeline orchestrator Celery task for JWST observations. Dispatches the full…, SAM 3 segmentation with SEP elliptical fallback Celery task. Generates pixel-…, generate_tiles() (+12 more)

### Community 13 - "Ingest Pipeline Tests"
Cohesion: 0.16
Nodes (15): server_running, slow, Integration tests for the ingest pipeline. Tests the POST /api/ingest and GET…, GET /api/ingest/{uuid}/status with unknown UUID should return 404., End-to-end test: ingest a real JWST observation through the full pipeline. This…, Check if the FastAPI server is reachable., POST /api/ingest should return 202 with observation_uuid and status., POST /api/ingest with empty body should return 422 validation error. (+7 more)

### Community 14 - "generate_cutouts"
Cohesion: 0.13
Nodes (15): _create_fits_cutout(), _create_raw_png(), _create_stretched_png(), _extract_cutout_data(), _find_sci_extension(), generate_cutouts(), task, Extract a WCS-preserving cutout from FITS data using Cutout2D. Computes a… (+7 more)

### Community 15 - "_process_fits_to_tiff"
Cohesion: 0.17
Nodes (12): _compute_normalization_parameters(), _find_sci_extension(), _generate_dzi_pyramid(), _get_pyvips(), _normalize_chunk(), _process_fits_to_tiff(), Compute ZScale normalization parameters from a subsample of the image. Samples…, Normalize a chunk of FITS data to 8-bit using pre-computed parameters. Applies… (+4 more)

### Community 16 - "Graphify Skill Docs"
Cohesion: 0.22
Nodes (10): .claude/CLAUDE.md (graphify trigger), graphify reference: add-watch, graphify reference: exports, graphify reference: extraction-spec, graphify reference: github-and-merge, graphify reference: hooks, graphify reference: query, graphify reference: transcribe (+2 more)

### Community 18 - "WCS Validation & Provenance"
Cohesion: 0.22
Nodes (9): _extract_fits_header_provenance(), _find_sci_extension(), task, Extract provenance metadata from FITS header fields. Supplements MAST metadata…, Extract and validate WCS from FITS headers, update Observation with pointing.…, Find the SCI extension in a FITS HDU list. Checks for a named 'SCI' extension…, Validate WCS accuracy via pixel-to-world-to-pixel round-trip test. Tests…, validate_wcs() (+1 more)

### Community 19 - "Coordinate Overlay UI"
Cohesion: 0.36
Nodes (7): CoordinateOverlay(), CoordinateOverlayHandle, CoordinateOverlayProps, updateLiveCoordinates(), decimalDegreesToDms(), decimalDegreesToHms(), formatCoordinates()

### Community 20 - "Phase 3 Viewer Planning Docs"
Cohesion: 0.32
Nodes (8): Phase 3 Plan 01: Tile Serving API Plan, Phase 3 Plan 01 Summary, Phase 3 Plan 02: Core Sky Viewer Plan, Phase 3 Plan 02 Summary, Phase 3 Plan 03: Viewer Panels Plan, Phase 3 Sky Viewer Context, Phase 3 Sky Viewer Research, Phase 3 Sky Viewer Verification Report

### Community 21 - "Docker Compose Services"
Cohesion: 0.43
Nodes (6): Pending todos (STATE.md), MinIO service, minio-init bucket bootstrap service, Neo4j service, PostgreSQL service, Redis service

### Community 22 - "models.py"
Cohesion: 0.36
Nodes (4): DeclarativeBase, AstronomicalObject, Base, CatalogCrossMatch

### Community 23 - "Phase 4 Segmentation Planning Docs"
Cohesion: 0.29
Nodes (7): Phase 4 Plan 01: Segmentation Foundation Plan, Phase 4 Plan 01 Summary, Phase 4 Plan 02: Source Detection & Segmentation Plan, Phase 4 Plan 02 Summary, Phase 4 Plan 03: Cutout Generation Plan, Phase 4 Segmentation Context, Phase 4 Segmentation Research

### Community 24 - "MAST Ingestion Task Pattern"
Cohesion: 0.40
Nodes (6): download_fits Celery task, S3 client singleton (shared/s3.py), generate_tiles Celery task, validate_wcs Celery task, ingest_observation orchestrator task, MAST ingestion pipeline pattern

### Community 25 - "upload_test_file"
Cohesion: 0.40
Nodes (5): post, Session, Temporary test endpoint: uploads a file to MinIO and creates an observation…, upload_test_file(), UploadFile

### Community 26 - "Next.js Root Layout"
Cohesion: 0.40
Nodes (3): geistMono, geistSans, metadata

### Community 27 - "Pipeline Architecture Overview"
Cohesion: 0.50
Nodes (4): Anti-feature: Telescope Control / Scheduling, Unified Pipeline: Image -> Segmentation -> Classification -> Encyclopedia, Celery, Redis

### Community 28 - "Project Concept Overview"
Cohesion: 0.67
Nodes (3): Explore the Universe project, Knowledge graph spatial hierarchy concept, SAM (Segment Anything Model) segmentation

### Community 31 - "main"
Cohesion: 0.83
Nodes (3): main(), Path, structure()

### Community 54 - "Knowledge Graph (graphify)"
Cohesion: 0.14
Nodes (13): Caveats, How agents use it, If graph.json starts conflicting, Keeping it used, Knowledge Graph (graphify), Optional: rebuild on every commit, Other things to know, Planned code appears as if it exists (+5 more)

### Community 55 - "test_knowledge_graph.py"
Cohesion: 0.17
Nodes (15): parametrize, _load(), Path, Guards on the committed graphify knowledge-graph integration. These are static…, graph.json is committed, so it must not embed this checkout's location., The graph only stays fresh if this hook survives; `graphify install` rewrites…, CI (.github/workflows/knowledge-graph.yml) shells out to this., `graphify install` hardcodes an absolute interpreter path here. That path only… (+7 more)

### Community 60 - "get_ingest_status"
Cohesion: 0.50
Nodes (4): get_ingest_status(), get, Session, Check the status of an ingestion pipeline. Returns the observation details…

## Ambiguous Edges - Review These
- `Next.js Web README` → `file.svg Icon`  [AMBIGUOUS]
  web/public/file.svg · relation: conceptually_related_to
- `Next.js Web README` → `globe.svg Icon`  [AMBIGUOUS]
  web/public/globe.svg · relation: conceptually_related_to
- `Next.js Web README` → `next.svg Logo`  [AMBIGUOUS]
  web/public/next.svg · relation: conceptually_related_to
- `Next.js Web README` → `vercel.svg Logo`  [AMBIGUOUS]
  web/public/vercel.svg · relation: conceptually_related_to
- `Next.js Web README` → `window.svg Icon`  [AMBIGUOUS]
  web/public/window.svg · relation: conceptually_related_to

## Knowledge Gaps
- **150 isolated node(s):** `graph-refresh.sh script`, `graphify-mcp`, `explore-the-universe`, `eslintConfig`, `nextConfig` (+145 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Next.js Web README` and `file.svg Icon`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Next.js Web README` and `globe.svg Icon`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Next.js Web README` and `next.svg Logo`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Next.js Web README` and `vercel.svg Logo`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Next.js Web README` and `window.svg Icon`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Project Research Summary` connect `Project Research Summary` to `Knowledge Graph With Spatial Hierarchy`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `MinIO` connect `Project Research Summary` to `tiles.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._