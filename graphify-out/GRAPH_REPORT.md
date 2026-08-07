# Graph Report - explore-the-universe  (2026-08-07)

## Corpus Check
- 155 files · ~142,239 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1014 nodes · 1763 edges · 99 communities (75 shown, 24 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 119 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `45b751dd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- WcsParams
- Phase 1: Foundation & Infrastructure Implementation Plan
- Phase 5 Research: Classification & Cross-Matching
- AstronomicalObject
- devDependencies
- TypeScript Config
- _detect_and_store
- Phase 5 Plan 01: Schema, Config, Catalog Clients
- Phase 1-2 Planning Docs
- Summary
- get_s3_client
- segment_sam.py
- test_load_graph.py
- Ingest Pipeline Tests
- ViewerClient.tsx
- generate_tiles
- Graphify Skill Docs
- graph-refresh.sh
- test_classification_schema.py
- extract_feature_vector
- Phase 3 Viewer Planning Docs
- Docker Compose Services
- Domain Docs
- Phase 4 Segmentation Planning Docs
- MAST Ingestion Task Pattern
- generate_cutouts
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
- ProcessingStep
- Issue tracker: GitHub
- test_load_graph_integration.py
- models.py
- triage-labels.md
- main.py
- query_simbad_region
- gaia_client.py
- query_ned_region
- query_sdss_region
- a1b2c3d4e5f6_add_classification_tables_and_columns.py
- ingest_observation
- predict_object_types
- cross_match_catalogs
- detect_anomalies
- _make_app_with_mock_session
- What was built
- What was built
- validate_wcs
- Project Research Summary
- test_object_detail_api.py
- MaskOverlay.tsx
- test_observations_api.py
- ml_models/__init__.py
- _run_load_graph_with_mocks
- classify_objects
- Knowledge Graph With Spatial Hierarchy
- detect_sources
- Next.js Web README
- get_neo4j_session
- upload_test_file
- Settings
- ObservationInfo.tsx
- observation.ts
- formatCoordinates
- api.ts
- _mock_neo4j_lifecycle
- test_cross_match_catalogs_not_queried_on_catalog_failure

## God Nodes (most connected - your core abstractions)
1. `ProcessingStep` - 34 edges
2. `AstronomicalObject` - 32 edges
3. `Observation` - 28 edges
4. `get_s3_client()` - 26 edges
5. `get_database_session()` - 19 edges
6. `_make_app_with_mock_session()` - 19 edges
7. `PipelineStatus` - 18 edges
8. `StepStatus` - 17 edges
9. `ObjectClassification` - 17 edges
10. `detect_anomalies()` - 16 edges

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

## Communities (99 total, 24 thin omitted)

### Community 0 - "WcsParams"
Cohesion: 0.16
Nodes (16): CoordinateGrid(), CoordinateGridProps, formatDecLabel(), formatRaLabel(), GridLine, NICE_GRID_ARCSEC, formatAngularSize(), NICE_ARCSEC_VALUES (+8 more)

### Community 1 - "Phase 1: Foundation & Infrastructure Implementation Plan"
Cohesion: 0.10
Nodes (8): Phase 1: Foundation & Infrastructure Implementation Plan, task, No-op task that simulates pipeline processing. Accepts an observation UUID,…, test_pipeline_task(), Test the task works with any observation UUID., Test the no-op task executes synchronously and returns expected result., test_noop_task_handles_different_uuids(), test_noop_task_returns_completed_status()

### Community 2 - "Phase 5 Research: Classification & Cross-Matching"
Cohesion: 0.10
Nodes (25): Phase 5 Context: Classification & Cross-Matching, Anomaly Sensitivity Decisions, Classification Taxonomy Decisions, Cross-Match Behavior Decisions, Result Storage & API Decisions, Phase 5 Research: Classification & Cross-Matching, Gaia DR3 Catalog, joblib (+17 more)

### Community 3 - "AstronomicalObject"
Cohesion: 0.08
Nodes (54): get_database_session(), _angular_separation_arcsec(), AnomalyResponse, _catalog_external_url(), ClassificationDetailResponse, ClassificationResponse, CrossMatchDetailResponse, CrossMatchResponse (+46 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (35): eslint, eslint-config-next, next, react, react-dom, tailwindcss, @tailwindcss/postcss, @types/node (+27 more)

### Community 5 - "TypeScript Config"
Cohesion: 0.07
Nodes (28): dom, dom.iterable, esnext, **/*.mts, .next/dev/types/**/*.ts, next-env.d.ts, .next/types/**/*.ts, node_modules (+20 more)

### Community 6 - "_detect_and_store"
Cohesion: 0.17
Nodes (16): _assign_confidence_tiers(), _compute_kron_photometry(), _detect_and_store(), _detect_sources_in_array(), _extract_sub_regions(), _flag_edge_detections(), ndarray, UUID (+8 more)

### Community 8 - "Phase 1-2 Planning Docs"
Cohesion: 0.12
Nodes (19): Phase 1 UAT, Phase 2 Plan 01 (MAST download), Phase 2 Plan 01 Summary, Phase 2 Plan 02 (WCS + Tiling), Phase 2 Plan 02 Summary, Phase 2 Plan 03 (Orchestration), Phase 2 Plan 03 Summary, Phase 2 UAT (+11 more)

### Community 9 - "Summary"
Cohesion: 0.25
Nodes (7): Changes, Checklist, How was this tested?, Notes for the issue-worker, Screenshots, Summary, Type of change

### Community 10 - "get_s3_client"
Cohesion: 0.10
Nodes (27): _find_sci_extension(), get_observation_detail(), get_tile(), get_wcs_params(), ObservationDetailResponse, BaseModel, get, Session (+19 more)

### Community 11 - "segment_sam.py"
Cohesion: 0.14
Nodes (22): _compute_normalization_parameters(), _encode_mask_to_rle(), _find_sci_extension(), _fits_to_sam_rgb(), _generate_elliptical_mask(), _generate_sam_masks(), _get_sam_processor(), _merge_boundary_masks() (+14 more)

### Community 12 - "test_load_graph.py"
Cohesion: 0.11
Nodes (19): neo4j_unit, _in_bbox(), load_graph(), task, Return True if pixel (cx, cy) lies inside bbox {xmin,ymin,xmax,ymax}., MERGE all objects for an observation into the Neo4j knowledge graph. Args:…, Offline unit tests for pipeline/tasks/load_graph.py and api/db/neo4j.py. These…, Source check: load_graph must not use CREATE for nodes (only MERGE). (+11 more)

### Community 13 - "Ingest Pipeline Tests"
Cohesion: 0.16
Nodes (15): server_running, slow, Integration tests for the ingest pipeline. Tests the POST /api/ingest and GET…, GET /api/ingest/{uuid}/status with unknown UUID should return 404., End-to-end test: ingest a real JWST observation through the full pipeline. This…, Check if the FastAPI server is reachable., POST /api/ingest should return 202 with observation_uuid and status., POST /api/ingest with empty body should return 422 validation error. (+7 more)

### Community 14 - "ViewerClient.tsx"
Cohesion: 0.15
Nodes (13): NOTE: Currently all bands share the same tile prefix in MinIO due to, ViewerClient(), BandSelector(), BandSelectorProps, buildCssFilter(), DEFAULTS, ImageAdjustments(), ImageAdjustmentsProps (+5 more)

### Community 15 - "generate_tiles"
Cohesion: 0.12
Nodes (17): _compute_normalization_parameters(), _find_sci_extension(), _generate_dzi_pyramid(), generate_tiles(), _get_pyvips(), _normalize_chunk(), _process_fits_to_tiff(), task (+9 more)

### Community 16 - "Graphify Skill Docs"
Cohesion: 0.22
Nodes (10): .claude/CLAUDE.md (graphify trigger), graphify reference: add-watch, graphify reference: exports, graphify reference: extraction-spec, graphify reference: github-and-merge, graphify reference: hooks, graphify reference: query, graphify reference: transcribe (+2 more)

### Community 18 - "test_classification_schema.py"
Cohesion: 0.05
Nodes (17): Unit tests for Phase 5 Plan 1: classification schema, catalog clients, and…, generate_cutouts must NOT assign pipeline_status = PipelineStatus.completed., CatalogCrossMatch records are created for real catalog matches (mock session)., classify_objects creates ObjectClassification for objects without SAM masks., When no ML model exists in S3, all objects get predicted_type='unknown',…, ObjectClassification.feature_vector is a non-empty dict (JSONB payload)., Observations with < 10 objects must skip IsolationForest gracefully., Objects whose predicted_object_type == 'artifact' must NOT be flagged. (+9 more)

### Community 19 - "extract_feature_vector"
Cohesion: 0.15
Nodes (19): _augment_with_sep(), extract_feature_vector(), ndarray, Morphological feature extraction for astronomical objects. Path A (statmorph):…, Build a SEP-only feature dict (statmorph fields set to sentinel)., Merge SEP photometric properties into features (in-place)., Replace any remaining NaN/Inf with sentinel; leave strings untouched., Compute a feature vector for one astronomical object. Returns a dict of named… (+11 more)

### Community 20 - "Phase 3 Viewer Planning Docs"
Cohesion: 0.32
Nodes (8): Phase 3 Plan 01: Tile Serving API Plan, Phase 3 Plan 01 Summary, Phase 3 Plan 02: Core Sky Viewer Plan, Phase 3 Plan 02 Summary, Phase 3 Plan 03: Viewer Panels Plan, Phase 3 Sky Viewer Context, Phase 3 Sky Viewer Research, Phase 3 Sky Viewer Verification Report

### Community 21 - "Docker Compose Services"
Cohesion: 0.43
Nodes (6): Pending todos (STATE.md), MinIO service, minio-init bucket bootstrap service, Neo4j service, PostgreSQL service, Redis service

### Community 22 - "Domain Docs"
Cohesion: 0.29
Nodes (6): Before exploring, read these, Domain Docs, Domain vocabulary, File structure, Flag ADR conflicts, Graphify first

### Community 23 - "Phase 4 Segmentation Planning Docs"
Cohesion: 0.29
Nodes (7): Phase 4 Plan 01: Segmentation Foundation Plan, Phase 4 Plan 01 Summary, Phase 4 Plan 02: Source Detection & Segmentation Plan, Phase 4 Plan 02 Summary, Phase 4 Plan 03: Cutout Generation Plan, Phase 4 Segmentation Context, Phase 4 Segmentation Research

### Community 24 - "MAST Ingestion Task Pattern"
Cohesion: 0.40
Nodes (6): download_fits Celery task, S3 client singleton (shared/s3.py), generate_tiles Celery task, validate_wcs Celery task, ingest_observation orchestrator task, MAST ingestion pipeline pattern

### Community 25 - "generate_cutouts"
Cohesion: 0.13
Nodes (15): _create_fits_cutout(), _create_raw_png(), _create_stretched_png(), _extract_cutout_data(), _find_sci_extension(), generate_cutouts(), task, Extract a WCS-preserving cutout from FITS data using Cutout2D. Computes a… (+7 more)

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

### Community 60 - "ProcessingStep"
Cohesion: 0.15
Nodes (19): get_ingest_status(), IngestRequest, IngestResponse, IngestStatusResponse, BaseModel, get, post, Session (+11 more)

### Community 61 - "Issue tracker: GitHub"
Cohesion: 0.29
Nodes (6): Blocking, Conventions, Issue tracker: GitHub, Pull requests as a triage surface, When a skill says "fetch the relevant ticket", When a skill says "publish to the issue tracker"

### Community 62 - "test_load_graph_integration.py"
Cohesion: 0.23
Nodes (13): _clean_test_nodes(), _make_catalog_match(), _make_mock_db(), _make_object(), _make_observation(), neo4j_driver(), fixture, Neo4j integration tests for load_graph. Requires a running Neo4j instance… (+5 more)

### Community 63 - "models.py"
Cohesion: 0.19
Nodes (17): Random Forest classifier for astronomical object morphological type prediction.…, Classify Celery task: feature extraction + RF classification for every object.…, Cross-match Celery task: query all 4 catalogs in parallel per object. Seventh…, Anomaly detection Celery task: IsolationForest scoring + multi-signal flagging.…, Multi-scale SEP source detection Celery task. Runs SEP (Source Extractor as a…, MAST download Celery task for JWST observations. Queries the Mikulski Archive…, Cutout generation Celery task (sixth step in the 9-task pipeline chain).…, Pipeline orchestrator Celery task for JWST observations. Dispatches the full… (+9 more)

### Community 65 - "main.py"
Cohesion: 0.26
Nodes (10): close_driver(), get_driver(), init_driver(), Neo4j driver singleton and FastAPI dependency. One driver is created at FastAPI…, Create the singleton driver and apply schema constraints., Close the singleton driver (called at FastAPI shutdown)., Return the singleton driver, initialising lazily if needed., lifespan() (+2 more)

### Community 66 - "query_simbad_region"
Cohesion: 0.32
Nodes (7): SkyCoord, query_simbad_region(), SIMBAD catalog client with exponential-backoff retry. Implements vectorized…, Query SIMBAD for all objects within *radius_arcsec* of *coordinate*. Returns a…, _table_to_dicts(), On repeated failure, query_simbad_region must return a not_queried sentinel., test_simbad_client_returns_not_queried_on_failure()

### Community 67 - "gaia_client.py"
Cohesion: 0.28
Nodes (7): SkyCoord, query_gaia_region(), Gaia DR3 catalog client using astroquery.gaia cone-search. On final failure…, Query Gaia DR3 for sources within *radius_arcsec* of *coordinate*. Returns a…, _table_to_dicts(), Catalog client package for cross-matching astronomical objects. Exports the…, test_gaia_client_returns_not_queried_on_failure()

### Community 68 - "query_ned_region"
Cohesion: 0.38
Nodes (6): SkyCoord, query_ned_region(), NED (NASA/IPAC Extragalactic Database) catalog client. NED has no…, Query NED for all objects within *radius_arcsec* of *coordinate*. Returns a…, _table_to_dicts(), test_ned_client_returns_not_queried_on_failure()

### Community 69 - "query_sdss_region"
Cohesion: 0.38
Nodes (6): SkyCoord, query_sdss_region(), SDSS (Sloan Digital Sky Survey) catalog client. Radius is hard-capped at 180…, Query SDSS for all objects within *radius_arcsec* of *coordinate*. Returns a…, _table_to_dicts(), test_sdss_client_returns_not_queried_on_failure()

### Community 70 - "a1b2c3d4e5f6_add_classification_tables_and_columns.py"
Cohesion: 0.40
Nodes (4): downgrade(), Add object_classifications table and 3 catalog columns to astronomical_objects., Remove object_classifications table and 3 catalog columns., upgrade()

### Community 71 - "ingest_observation"
Cohesion: 0.40
Nodes (5): ingest_observation(), task, Dispatch the full 10-task pipeline chain for a pre-created Observation. The…, test_ingest_observation_chain_has_10_tasks(), test_ingest_chain_has_10_tasks()

### Community 72 - "predict_object_types"
Cohesion: 0.18
Nodes (12): load_or_create_classifier(), predict_object_types(), ndarray, Serialize and upload a trained classifier to S3., Download and deserialize the pre-trained RF classifier from S3. Returns None if…, Predict morphological types for a batch of objects. Sentinel values (-999.0)…, save_classifier(), RandomForestClassifier (+4 more)

### Community 73 - "cross_match_catalogs"
Cohesion: 0.17
Nodes (13): compute_search_radius_arcsec(), Return an adaptive cross-match search radius in arcseconds. Compact sources…, cross_match_catalogs(), SkyCoord, task, _query_one_catalog(), Cross-match detected objects against SIMBAD, NED, SDSS, and Gaia. Seventh step…, Compact source (1 pixel × 0.1 arcsec/px = 0.1 arcsec extent) → ~2 arcsec. (+5 more)

### Community 74 - "detect_anomalies"
Cohesion: 0.16
Nodes (14): IsolationForest, _build_feature_matrix(), detect_anomalies(), _impute_sentinels(), ndarray, task, Build a 2-D float array from a list of feature-vector dicts. Missing or…, Replace -999.0 sentinel and NaN values with column medians in-place copy. (+6 more)

### Community 75 - "_make_app_with_mock_session"
Cohesion: 0.16
Nodes (10): _make_app_with_mock_session(), _make_obj(), Tests for cone-search and type-filter API endpoints. GET /api/objects/search —…, Return a TestClient wired with a mock DB session override., Object ~200 arcsec away should not appear when radius=60 arcsec., TestConeAndTypeFilter, TestConeSearch, TestObjectTypes (+2 more)

### Community 76 - "What was built"
Cohesion: 0.18
Nodes (10): Deviations from plan, `pipeline/feature_extraction.py` (160 lines), `pipeline/ml_models/__init__.py` + `pipeline/ml_models/classifier.py` (131 lines), `pipeline/tasks/classify_objects.py` (281 lines), `pipeline/tasks/cross_match_catalogs.py` (361 lines), Plan 02 Summary — Cross-match & ML Classification, Remaining work (Plan 3 — issue #5), Test results (+2 more)

### Community 77 - "What was built"
Cohesion: 0.15
Nodes (12): `api/main.py` (updated), `api/routers/objects.py` (new, 160 lines), Deviations from plan, `.github/workflows/ci.yml` (updated), Knowledge graph, `pipeline/tasks/detect_anomalies.py` (260 lines, replacing 23-line stub), Plan 03 Summary — Anomaly Detection + Classification API, Prototype comparison (+4 more)

### Community 78 - "validate_wcs"
Cohesion: 0.22
Nodes (9): _extract_fits_header_provenance(), _find_sci_extension(), task, Extract provenance metadata from FITS header fields. Supplements MAST metadata…, Extract and validate WCS from FITS headers, update Observation with pointing.…, Find the SCI extension in a FITS HDU list. Checks for a named 'SCI' extension…, Validate WCS accuracy via pixel-to-world-to-pixel round-trip test. Tests…, validate_wcs() (+1 more)

### Community 79 - "Project Research Summary"
Cohesion: 0.19
Nodes (16): check_service_health(), get, Response, Celery, FastAPI, healpix-alchemy, MinIO, Neo4j (+8 more)

### Community 80 - "test_object_detail_api.py"
Cohesion: 0.34
Nodes (21): _make_app(), _make_clf(), _make_match(), _make_obj(), Regression suite: Phase 6 — object detail API endpoint. GET /api/objects/{uuid}…, Return a mock session that dispatches correctly for the detail endpoint., _session_for(), _teardown() (+13 more)

### Community 81 - "MaskOverlay.tsx"
Cohesion: 0.21
Nodes (11): decompressCocoRle(), MaskOverlay(), MaskOverlayProps, maskToSvgPath(), ObjectPage(), ObjectPageProps, fetchObjectDetail(), ClassificationDetail (+3 more)

### Community 82 - "test_observations_api.py"
Cohesion: 0.37
Nodes (8): _make_app(), _make_obs(), _make_step(), Regression suite: Phase 6 — observations list API endpoint. GET…, Build a mock Session routing query() calls by model class. AstronomicalObject…, _session_for(), _teardown(), TestObservationsList

### Community 84 - "_run_load_graph_with_mocks"
Cohesion: 0.25
Nodes (11): _make_catalog_match(), _make_object(), _make_observation(), Helper: patch SessionLocal + get_driver, call load_graph.run()., Galaxy CONTAINS two stars whose centroids are inside its bbox., _run_load_graph_with_mocks(), test_load_graph_contains_inference(), test_load_graph_creates_catalog_entries() (+3 more)

### Community 85 - "classify_objects"
Cohesion: 0.20
Nodes (11): _build_feature_matrix(), classify_objects(), _download_cutout(), ndarray, task, Extract morphological features and classify objects using a trained ML model.…, Download cutout.fits from MinIO and return its data as a float64 array., Convert list of feature dicts to a numeric matrix (n_objects × n_features). (+3 more)

### Community 86 - "Knowledge Graph With Spatial Hierarchy"
Cohesion: 0.07
Nodes (38): Astropy, astroquery, react-force-graph, openseadragon, AI-assisted Natural Language Querying, Anomaly Detection and Novel Object Flagging, Anti-feature: 3D Universe Navigation, Anti-feature: Full Citizen Science Platform (+30 more)

### Community 87 - "detect_sources"
Cohesion: 0.29
Nodes (7): detect_sources(), _find_sci_extension(), _fix_byte_order(), task, Find the SCI extension in a FITS HDU list. Same logic as…, Run multi-scale SEP source detection on a FITS observation. Receives the output…, Ensure data is in native byte order and float32 for SEP. FITS files are big-…

### Community 88 - "Next.js Web README"
Cohesion: 0.25
Nodes (8): Next.js, React, file.svg Icon, globe.svg Icon, next.svg Logo, vercel.svg Logo, window.svg Icon, Next.js Web README

### Community 89 - "get_neo4j_session"
Cohesion: 0.40
Nodes (5): get_neo4j_session(), Session, FastAPI dependency yielding a Neo4j session from the singleton driver., get_neo4j_session must be a generator function so FastAPI Depends works., test_get_neo4j_session_is_generator()

### Community 91 - "upload_test_file"
Cohesion: 0.40
Nodes (5): post, Session, Temporary test endpoint: uploads a file to MinIO and creates an observation…, upload_test_file(), UploadFile

### Community 94 - "ObservationInfo.tsx"
Cohesion: 0.22
Nodes (8): ViewerClientProps, ViewerClient, ViewerLoader(), ViewerLoaderProps, ObservationInfo(), ObservationInfoProps, ObservationDetail, TileMetadata

### Community 95 - "observation.ts"
Cohesion: 0.29
Nodes (8): DashboardClient(), DashboardClientProps, STATUS_STYLES, DashboardPage(), metadata, fetchObservations(), ObservationStep, ObservationSummary

### Community 96 - "formatCoordinates"
Cohesion: 0.36
Nodes (7): CoordinateOverlay(), CoordinateOverlayHandle, CoordinateOverlayProps, updateLiveCoordinates(), decimalDegreesToDms(), decimalDegreesToHms(), formatCoordinates()

### Community 97 - "api.ts"
Cohesion: 0.57
Nodes (5): ViewerPage(), ViewerPageProps, fetchObservation(), fetchWcsParams(), getTileUrl()

### Community 98 - "_mock_neo4j_lifecycle"
Cohesion: 0.40
Nodes (4): _mock_neo4j_lifecycle(), fixture, Shared pytest fixtures for the offline test suite. Any test that brings up the…, Patch Neo4j driver lifecycle for tests that don't need a live instance.

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
- **191 isolated node(s):** `graph-refresh.sh script`, `graphify-mcp`, `explore-the-universe`, `eslintConfig`, `nextConfig` (+186 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

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
- **Why does `Project Research Summary` connect `Project Research Summary` to `Next.js Web README`, `Knowledge Graph With Spatial Hierarchy`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Why does `MinIO` connect `Project Research Summary` to `models.py`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._