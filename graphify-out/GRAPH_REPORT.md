# Graph Report - explore-the-universe  (2026-09-18)

## Corpus Check
- 175 files · ~156,644 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1320 nodes · 2598 edges · 114 communities (87 shown, 27 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 250 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f56f0f34`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ViewerClient.tsx
- Phase 1: Foundation & Infrastructure Implementation Plan
- Phase 5 Research: Classification & Cross-Matching
- graph_client
- devDependencies
- TypeScript Config
- detect_sources.py
- Phase 5 Plan 01: Schema, Config, Catalog Clients
- Phase 1-2 Planning Docs
- Summary
- get_observation_detail
- segment_sam.py
- TestClient
- Ingest Pipeline Tests
- observations.py
- _process_fits_to_tiff
- Graphify Skill Docs
- graph-refresh.sh
- test_classification_schema.py
- extract_feature_vector
- Phase 3 Viewer Planning Docs
- Docker Compose Services
- Domain Docs
- Phase 4 Segmentation Planning Docs
- MAST Ingestion Task Pattern
- _make_app_with_mock_session
- Next.js Root Layout
- Pipeline Architecture Overview
- Project Concept Overview
- main
- ESLint Config
- Next.js Config
- PostCSS Config
- Session
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
- chat.py
- Issue tracker: GitHub
- test_load_graph_integration.py
- Observation
- triage-labels.md
- graph.py
- simbad_client.py
- gaia_client.py
- query_ned_region
- query_sdss_region
- a1b2c3d4e5f6_add_classification_tables_and_columns.py
- objects.py
- PipelineStatus
- cross_match_catalogs
- detect_anomalies
- _make_app_with_mock_session
- What was built
- What was built
- validate_wcs
- Project Research Summary
- test_object_detail_api.py
- FastAPI
- test_observations_api.py
- ml_models/__init__.py
- test_load_graph.py
- _make_app_with_mock_session
- Automated SAM-based Object Segmentation
- object.ts
- Next.js Web README
- AstronomicalObject
- compute_search_radius_arcsec
- deploy
- deploy
- Image Tiling (HiPS/HEALPix)
- generate_cutouts
- AIChatPanel.tsx
- _mock_neo4j_lifecycle
- DashboardClient.tsx
- search/page.tsx
- classify_objects
- Knowledge Graph With Spatial Hierarchy
- SearchBar.tsx
- predict_object_types
- api.ts
- viewer/[uuid]/page.tsx
- QueryBuilder
- check_service_health
- Railway deployment
- Settings
- test_load_or_create_classifier_returns_none_when_no_s3_model
- test_classify_objects_creates_classification_for_maskless_object
- test_classify_objects_no_model_classifies_as_unknown

## God Nodes (most connected - your core abstractions)
1. `AstronomicalObject` - 60 edges
2. `Observation` - 35 edges
3. `_make_app_with_mock_session()` - 34 edges
4. `_make_chained_mock()` - 32 edges
5. `ProcessingStep` - 31 edges
6. `TestStructuredSearch` - 31 edges
7. `ObjectClassification` - 29 edges
8. `get_s3_client()` - 29 edges
9. `PipelineStatus` - 28 edges
10. `get_database_session()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `test_classify_objects_not_implemented_removed()` --indirect_call--> `classify_objects()`  [INFERRED]
  tests/test_classification_schema.py → pipeline/tasks/classify_objects.py
- `test_detect_anomalies_excludes_artifacts()` --indirect_call--> `detect_anomalies()`  [INFERRED]
  tests/test_classification_schema.py → pipeline/tasks/detect_anomalies.py
- `test_detect_anomalies_has_isolation_forest()` --indirect_call--> `detect_anomalies()`  [INFERRED]
  tests/test_classification_schema.py → pipeline/tasks/detect_anomalies.py
- `test_detect_anomalies_sets_pipeline_status_completed()` --indirect_call--> `detect_anomalies()`  [INFERRED]
  tests/test_classification_schema.py → pipeline/tasks/detect_anomalies.py
- `test_astronomical_object_catalog_object_name_is_indexed()` --uses--> `AstronomicalObject`  [INFERRED]
  tests/test_classification_schema.py → shared/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Core Pipeline Dependency Chain (Ingest to Encyclopedia)** — planning_research_features_fits_ingestion, planning_research_features_wcs_coordinate_support, planning_research_features_image_tiling, planning_research_features_sam_segmentation, planning_research_features_catalog_cross_matching, planning_research_features_knowledge_graph [EXTRACTED 0.85]
- **Dual-database Knowledge Graph Architecture** — planning_research_features_knowledge_graph, planning_research_stack_neo4j, planning_research_pitfalls_kg_schema_lock_in [EXTRACTED 0.85]
- **FastAPI Health Check Verification Flow** — api_routers_health, concept_postgresql, concept_redis, concept_minio, concept_neo4j [EXTRACTED 0.85]
- **Docker Compose Infrastructure Stack** — docker_compose, docker_compose_postgres, docker_compose_redis, docker_compose_minio, docker_compose_neo4j [EXTRACTED 0.90]
- **JWST Ingestion Celery Task Chain** — _planning_phases_02_data_ingestion_tiling_02_03_summary_ingest_observation_task, _planning_phases_02_data_ingestion_tiling_02_01_summary_download_fits_task, _planning_phases_02_data_ingestion_tiling_02_02_summary_wcs_validation_task, _planning_phases_02_data_ingestion_tiling_02_02_summary_generate_tiles_task [EXTRACTED 0.90]
- **Phase 5 Locked Decision Set** — planning_phases_05_classification_cross_matching_05_context_cross_match_behavior, planning_phases_05_classification_cross_matching_05_context_classification_taxonomy, planning_phases_05_classification_cross_matching_05_context_anomaly_sensitivity, planning_phases_05_classification_cross_matching_05_context_result_storage_api [EXTRACTED 0.90]
- **Roadmap Phase 1-5 Execution Order** — _planning_roadmap_phase1_foundation_infrastructure, _planning_roadmap_phase2_data_ingestion_tiling, _planning_roadmap_phase3_sky_viewer, _planning_roadmap_phase4_segmentation, _planning_roadmap_phase5_classification_crossmatching [EXTRACTED 0.90]
- **Astronomical Data Pipeline Core Stack** — concept_sam, concept_astropy, concept_astroquery, concept_pyvips [INFERRED 0.70]
- **Phase 3 Sky Viewer Planning Cycle** — planning_phases_03-sky-viewer_03-CONTEXT, planning_phases_03-sky-viewer_03-RESEARCH, planning_phases_03-sky-viewer_03-01-PLAN, planning_phases_03-sky-viewer_03-02-PLAN, planning_phases_03-sky-viewer_03-03-PLAN, planning_phases_03-sky-viewer_03-VERIFICATION [INFERRED 0.75]
- **SAM Segmentation Pipeline and Domain-Adaptation Risk** — planning_research_features_sam_segmentation, planning_research_stack_sam2, planning_research_stack_pytorch, planning_research_pitfalls_sam_domain_mismatch [INFERRED 0.75]

## Communities (114 total, 27 thin omitted)

### Community 0 - "ViewerClient.tsx"
Cohesion: 0.06
Nodes (44): NOTE: Currently all bands share the same tile prefix in MinIO due to, ViewerClient(), ViewerClientProps, ViewerClient, ViewerLoaderProps, BandSelector(), BandSelectorProps, CoordinateGrid() (+36 more)

### Community 1 - "Phase 1: Foundation & Infrastructure Implementation Plan"
Cohesion: 0.18
Nodes (8): Phase 1: Foundation & Infrastructure Implementation Plan, task, No-op task that simulates pipeline processing. Accepts an observation UUID,…, test_pipeline_task(), Test the task works with any observation UUID., Test the no-op task executes synchronously and returns expected result., test_noop_task_handles_different_uuids(), test_noop_task_returns_completed_status()

### Community 2 - "Phase 5 Research: Classification & Cross-Matching"
Cohesion: 0.10
Nodes (25): Phase 5 Context: Classification & Cross-Matching, Anomaly Sensitivity Decisions, Classification Taxonomy Decisions, Cross-Match Behavior Decisions, Result Storage & API Decisions, Phase 5 Research: Classification & Cross-Matching, Gaia DR3 Catalog, joblib (+17 more)

### Community 3 - "graph_client"
Cohesion: 0.11
Nodes (29): get_neo4j_session(), Session, FastAPI dependency yielding a Neo4j session from the singleton driver., graph_client, _mock_neo4j_session(), Regression suite: Issue #12 — graph query and neighborhood API. GET…, Empty Cypher result → in_graph: false., OPTIONAL MATCH produces {uuid: null, ...} rows — these should be dropped. (+21 more)

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

### Community 9 - "Summary"
Cohesion: 0.25
Nodes (7): Changes, Checklist, How was this tested?, Notes for the issue-worker, Screenshots, Summary, Type of change

### Community 10 - "get_observation_detail"
Cohesion: 0.13
Nodes (17): _find_sci_extension(), get_observation_detail(), get_tile(), get_wcs_params(), ObservationDetailResponse, BaseModel, get, Session (+9 more)

### Community 11 - "segment_sam.py"
Cohesion: 0.14
Nodes (22): _compute_normalization_parameters(), _encode_mask_to_rle(), _find_sci_extension(), _fits_to_sam_rgb(), _generate_elliptical_mask(), _generate_sam_masks(), _get_sam_processor(), _merge_boundary_masks() (+14 more)

### Community 12 - "TestClient"
Cohesion: 0.09
Nodes (64): get_database_session(), TestClient, _make_app_with_mock_session(), Regression suite: Phase 5 Plan 3 — anomaly API endpoints. All tests are offline…, Returns [] (not 404) when no anomaly-flagged objects exist., Return a TestClient wired with a mock DB session override., test_anomalies_returns_empty_list_when_none_found(), test_anomalies_returns_flagged_objects_with_explanation() (+56 more)

### Community 13 - "Ingest Pipeline Tests"
Cohesion: 0.16
Nodes (15): server_running, slow, Integration tests for the ingest pipeline. Tests the POST /api/ingest and GET…, GET /api/ingest/{uuid}/status with unknown UUID should return 404., End-to-end test: ingest a real JWST observation through the full pipeline. This…, Check if the FastAPI server is reachable., POST /api/ingest should return 202 with observation_uuid and status., POST /api/ingest with empty body should return 422 validation error. (+7 more)

### Community 14 - "observations.py"
Cohesion: 0.31
Nodes (8): list_observations(), ObservationSummaryResponse, ProcessingStepSummary, BaseModel, get, Session, Observations list API endpoint. GET /api/observations — all ingested…, Return all ingested observations with pipeline status and object counts.

### Community 15 - "_process_fits_to_tiff"
Cohesion: 0.17
Nodes (12): _compute_normalization_parameters(), _find_sci_extension(), _generate_dzi_pyramid(), _get_pyvips(), _normalize_chunk(), _process_fits_to_tiff(), Compute ZScale normalization parameters from a subsample of the image. Samples…, Normalize a chunk of FITS data to 8-bit using pre-computed parameters. Applies… (+4 more)

### Community 16 - "Graphify Skill Docs"
Cohesion: 0.22
Nodes (10): .claude/CLAUDE.md (graphify trigger), graphify reference: add-watch, graphify reference: exports, graphify reference: extraction-spec, graphify reference: github-and-merge, graphify reference: hooks, graphify reference: query, graphify reference: transcribe (+2 more)

### Community 18 - "test_classification_schema.py"
Cohesion: 0.05
Nodes (20): Unit tests for Phase 5 Plan 1: classification schema, catalog clients, and…, generate_cutouts must NOT assign pipeline_status = PipelineStatus.completed., CatalogCrossMatch records are created for real catalog matches (mock session)., Catalog failure → no CatalogCrossMatch, task continues without aborting., ObjectClassification.feature_vector is a non-empty dict (JSONB payload)., test_astronomical_object_catalog_object_name_is_indexed(), test_astronomical_object_has_catalog_magnitude(), test_astronomical_object_has_catalog_object_name() (+12 more)

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

### Community 25 - "_make_app_with_mock_session"
Cohesion: 0.21
Nodes (11): _make_anthropic_response(), _make_app_with_mock_session(), _make_chained_mock(), _make_chained_mock_with_objects(), _make_obj(), Tests for the AI chat API endpoint. POST /api/chat — translates natural-…, Variant where .all() returns object list (not types). We configure .all() to…, Build a mock Anthropic Messages response. (+3 more)

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

### Community 35 - "Session"
Cohesion: 0.15
Nodes (20): export_csv(), _export_filename(), export_fits(), export_votable(), _get_latest_classification(), _get_object_or_404(), get_object_types(), get_observation_anomalies() (+12 more)

### Community 54 - "Knowledge Graph (graphify)"
Cohesion: 0.14
Nodes (13): Caveats, How agents use it, If graph.json starts conflicting, Keeping it used, Knowledge Graph (graphify), Optional: rebuild on every commit, Other things to know, Planned code appears as if it exists (+5 more)

### Community 55 - "test_knowledge_graph.py"
Cohesion: 0.17
Nodes (15): parametrize, _load(), Path, Guards on the committed graphify knowledge-graph integration. These are static…, graph.json is committed, so it must not embed this checkout's location., The graph only stays fresh if this hook survives; `graphify install` rewrites…, CI (.github/workflows/knowledge-graph.yml) shells out to this., `graphify install` hardcodes an absolute interpreter path here. That path only… (+7 more)

### Community 60 - "chat.py"
Cohesion: 0.24
Nodes (12): chat_query(), ChatContext, ChatObjectResult, ChatRequest, ChatResponse, BaseModel, post, Session (+4 more)

### Community 61 - "Issue tracker: GitHub"
Cohesion: 0.29
Nodes (6): Blocking, Conventions, Issue tracker: GitHub, Pull requests as a triage surface, When a skill says "fetch the relevant ticket", When a skill says "publish to the issue tracker"

### Community 62 - "test_load_graph_integration.py"
Cohesion: 0.23
Nodes (13): _clean_test_nodes(), _make_catalog_match(), _make_mock_db(), _make_object(), _make_observation(), neo4j_driver(), fixture, Neo4j integration tests for load_graph. Requires a running Neo4j instance… (+5 more)

### Community 63 - "Observation"
Cohesion: 0.16
Nodes (24): Tile serving API endpoints for the sky viewer. GET…, Classify Celery task: feature extraction + RF classification for every object.…, Cross-match Celery task: query all 4 catalogs in parallel per object. Seventh…, Anomaly detection Celery task: IsolationForest scoring + multi-signal flagging.…, download_fits(), task, MAST download Celery task for JWST observations. Queries the Mikulski Archive…, Download calibrated FITS files from MAST and upload to MinIO. Receives a pre-… (+16 more)

### Community 65 - "graph.py"
Cohesion: 0.20
Nodes (17): _build_neighbors(), get_graph_neighbors(), GraphCatalogEntry, GraphNeighborNode, GraphNeighborsResponse, GraphQueryResponse, GraphQueryResult, BaseModel (+9 more)

### Community 66 - "simbad_client.py"
Cohesion: 0.27
Nodes (9): SkyCoord, query_simbad_region(), SIMBAD catalog client with exponential-backoff retry. Implements vectorized…, Query SIMBAD for all objects within *radius_arcsec* of *coordinate*. Returns a…, Resolve an object name to (ra_deg, dec_deg, canonical_name) via SIMBAD. Returns…, resolve_object_name(), _table_to_dicts(), On repeated failure, query_simbad_region must return a not_queried sentinel. (+1 more)

### Community 67 - "gaia_client.py"
Cohesion: 0.38
Nodes (6): SkyCoord, query_gaia_region(), Gaia DR3 catalog client using astroquery.gaia cone-search. On final failure…, Query Gaia DR3 for sources within *radius_arcsec* of *coordinate*. Returns a…, _table_to_dicts(), test_gaia_client_returns_not_queried_on_failure()

### Community 68 - "query_ned_region"
Cohesion: 0.38
Nodes (6): SkyCoord, query_ned_region(), NED (NASA/IPAC Extragalactic Database) catalog client. NED has no…, Query NED for all objects within *radius_arcsec* of *coordinate*. Returns a…, _table_to_dicts(), test_ned_client_returns_not_queried_on_failure()

### Community 69 - "query_sdss_region"
Cohesion: 0.38
Nodes (6): SkyCoord, query_sdss_region(), SDSS (Sloan Digital Sky Survey) catalog client. Radius is hard-capped at 180…, Query SDSS for all objects within *radius_arcsec* of *coordinate*. Returns a…, _table_to_dicts(), test_sdss_client_returns_not_queried_on_failure()

### Community 70 - "a1b2c3d4e5f6_add_classification_tables_and_columns.py"
Cohesion: 0.40
Nodes (4): downgrade(), Add object_classifications table and 3 catalog columns to astronomical_objects., Remove object_classifications table and 3 catalog columns., upgrade()

### Community 71 - "objects.py"
Cohesion: 0.13
Nodes (27): _angular_separation_arcsec(), AnomalyResponse, _catalog_external_url(), ClassificationDetailResponse, ClassificationResponse, CrossMatchDetailResponse, CrossMatchResponse, get_object_cross_matches() (+19 more)

### Community 72 - "PipelineStatus"
Cohesion: 0.11
Nodes (22): get_ingest_status(), IngestRequest, IngestResponse, IngestStatusResponse, BaseModel, get, post, Session (+14 more)

### Community 73 - "cross_match_catalogs"
Cohesion: 0.22
Nodes (10): cross_match_catalogs(), _get_pixel_scale(), SkyCoord, task, UUID, _query_one_catalog(), Cross-match detected objects against SIMBAD, NED, SDSS, and Gaia. Seventh step…, Return WCS pixel scale in arcsec/px for this observation. Recovers FITS S3 keys… (+2 more)

### Community 74 - "detect_anomalies"
Cohesion: 0.16
Nodes (14): IsolationForest, _build_feature_matrix(), detect_anomalies(), _finalize_empty(), _impute_sentinels(), ndarray, task, UUID (+6 more)

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
Cohesion: 0.25
Nodes (13): Celery, FastAPI, healpix-alchemy, MinIO, Neo4j, PostgreSQL, pyvips, Redis (+5 more)

### Community 80 - "test_object_detail_api.py"
Cohesion: 0.34
Nodes (22): _make_app(), _make_clf(), _make_match(), _make_obj(), Regression suite: Phase 6 — object detail API endpoint. GET /api/objects/{uuid}…, Return a mock session that dispatches correctly for the detail endpoint., _session_for(), _teardown() (+14 more)

### Community 81 - "FastAPI"
Cohesion: 0.16
Nodes (16): FastAPI, _make_app_with_mock_session(), _make_obj(), _mock_session_with_objects(), Tests for SIMBAD name-search mode of GET /api/objects/search. Covers: -…, AC2 variant: SIMBAD returns None (name not found) → empty results with null…, AC3: SIMBAD raises RuntimeError (unreachable) → 503 with error detail., Multiple local objects within 5 arcsec are all returned. (+8 more)

### Community 82 - "test_observations_api.py"
Cohesion: 0.37
Nodes (8): _make_app(), _make_obs(), _make_step(), Regression suite: Phase 6 — observations list API endpoint. GET…, Build a mock Session routing query() calls by model class. AstronomicalObject…, _session_for(), _teardown(), TestObservationsList

### Community 84 - "test_load_graph.py"
Cohesion: 0.06
Nodes (47): close_driver(), get_driver(), init_driver(), Neo4j driver singleton and FastAPI dependency. One driver is created at FastAPI…, Create the singleton driver and apply schema constraints., Close the singleton driver (called at FastAPI shutdown)., Return the singleton driver, initialising lazily if needed., lifespan() (+39 more)

### Community 85 - "_make_app_with_mock_session"
Cohesion: 0.13
Nodes (13): _make_app_with_mock_session(), _make_chained_mock(), _make_obj(), Tests for structured query API endpoint. POST /api/objects/search — structured…, Return a TestClient wired with a mock DB session override., angular_separation sort in pure-filter mode falls back to magnitude sort —…, Endpoint accepts limit param without error., Endpoint accepts offset param without error. (+5 more)

### Community 86 - "Automated SAM-based Object Segmentation"
Cohesion: 0.11
Nodes (22): Astropy, astroquery, Anomaly Detection and Novel Object Flagging, Anti-feature: Full Citizen Science Platform, Anti-feature: Full LSST Real-time Ingestion, Anti-feature: Spectral Analysis Tools, Catalog Cross-matching, FITS Ingestion Pipeline (+14 more)

### Community 87 - "object.ts"
Cohesion: 0.15
Nodes (16): GraphPanel(), decompressCocoRle(), MaskOverlay(), MaskOverlayProps, maskToSvgPath(), ObjectPage(), ObjectPageProps, fetchGraphNeighbors() (+8 more)

### Community 88 - "Next.js Web README"
Cohesion: 0.25
Nodes (8): Next.js, React, file.svg Icon, globe.svg Icon, next.svg Logo, vercel.svg Logo, window.svg Icon, Next.js Web README

### Community 89 - "AstronomicalObject"
Cohesion: 0.16
Nodes (13): get_object_classifications(), Return full append-only classification history for an object, newest first., DeclarativeBase, AstronomicalObject, Base, ObjectClassification, Append-only ML classification record for a single pipeline run on one object., Observations with < 10 objects must skip IsolationForest gracefully. (+5 more)

### Community 90 - "compute_search_radius_arcsec"
Cohesion: 0.25
Nodes (7): compute_search_radius_arcsec(), Catalog client package for cross-matching astronomical objects. Exports the…, Return an adaptive cross-match search radius in arcseconds. Compact sources…, Compact source (1 pixel × 0.1 arcsec/px = 0.1 arcsec extent) → ~2 arcsec., Extended source (200 px × 0.1 arcsec/px = 20 arcsec extent) → scales up., test_compute_search_radius_compact_source_returns_approx_2_arcsec(), test_compute_search_radius_extended_source_scales_up()

### Community 91 - "deploy"
Cohesion: 0.18
Nodes (10): build, buildCommand, builder, deploy, healthcheckPath, healthcheckTimeout, restartPolicyMaxRetries, restartPolicyType (+2 more)

### Community 92 - "deploy"
Cohesion: 0.20
Nodes (9): build, builder, dockerfilePath, deploy, healthcheckPath, healthcheckTimeout, restartPolicyMaxRetries, restartPolicyType (+1 more)

### Community 94 - "Image Tiling (HiPS/HEALPix)"
Cohesion: 0.38
Nodes (7): openseadragon, Anti-feature: 3D Universe Navigation, Image Tiling (HiPS/HEALPix), Multi-wavelength Image Layers, Zoomable Sky Map / Image Viewer, Pitfall: Memory Exhaustion on Trillion-pixel FITS, pyvips

### Community 96 - "generate_cutouts"
Cohesion: 0.13
Nodes (15): _create_fits_cutout(), _create_raw_png(), _create_stretched_png(), _extract_cutout_data(), _find_sci_extension(), generate_cutouts(), task, Extract a WCS-preserving cutout from FITS data using Cutout2D. Computes a… (+7 more)

### Community 97 - "AIChatPanel.tsx"
Cohesion: 0.17
Nodes (9): metadata, AIChatPanel(), handleKeyDown(), handleSend(), AIChatPanelProps, chatQuery(), ChatMessage, ChatObjectResult (+1 more)

### Community 98 - "_mock_neo4j_lifecycle"
Cohesion: 0.40
Nodes (4): _mock_neo4j_lifecycle(), fixture, Shared pytest fixtures for the offline test suite. Any test that brings up the…, Patch Neo4j driver lifecycle for tests that don't need a live instance.

### Community 99 - "DashboardClient.tsx"
Cohesion: 0.33
Nodes (7): DashboardClient(), DashboardClientProps, STATUS_STYLES, DashboardPage(), metadata, fetchObservations(), ObservationSummary

### Community 100 - "search/page.tsx"
Cohesion: 0.38
Nodes (6): SearchResults(), run(), searchByCone(), searchByName(), searchByType(), throwApiError()

### Community 101 - "classify_objects"
Cohesion: 0.15
Nodes (13): load_or_create_classifier(), Random Forest classifier for astronomical object morphological type prediction.…, Download and deserialize the pre-trained RF classifier from S3. Returns None if…, _build_feature_matrix(), classify_objects(), _download_cutout(), ndarray, task (+5 more)

### Community 102 - "Knowledge Graph With Spatial Hierarchy"
Cohesion: 0.25
Nodes (9): react-force-graph, AI-assisted Natural Language Querying, Anti-feature: Raw SQL/ADQL Query Interface, Knowledge Graph With Spatial Hierarchy, Object Search, Visual Knowledge Graph Explorer, Pitfall: Knowledge Graph Schema Lock-in, Neo4j Community Edition (+1 more)

### Community 103 - "SearchBar.tsx"
Cohesion: 0.28
Nodes (4): SearchBar(), handleNameSubmit(), Tab, fetchObjectTypes()

### Community 104 - "predict_object_types"
Cohesion: 0.29
Nodes (8): predict_object_types(), ndarray, Serialize and upload a trained classifier to S3., Predict morphological types for a batch of objects. Sentinel values (-999.0)…, save_classifier(), RandomForestClassifier, predict_object_types handles -999.0 sentinels without crashing., test_predict_object_types_imputes_sentinels()

### Community 105 - "api.ts"
Cohesion: 0.54
Nodes (5): QueryBuilderProps, NameSearchResult, ObjectSearchItem, StructuredSearchFilters, StructuredSearchResult

### Community 106 - "viewer/[uuid]/page.tsx"
Cohesion: 0.43
Nodes (6): ViewerPage(), ViewerPageProps, ViewerLoader(), fetchObservation(), fetchWcsParams(), getTileUrl()

### Community 107 - "QueryBuilder"
Cohesion: 0.67
Nodes (3): QueryBuilder(), handleSearch(), searchByFilters()

### Community 108 - "check_service_health"
Cohesion: 0.67
Nodes (3): check_service_health(), get, Response

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
- **210 isolated node(s):** `graph-refresh.sh script`, `graphify-mcp`, `explore-the-universe`, `$schema`, `builder` (+205 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

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
- **Why does `Project Research Summary` connect `Project Research Summary` to `Next.js Web README`, `Image Tiling (HiPS/HEALPix)`, `Knowledge Graph With Spatial Hierarchy`, `Automated SAM-based Object Segmentation`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `AstronomicalObject` connect `AstronomicalObject` to `detect_sources.py`, `segment_sam.py`, `TestClient`, `observations.py`, `test_classification_schema.py`, `_make_app_with_mock_session`, `Session`, `chat.py`, `Observation`, `objects.py`, `cross_match_catalogs`, `detect_anomalies`, `_make_app_with_mock_session`, `test_object_detail_api.py`, `FastAPI`, `test_observations_api.py`, `test_load_graph.py`, `_make_app_with_mock_session`, `generate_cutouts`, `classify_objects`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._