# Graph Report - explore-the-universe  (2026-08-08)

## Corpus Check
- 163 files · ~149,172 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1177 nodes · 2209 edges · 104 communities (74 shown, 30 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 178 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `736c43ff`
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
- tiles.py
- segment_sam.py
- TestClient
- Ingest Pipeline Tests
- ProcessingStep
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
- FITS Ingestion Pipeline
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
- routers/ingest.py
- Issue tracker: GitHub
- test_load_graph_integration.py
- models.py
- triage-labels.md
- graph.py
- simbad_client.py
- gaia_client.py
- query_ned_region
- query_sdss_region
- a1b2c3d4e5f6_add_classification_tables_and_columns.py
- objects.py
- classify_objects
- cross_match_catalogs
- detect_anomalies
- _make_app_with_mock_session
- What was built
- What was built
- validate_wcs
- Project Research Summary
- test_object_detail_api.py
- api.ts
- test_observations_api.py
- ml_models/__init__.py
- test_load_graph.py
- get_s3_client
- Knowledge Graph With Spatial Hierarchy
- upload_test_file
- Next.js Web README
- test_generate_cutouts_does_not_set_pipeline_completed
- compute_search_radius_arcsec
- test_load_or_create_classifier_returns_none_when_no_s3_model
- Settings
- Image Tiling (HiPS/HEALPix)
- test_cross_match_catalogs_creates_crossmatch_records_for_real_matches
- check_service_health
- _mock_neo4j_lifecycle
- PyTorch
- test_cross_match_catalogs_not_queried_on_catalog_failure
- test_classify_objects_creates_classification_for_maskless_object
- test_detect_anomalies_skips_isolation_forest_for_small_observations
- test_detect_anomalies_artifact_never_flagged

## God Nodes (most connected - your core abstractions)
1. `AstronomicalObject` - 36 edges
2. `ProcessingStep` - 34 edges
3. `get_s3_client()` - 29 edges
4. `Observation` - 28 edges
5. `_teardown()` - 23 edges
6. `get_database_session()` - 22 edges
7. `_make_app()` - 22 edges
8. `_session_for()` - 20 edges
9. `_make_app_with_mock_session()` - 20 edges
10. `ObjectClassification` - 19 edges

## Surprising Connections (you probably didn't know these)
- `test_classify_objects_not_implemented_removed()` --indirect_call--> `classify_objects()`  [INFERRED]
  tests/test_classification_schema.py → pipeline/tasks/classify_objects.py
- `Multi-wavelength Image Layers` --conceptually_related_to--> `openseadragon`  [INFERRED]
  .planning/research/FEATURES.md → web/package.json
- `Project Research Summary` --references--> `openseadragon`  [EXTRACTED]
  .planning/research/SUMMARY.md → web/package.json
- `file.svg Icon` --conceptually_related_to--> `Next.js Web README`  [AMBIGUOUS]
  web/public/file.svg → web/README.md
- `globe.svg Icon` --conceptually_related_to--> `Next.js Web README`  [AMBIGUOUS]
  web/public/globe.svg → web/README.md

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

## Communities (104 total, 30 thin omitted)

### Community 0 - "ViewerClient.tsx"
Cohesion: 0.06
Nodes (44): NOTE: Currently all bands share the same tile prefix in MinIO due to, ViewerClient(), ViewerClientProps, ViewerClient, ViewerLoaderProps, BandSelector(), BandSelectorProps, CoordinateGrid() (+36 more)

### Community 1 - "Phase 1: Foundation & Infrastructure Implementation Plan"
Cohesion: 0.14
Nodes (8): Phase 1: Foundation & Infrastructure Implementation Plan, task, No-op task that simulates pipeline processing. Accepts an observation UUID,…, test_pipeline_task(), Test the task works with any observation UUID., Test the no-op task executes synchronously and returns expected result., test_noop_task_handles_different_uuids(), test_noop_task_returns_completed_status()

### Community 2 - "Phase 5 Research: Classification & Cross-Matching"
Cohesion: 0.10
Nodes (25): Phase 5 Context: Classification & Cross-Matching, Anomaly Sensitivity Decisions, Classification Taxonomy Decisions, Cross-Match Behavior Decisions, Result Storage & API Decisions, Phase 5 Research: Classification & Cross-Matching, Gaia DR3 Catalog, joblib (+17 more)

### Community 3 - "graph_client"
Cohesion: 0.11
Nodes (29): get_neo4j_session(), Session, FastAPI dependency yielding a Neo4j session from the singleton driver., graph_client, _mock_neo4j_session(), Regression suite: Issue #12 — graph query and neighborhood API. GET…, Empty Cypher result → in_graph: false., OPTIONAL MATCH produces {uuid: null, ...} rows — these should be dropped. (+21 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (34): eslint, eslint-config-next, next, react, react-dom, tailwindcss, @tailwindcss/postcss, @types/node (+26 more)

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

### Community 10 - "tiles.py"
Cohesion: 0.16
Nodes (18): _find_sci_extension(), get_observation_detail(), get_tile(), get_wcs_params(), ObservationDetailResponse, BaseModel, get, Session (+10 more)

### Community 11 - "segment_sam.py"
Cohesion: 0.14
Nodes (22): _compute_normalization_parameters(), _encode_mask_to_rle(), _find_sci_extension(), _fits_to_sam_rgb(), _generate_elliptical_mask(), _generate_sam_masks(), _get_sam_processor(), _merge_boundary_masks() (+14 more)

### Community 12 - "TestClient"
Cohesion: 0.09
Nodes (64): get_database_session(), TestClient, _make_app_with_mock_session(), Regression suite: Phase 5 Plan 3 — anomaly API endpoints. All tests are offline…, Returns [] (not 404) when no anomaly-flagged objects exist., Return a TestClient wired with a mock DB session override., test_anomalies_returns_empty_list_when_none_found(), test_anomalies_returns_flagged_objects_with_explanation() (+56 more)

### Community 13 - "Ingest Pipeline Tests"
Cohesion: 0.16
Nodes (15): server_running, slow, Integration tests for the ingest pipeline. Tests the POST /api/ingest and GET…, GET /api/ingest/{uuid}/status with unknown UUID should return 404., End-to-end test: ingest a real JWST observation through the full pipeline. This…, Check if the FastAPI server is reachable., POST /api/ingest should return 202 with observation_uuid and status., POST /api/ingest with empty body should return 422 validation error. (+7 more)

### Community 14 - "ProcessingStep"
Cohesion: 0.22
Nodes (12): list_observations(), ObservationSummaryResponse, ProcessingStepSummary, BaseModel, get, Session, Observations list API endpoint. GET /api/observations — all ingested…, Return all ingested observations with pipeline status and object counts. (+4 more)

### Community 15 - "generate_tiles"
Cohesion: 0.14
Nodes (15): _compute_normalization_parameters(), _find_sci_extension(), _generate_dzi_pyramid(), generate_tiles(), _get_pyvips(), _normalize_chunk(), _process_fits_to_tiff(), task (+7 more)

### Community 16 - "Graphify Skill Docs"
Cohesion: 0.22
Nodes (10): .claude/CLAUDE.md (graphify trigger), graphify reference: add-watch, graphify reference: exports, graphify reference: extraction-spec, graphify reference: github-and-merge, graphify reference: hooks, graphify reference: query, graphify reference: transcribe (+2 more)

### Community 18 - "test_classification_schema.py"
Cohesion: 0.06
Nodes (8): Unit tests for Phase 5 Plan 1: classification schema, catalog clients, and…, When no ML model exists in S3, all objects get predicted_type='unknown',…, ObjectClassification.feature_vector is a non-empty dict (JSONB payload)., anomaly_explanation must be a non-empty string when signals fire., test_classify_objects_no_model_classifies_as_unknown(), test_classify_objects_not_implemented_removed(), test_classify_objects_stores_feature_vector_jsonb(), test_detect_anomalies_anomaly_explanation_is_human_readable()

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

### Community 35 - "FITS Ingestion Pipeline"
Cohesion: 0.20
Nodes (10): Astropy, astroquery, Anti-feature: Full LSST Real-time Ingestion, FITS Ingestion Pipeline, FITS File Support, Coordinate System Support (WCS), Pitfall: Storage Costs Explode Before Funding, Pitfall: WCS Coordinate Errors Corrupt Cross-matching (+2 more)

### Community 54 - "Knowledge Graph (graphify)"
Cohesion: 0.14
Nodes (13): Caveats, How agents use it, If graph.json starts conflicting, Keeping it used, Knowledge Graph (graphify), Optional: rebuild on every commit, Other things to know, Planned code appears as if it exists (+5 more)

### Community 55 - "test_knowledge_graph.py"
Cohesion: 0.17
Nodes (15): parametrize, _load(), Path, Guards on the committed graphify knowledge-graph integration. These are static…, graph.json is committed, so it must not embed this checkout's location., The graph only stays fresh if this hook survives; `graphify install` rewrites…, CI (.github/workflows/knowledge-graph.yml) shells out to this., `graphify install` hardcodes an absolute interpreter path here. That path only… (+7 more)

### Community 60 - "routers/ingest.py"
Cohesion: 0.17
Nodes (15): get_ingest_status(), IngestRequest, IngestResponse, IngestStatusResponse, BaseModel, get, post, Session (+7 more)

### Community 61 - "Issue tracker: GitHub"
Cohesion: 0.29
Nodes (6): Blocking, Conventions, Issue tracker: GitHub, Pull requests as a triage surface, When a skill says "fetch the relevant ticket", When a skill says "publish to the issue tracker"

### Community 62 - "test_load_graph_integration.py"
Cohesion: 0.23
Nodes (13): _clean_test_nodes(), _make_catalog_match(), _make_mock_db(), _make_object(), _make_observation(), neo4j_driver(), fixture, Neo4j integration tests for load_graph. Requires a running Neo4j instance… (+5 more)

### Community 63 - "models.py"
Cohesion: 0.25
Nodes (13): Classify Celery task: feature extraction + RF classification for every object.…, Cross-match Celery task: query all 4 catalogs in parallel per object. Seventh…, Anomaly detection Celery task: IsolationForest scoring + multi-signal flagging.…, MAST download Celery task for JWST observations. Queries the Mikulski Archive…, Cutout generation Celery task (sixth step in the 9-task pipeline chain).…, Pipeline orchestrator Celery task for JWST observations. Dispatches the full…, DZI tile pyramid generation Celery task for FITS observations. Converts FITS…, WCS validation Celery task for FITS observations. Extracts World Coordinate… (+5 more)

### Community 65 - "graph.py"
Cohesion: 0.20
Nodes (17): _build_neighbors(), get_graph_neighbors(), GraphCatalogEntry, GraphNeighborNode, GraphNeighborsResponse, GraphQueryResponse, GraphQueryResult, BaseModel (+9 more)

### Community 66 - "simbad_client.py"
Cohesion: 0.32
Nodes (7): SkyCoord, query_simbad_region(), SIMBAD catalog client with exponential-backoff retry. Implements vectorized…, Query SIMBAD for all objects within *radius_arcsec* of *coordinate*. Returns a…, _table_to_dicts(), On repeated failure, query_simbad_region must return a not_queried sentinel., test_simbad_client_returns_not_queried_on_failure()

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
Cohesion: 0.06
Nodes (67): _angular_separation_arcsec(), AnomalyResponse, _catalog_external_url(), ClassificationDetailResponse, ClassificationResponse, CrossMatchDetailResponse, CrossMatchResponse, export_csv() (+59 more)

### Community 72 - "classify_objects"
Cohesion: 0.13
Nodes (19): load_or_create_classifier(), predict_object_types(), ndarray, Random Forest classifier for astronomical object morphological type prediction.…, Serialize and upload a trained classifier to S3., Download and deserialize the pre-trained RF classifier from S3. Returns None if…, Predict morphological types for a batch of objects. Sentinel values (-999.0)…, save_classifier() (+11 more)

### Community 73 - "cross_match_catalogs"
Cohesion: 0.25
Nodes (9): cross_match_catalogs(), SkyCoord, task, _query_one_catalog(), Cross-match detected objects against SIMBAD, NED, SDSS, and Gaia. Seventh step…, After Plan 3, all 9 pipeline tasks are fully implemented — no…, test_cross_match_catalogs_not_implemented_removed(), test_cross_match_catalogs_uses_thread_pool() (+1 more)

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
Cohesion: 0.25
Nodes (13): Celery, FastAPI, healpix-alchemy, MinIO, Neo4j, PostgreSQL, pyvips, Redis (+5 more)

### Community 80 - "test_object_detail_api.py"
Cohesion: 0.34
Nodes (22): _make_app(), _make_clf(), _make_match(), _make_obj(), Regression suite: Phase 6 — object detail API endpoint. GET /api/objects/{uuid}…, Return a mock session that dispatches correctly for the detail endpoint., _session_for(), _teardown() (+14 more)

### Community 81 - "api.ts"
Cohesion: 0.07
Nodes (39): DashboardClient(), DashboardClientProps, STATUS_STYLES, DashboardPage(), metadata, GraphPanel(), decompressCocoRle(), MaskOverlay() (+31 more)

### Community 82 - "test_observations_api.py"
Cohesion: 0.37
Nodes (8): _make_app(), _make_obs(), _make_step(), Regression suite: Phase 6 — observations list API endpoint. GET…, Build a mock Session routing query() calls by model class. AstronomicalObject…, _session_for(), _teardown(), TestObservationsList

### Community 84 - "test_load_graph.py"
Cohesion: 0.06
Nodes (46): close_driver(), get_driver(), init_driver(), Neo4j driver singleton and FastAPI dependency. One driver is created at FastAPI…, Create the singleton driver and apply schema constraints., Close the singleton driver (called at FastAPI shutdown)., Return the singleton driver, initialising lazily if needed., lifespan() (+38 more)

### Community 85 - "get_s3_client"
Cohesion: 0.20
Nodes (10): _get_pixel_scale(), UUID, Return WCS pixel scale in arcsec/px for this observation. Recovers FITS S3 keys…, download_fits(), task, Download calibrated FITS files from MAST and upload to MinIO. Receives a pre-…, Upload DZI XML and all tile images to MinIO tiles bucket. Uploads the DZI…, _upload_tiles_to_minio() (+2 more)

### Community 86 - "Knowledge Graph With Spatial Hierarchy"
Cohesion: 0.15
Nodes (18): react-force-graph, AI-assisted Natural Language Querying, Anomaly Detection and Novel Object Flagging, Anti-feature: Full Citizen Science Platform, Anti-feature: Raw SQL/ADQL Query Interface, Anti-feature: Spectral Analysis Tools, Catalog Cross-matching, Knowledge Graph With Spatial Hierarchy (+10 more)

### Community 87 - "upload_test_file"
Cohesion: 0.40
Nodes (5): post, Session, Temporary test endpoint: uploads a file to MinIO and creates an observation…, upload_test_file(), UploadFile

### Community 88 - "Next.js Web README"
Cohesion: 0.25
Nodes (8): Next.js, React, file.svg Icon, globe.svg Icon, next.svg Logo, vercel.svg Logo, window.svg Icon, Next.js Web README

### Community 90 - "compute_search_radius_arcsec"
Cohesion: 0.25
Nodes (7): compute_search_radius_arcsec(), Catalog client package for cross-matching astronomical objects. Exports the…, Return an adaptive cross-match search radius in arcseconds. Compact sources…, Compact source (1 pixel × 0.1 arcsec/px = 0.1 arcsec extent) → ~2 arcsec., Extended source (200 px × 0.1 arcsec/px = 20 arcsec extent) → scales up., test_compute_search_radius_compact_source_returns_approx_2_arcsec(), test_compute_search_radius_extended_source_scales_up()

### Community 94 - "Image Tiling (HiPS/HEALPix)"
Cohesion: 0.32
Nodes (8): openseadragon, Anti-feature: 3D Universe Navigation, Image Tiling (HiPS/HEALPix), Multi-wavelength Image Layers, Zoomable Sky Map / Image Viewer, Pitfall: Memory Exhaustion on Trillion-pixel FITS, pyvips, openseadragon

### Community 97 - "check_service_health"
Cohesion: 0.67
Nodes (3): check_service_health(), get, Response

### Community 98 - "_mock_neo4j_lifecycle"
Cohesion: 0.40
Nodes (4): _mock_neo4j_lifecycle(), fixture, Shared pytest fixtures for the offline test suite. Any test that brings up the…, Patch Neo4j driver lifecycle for tests that don't need a live instance.

### Community 99 - "PyTorch"
Cohesion: 0.67
Nodes (3): PyTorch, SAM 2.1, timm

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
- **193 isolated node(s):** `graph-refresh.sh script`, `graphify-mcp`, `explore-the-universe`, `eslintConfig`, `nextConfig` (+188 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

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
- **Why does `Project Research Summary` connect `Project Research Summary` to `Next.js Web README`, `Image Tiling (HiPS/HEALPix)`, `FITS Ingestion Pipeline`, `Knowledge Graph With Spatial Hierarchy`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Why does `AstronomicalObject` connect `objects.py` to `detect_sources.py`, `segment_sam.py`, `TestClient`, `_make_app_with_mock_session`, `ProcessingStep`, `test_object_detail_api.py`, `test_classification_schema.py`, `test_observations_api.py`, `test_load_graph.py`, `models.py`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._