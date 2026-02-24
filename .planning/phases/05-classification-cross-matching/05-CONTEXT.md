# Phase 5: Classification & Cross-Matching - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Every segmented object from Phase 4 is identified against known astronomical catalogs (SIMBAD, NED, SDSS, Gaia), classified by ML with detailed subtypes, and scored for anomalousness. Truly novel objects are flagged with human-readable explanations. Results are stored with full provenance and exposed via basic API endpoints. Search UI, object detail pages, and knowledge graph integration belong to Phases 6-8.

</domain>

<decisions>
## Implementation Decisions

### Cross-match behavior
- Adaptive search radius based on object angular extent from segmentation — compact sources ~2-3 arcsec, extended sources scale up proportionally
- Keep ALL matches from ALL catalogs — every match stored with distance and confidence score
- Query SIMBAD, NED, SDSS, and Gaia in parallel (no priority order, no early exit)
- On catalog API failure: retry 3x with backoff, then mark that catalog as "not queried" for affected objects — pipeline continues with remaining catalogs; reprocessable later

### Classification taxonomy
- Detailed subtypes (spiral galaxy, elliptical galaxy, planetary nebula, emission nebula, main sequence star, white dwarf, etc.) — not just broad categories
- Use existing labeled astronomical datasets for training (researcher to investigate Galaxy Zoo, SDSS spectroscopic classifications, and other available labeled data)
- ML classifier runs on EVERY object, whether catalog-matched or not — enables disagreement detection and validates catalog matches
- Catalog classification is authoritative, but ML prediction is always stored alongside for comparison
- Persist full feature vectors (ellipticity, concentration, asymmetry, etc.) per object — powers anomaly detection (INTEL-01) and future analysis

### Anomaly sensitivity
- Cast a wide net — better to review 100 candidates and find 5 real anomalies than miss one
- Any single signal triggers a flag: feature vector outlier OR catalog disagreement OR no catalog match OR unusual morphology OR low ML confidence
- Every anomaly flag includes a human-readable explanation ("feature vector outlier in concentration index", "no catalog match within search radius", "ML confidence below threshold")
- Artifacts (diffraction spikes, cosmic rays, imaging artifacts) classified as "artifact" type by ML — NOT flagged as anomalies. Keeps the anomaly list clean for real discoveries.

### Result storage & API
- Core fields indexed as database columns (name, type, coordinates, magnitude, redshift) for fast querying
- Full catalog response stored as raw JSON blob alongside indexed fields — completeness without re-querying
- Basic API endpoints in this phase: get object classifications, get cross-matches by object ID, list anomalies — Phase 6 builds richer UI on top
- Full provenance tracking: classification timestamp, ML model version, feature extractor version, catalog query date
- Reclassification supported via append: new classification runs create new records alongside old ones, preserving full classification history per object

### Claude's Discretion
- Exact ML model architecture and training approach
- Feature vector engineering details
- Database schema design for classification/match tables
- API endpoint structure and response formats
- Anomaly score computation method
- Catalog query optimization and rate limiting strategy

</decisions>

<specifics>
## Specific Ideas

- User wants to leverage existing labeled astronomical datasets (Galaxy Zoo morphologies, SDSS spectroscopic classifications) for training the detailed subtype classifier — researcher should investigate what's available and how to use it
- Classification disagreements between ML and catalogs are valuable signal, not noise — store both, flag disagreements
- "Cast a wide net" for anomalies reflects a discovery-oriented philosophy — this is a tool for finding interesting things, not just confirming known ones

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-classification-cross-matching*
*Context gathered: 2026-02-23*
