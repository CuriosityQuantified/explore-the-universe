# Feature Research

**Domain:** Astronomical data exploration platform + galactic encyclopedia
**Researched:** 2026-02-21
**Confidence:** MEDIUM-HIGH (based on analysis of 10+ existing platforms and recent research)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Zoomable sky map / image viewer** | Every astronomical visualization tool (WWT, Aladin, ESASky, Legacy Survey Viewer) provides map-like pan/zoom navigation. Users cannot evaluate spatial data without it. | HIGH | Must handle trillion+ pixel images. Use HiPS tiling standard (IVOA standard, adopted by WWT, Aladin, Stellarium, IPAC). Leaflet.js or OpenLayers on client side with pre-tiled HEALPix image pyramids on server side. Legacy Survey Viewer uses exactly this pattern (Leaflet + Django). |
| **FITS file support** | FITS is the universal format in astronomy. JWST and Rubin both deliver FITS. No FITS = no credibility. | MEDIUM | Need both server-side processing (astropy.io.fits) and client-side quick-look visualization (JS9 or Jdaviz integration). Must parse WCS headers for coordinate mapping. |
| **Multi-wavelength image layers** | ESASky, Aladin, and WWT all let users toggle between survey layers (optical, infrared, X-ray). JWST data inherently spans NIRCam, MIRI bands. | MEDIUM | HiPS standard supports this natively with 1100+ available surveys from CDS. Aladin Lite provides embeddable multi-layer viewer. Consider using Aladin Lite as base component rather than building from scratch. |
| **Catalog cross-matching** | SIMBAD has 20M+ objects; NED covers extragalactic; SDSS has hundreds of millions of sources. Users expect known objects to be identified. | MEDIUM | Use astroquery (Python) for SIMBAD, NED, VizieR, SDSS APIs. CDS X-Match service handles billion-row cross-matches efficiently. Requires accurate WCS extraction from FITS headers to convert pixel coords to sky coords (RA/Dec). |
| **Object search** | Every platform (NED, SIMBAD, SDSS SkyServer, ESASky) provides search by name, coordinates, or object type. Non-negotiable for any catalog-like tool. | LOW-MEDIUM | Search by: object name (resolve via SIMBAD/Sesame), sky coordinates (cone search), object type/class. Autocomplete with known catalog entries. |
| **Individual object detail pages** | NED, SIMBAD, SDSS, and HyperLEDA all provide per-object pages with properties, cross-IDs, bibliography, and imagery. This is the "encyclopedia" core promise. | MEDIUM | Must aggregate: cutout imagery, physical properties (magnitude, redshift, spectral type), catalog cross-references, source observation metadata. |
| **Data export / download** | MAST, SDSS CasJobs, ESASky all provide data download. Researchers expect to extract data for their own analysis. | LOW | Export formats: FITS cutouts, CSV/VOTable for catalog data, PNG for imagery. Provide API endpoints alongside UI downloads. |
| **Coordinate system support (WCS)** | Fundamental to astronomy. All professional tools display RA/Dec and support coordinate-based navigation. | LOW-MEDIUM | Extract WCS from FITS headers using astropy.wcs. Display coordinates on hover/click. Support common coordinate frames (ICRS, Galactic, Ecliptic). |
| **Data provenance / metadata** | Users need to know: which telescope, which instrument, which observation, what processing level. MAST and ESASky both surface this prominently. | LOW | Store and display: observation ID, instrument, filter, exposure time, PI, program ID, processing level. Link back to source archive (MAST). |

### Differentiators (Competitive Advantage)

Features that set this product apart from existing platforms. Aligned with the project's core value: "any image goes in, every object comes out segmented, classified, and explorable."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Automated SAM-based object segmentation** | No existing astronomical platform provides automatic universal segmentation of every distinguishable object in an image. Traditional source extraction (SExtractor, photutils) finds point/extended sources but does not produce pixel-perfect masks. SAM provides instance segmentation without domain-specific training. This is the project's primary technical differentiator. | HIGH | SAM has been validated for galaxy size estimation in Euclid images (2025 A&A paper). SAM 2 is 6x faster than original. SAM 3 adds concept-based prompting. Will likely need fine-tuning or prompt engineering for astronomical data since SAM was trained on natural images. Tiling strategy needed for large images. DeepDISC (Detectron2-based) is the closest existing approach but is research-only, not productized. |
| **Knowledge graph with spatial hierarchy** | No existing public tool provides a navigable graph connecting galaxies to their constituent systems, stars, and planets with typed relationships. NED/SIMBAD store flat catalogs; they do not expose a traversable hierarchy. This enables "zoom semantically" not just "zoom spatially." | HIGH | Graph structure: sky region -> galaxy cluster -> galaxy -> stellar system -> star/planet. Edge types: contains, orbits, is_member_of, is_near. Properties on nodes: photometry, spectral type, redshift, morphology. Neo4j or similar graph DB. Must start small (thousands of objects for POC) and architect for billions. |
| **AI-assisted natural language querying** | SDSS CasJobs requires SQL. SIMBAD has its own query language. No existing astronomical platform offers conversational data exploration. AstroSage-Llama (2025) achieves GPT-4o level performance on astronomy Q&A, proving feasibility. | MEDIUM-HIGH | RAG pipeline over the knowledge graph + catalog data. Text-to-query translation (natural language -> graph queries / SQL). Use LLM with astronomy fine-tuning or strong general model with domain-specific prompt engineering. RAG-based Slack bots for astronomy already exist (AAS 2025 presentation). |
| **Anomaly detection and novel object flagging** | Existing platforms do not automatically flag unusual objects. Astronomaly (active anomaly detection framework) exists as research software but is not integrated into any browsing platform. LSST brokers are building this for transients but not for general object morphology. | MEDIUM-HIGH | Multi-class Isolation Forests (2025 RASTI paper) on object feature vectors. Compare segmented object properties against known distributions. Flag outliers for review. Integrate with citizen-science-style "interesting object" voting. |
| **Temporal change tracking** | Rubin/LSST will image the southern sky every 3 nights. No current encyclopedia-style tool tracks how individual segmented objects change over time. LSST brokers (Lasair, Fink, ANTARES) handle transient alerts but do not provide visual before/after comparison at the object level. | HIGH | Requires: repeated observation alignment, difference imaging, object-level time series storage. Blink comparison UI (before/after slider). Change magnitude quantification. Dependency: requires the ingestion pipeline and segmentation to run repeatedly on overlapping fields. |
| **Visual knowledge graph explorer** | Graph visualization of astronomical relationships does not exist in any current tool. Would allow users to click an object and see its neighborhood: what galaxy it belongs to, nearby objects, similar objects by properties. | MEDIUM | Force-directed graph visualization (D3.js or Cytoscape.js). Filter by relationship type. Expand/collapse nodes. Link graph nodes to sky map locations and detail pages. |
| **Unified pipeline: image -> segmentation -> classification -> encyclopedia** | No existing tool provides the complete pipeline. MAST provides raw data. SExtractor/photutils extract sources. SIMBAD classifies. But no single platform chains these together automatically. This is the project's architectural differentiator. | HIGH | The pipeline IS the product. Each stage must work end-to-end: FITS ingestion -> tiling -> SAM segmentation -> WCS coordinate extraction -> catalog cross-match -> ML classification for unknowns -> knowledge graph insertion -> frontend rendering. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems. Deliberately NOT building these.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full LSST real-time ingestion (20TB/night)** | Completeness; "all the data" appeal | Requires massive infrastructure (petabyte storage, GPU clusters for SAM at scale). Unsustainable for self-funded POC. LSST brokers (Lasair, Fink) already handle the alert stream professionally. | Start with curated subsets of JWST deep fields and Rubin commissioning data. Design architecture for scale, but only process what's affordable. Add full ingestion when funding is secured. |
| **Telescope control / observation scheduling** | "End-to-end astronomy platform" scope creep | Completely different domain. Requires instrument APIs, queue management, weather systems. Out of scope per PROJECT.md. | Remain a passive data consumer. Link to existing scheduling tools (e.g., JWST APT) from object pages. |
| **Mobile native app** | Broader audience reach | Enormous development cost for a data-heavy visualization tool. Astronomical images require large screens. Touch-based pan/zoom on complex sky maps is inferior to mouse. | Build responsive web app that works acceptably on tablets. Mobile is explicitly out of scope per PROJECT.md. |
| **User-generated classifications / full citizen science platform** | Community engagement, Zooniverse model | Building a citizen science platform (project builder, workflow designer, talk forums, moderation tools) is a massive product in itself. Zooniverse has 2.7M+ users and decades of tooling. Cannot compete. | Provide a "flag this object" or "suggest classification" lightweight feedback mechanism. Partner with Zooniverse for formal citizen science campaigns rather than building a competing platform. |
| **Raw SQL/ADQL query interface** | Power users want maximum flexibility (SDSS CasJobs model) | Exposes database internals, creates security surface, requires query optimization for large datasets, intimidates non-technical users. SDSS CasJobs is powerful but notoriously hard to use. | Structured smart query builder with visual filters that generates queries internally. AI natural language interface for complex questions. Export query results for users who need to do their own analysis. |
| **Real-time collaborative editing/annotation** | Team science, shared workspace appeal | Requires WebSocket infrastructure, conflict resolution, permission management, presence indicators. Massive complexity for marginal value in a POC. | Single-user annotations saved to user account. Export/share annotations as static files. Add collaboration later if validated. |
| **3D universe navigation** | WWT has 3D mode; visually impressive | 3D rendering of astronomical data is technically demanding and often scientifically misleading (distances are poorly constrained for most objects). WebGL performance with millions of objects is challenging. WWT has years of investment in this. | 2D sky map with depth/distance as a filterable property, not a rendering axis. Link to WWT for users who want 3D exploration. |
| **Spectral analysis tools** | Professional astronomers need spectral fitting, line identification | Deep domain-specific tooling (specutils, PySpecKit, IRAF legacy). Would need to replicate years of specialist software. Not the project's core value. | Display basic spectral information from catalogs on object pages. Link to Jdaviz/specutils notebooks for detailed analysis. Provide FITS spectrum download for offline analysis. |

## Feature Dependencies

```
[FITS Ingestion Pipeline]
    |-- requires --> [WCS Coordinate Extraction]
    |                   |-- requires --> [Catalog Cross-Matching (SIMBAD/NED/SDSS)]
    |                   |                   |-- feeds --> [Object Classification]
    |                   |                   |-- feeds --> [Knowledge Graph Population]
    |                   |
    |                   |-- enables --> [Zoomable Sky Map (coordinate overlay)]
    |
    |-- requires --> [Image Tiling (HiPS/HEALPix)]
    |                   |-- enables --> [Zoomable Sky Map (image layers)]
    |                   |-- enables --> [Multi-wavelength Layer Toggle]
    |
    |-- requires --> [SAM Segmentation]
                        |-- requires --> [Image Tiling] (SAM needs manageable tile sizes)
                        |-- feeds --> [Object Detail Pages] (cutouts, masks)
                        |-- feeds --> [Knowledge Graph Population] (segmented objects as nodes)
                        |-- feeds --> [Anomaly Detection] (feature vectors from segmented objects)

[Knowledge Graph]
    |-- enables --> [Visual Graph Explorer]
    |-- enables --> [AI Natural Language Querying] (RAG over graph)
    |-- enables --> [Property-based Search/Filters]
    |-- enables --> [Spatial Hierarchy Navigation]

[Object Detail Pages]
    |-- requires --> [Knowledge Graph] (relationships, properties)
    |-- requires --> [Catalog Cross-Matching] (external references)
    |-- requires --> [SAM Segmentation] (object masks, cutouts)

[Temporal Change Tracking]
    |-- requires --> [FITS Ingestion Pipeline] (repeated observations)
    |-- requires --> [SAM Segmentation] (re-segmentation of same fields)
    |-- requires --> [Knowledge Graph] (object identity persistence across epochs)

[AI Natural Language Querying]
    |-- requires --> [Knowledge Graph] (structured data to query against)
    |-- requires --> [Object Search] (entity resolution)
    |-- enhances --> [Object Search] (natural language -> structured query)

[Anomaly Detection]
    |-- requires --> [SAM Segmentation] (object feature extraction)
    |-- requires --> [Catalog Cross-Matching] (to know what's "normal")
    |-- enhances --> [Object Detail Pages] (anomaly score display)
```

### Dependency Notes

- **SAM Segmentation requires Image Tiling:** SAM cannot process trillion-pixel images directly. Images must be tiled into manageable chunks (typically 1024x1024 or 2048x2048 for SAM). Segmentation results must be stitched across tile boundaries.
- **Knowledge Graph requires both Cross-Matching and Segmentation:** Objects enter the graph from segmentation (detection) and get enriched from catalog cross-matching (classification). Both pipelines must feed the graph.
- **Temporal Change Tracking requires everything else first:** This is the most dependent feature. It needs the full pipeline running repeatedly, plus object identity persistence across observation epochs. Defer to late phases.
- **AI Querying enhances Object Search:** The natural language interface translates user intent into structured queries against the knowledge graph. It requires the graph to be populated and queryable first.
- **Anomaly Detection conflicts with early-phase launch:** It requires sufficient baseline data and well-calibrated segmentation to define "normal" before it can flag "unusual." Ship after the pipeline has processed enough data.

## MVP Definition

### Launch With (v1)

Minimum viable product -- validate that the pipeline works end-to-end on a curated data subset.

- [ ] **FITS ingestion from MAST** -- Download and store JWST deep field observations. Without data, nothing else works.
- [ ] **WCS extraction and coordinate mapping** -- Convert pixel coordinates to sky coordinates. Foundation for all spatial features.
- [ ] **Image tiling (HiPS-compatible)** -- Pre-tile images into multi-resolution pyramids for performant web viewing.
- [ ] **Zoomable sky map viewer** -- Pan/zoom interface over tiled imagery. Use Aladin Lite or Leaflet + custom tile server. Core browsing experience.
- [ ] **SAM segmentation pipeline** -- Run SAM on tiled images, produce per-object masks. The primary technical differentiator.
- [ ] **Catalog cross-matching** -- Match segmented object coordinates against SIMBAD/NED. Identify known objects.
- [ ] **Basic object detail pages** -- Per-object page showing: cutout image, mask overlay, catalog matches, basic properties (coordinates, magnitude if available).
- [ ] **Basic object search** -- Search by name (SIMBAD resolution), coordinates (cone search), and object type.

### Add After Validation (v1.x)

Features to add once the core pipeline is validated and working.

- [ ] **Knowledge graph with spatial hierarchy** -- Trigger: Once enough objects are segmented and classified to make graph navigation meaningful (thousands of objects).
- [ ] **Visual knowledge graph explorer** -- Trigger: Once the knowledge graph has sufficient density to provide useful traversals.
- [ ] **Multi-wavelength layer toggle** -- Trigger: Once the tiling pipeline supports multiple surveys/bands for the same sky region.
- [ ] **ML classification for unknowns** -- Trigger: Once cross-matching reveals a meaningful population of unmatched objects that need classification.
- [ ] **Anomaly detection / novel object flagging** -- Trigger: Once the pipeline has processed enough objects to establish baseline distributions.
- [ ] **Structured smart query builder** -- Trigger: Once the knowledge graph supports property-based queries and users need more than basic search.
- [ ] **Data export (FITS cutouts, CSV, VOTable)** -- Trigger: Once users demonstrate need to take data out of the platform for external analysis.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **AI natural language querying** -- Why defer: Requires mature knowledge graph, significant LLM integration work, and clear user demand. Ship the structured query builder first.
- [ ] **Temporal change tracking** -- Why defer: Requires repeated observations of the same fields (Rubin data), the full pipeline running in production, and object identity persistence. Most complex feature.
- [ ] **Citizen-science-style "interesting object" feedback** -- Why defer: Need users first. Lightweight flagging mechanism, not a full Zooniverse competitor.
- [ ] **Statistical analysis dashboard** -- Why defer: Requires large catalog of segmented/classified objects. Distributions and correlations are meaningless with small datasets.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| FITS ingestion pipeline | HIGH | MEDIUM | P1 |
| WCS coordinate extraction | HIGH | LOW | P1 |
| Image tiling (HiPS) | HIGH | MEDIUM | P1 |
| Zoomable sky map viewer | HIGH | MEDIUM | P1 |
| SAM segmentation pipeline | HIGH | HIGH | P1 |
| Catalog cross-matching | HIGH | MEDIUM | P1 |
| Object detail pages | HIGH | MEDIUM | P1 |
| Object search (name/coords/type) | HIGH | LOW | P1 |
| Data provenance / metadata display | MEDIUM | LOW | P1 |
| Knowledge graph | HIGH | HIGH | P2 |
| Visual graph explorer | MEDIUM | MEDIUM | P2 |
| Multi-wavelength layers | MEDIUM | MEDIUM | P2 |
| ML classification (unknowns) | HIGH | HIGH | P2 |
| Anomaly detection | HIGH | HIGH | P2 |
| Smart query builder | MEDIUM | MEDIUM | P2 |
| Data export | MEDIUM | LOW | P2 |
| AI natural language querying | HIGH | HIGH | P3 |
| Temporal change tracking | HIGH | HIGH | P3 |
| Statistical analysis dashboard | MEDIUM | MEDIUM | P3 |
| Citizen feedback mechanism | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch -- validates the core pipeline and provides a usable browsing experience
- P2: Should have, add when pipeline is validated -- builds the "encyclopedia" and "discovery" layers
- P3: Nice to have, future consideration -- requires mature data and user base

## Competitor Feature Analysis

| Feature | WWT | Aladin/Lite | ESASky | Legacy Survey Viewer | MAST Portal | SDSS SkyServer | NED/SIMBAD | Zooniverse | **Our Approach** |
|---------|-----|-------------|--------|---------------------|-------------|----------------|------------|------------|-----------------|
| Zoomable sky map | Yes (3D + 2D) | Yes (HiPS) | Yes (HiPS) | Yes (Leaflet) | No (table-based) | Basic (Navigate) | No | No | Yes (HiPS, Aladin Lite or Leaflet) |
| Multi-wavelength layers | Yes | Yes (1100+ HiPS) | Yes | Limited | No | No | No | No | Yes (via HiPS standard) |
| Object search | Basic | Via SIMBAD | Yes | Limited | Yes | Yes (SQL) | Yes | By project | Yes (name, coords, type, natural language) |
| Object detail pages | No | Basic popup | Basic | Basic popup | Yes | Yes | Yes | Per-task | Yes (rich, aggregated from multiple sources) |
| Automatic object segmentation | No | No | No | No | No | No | No | No | **Yes (SAM-based, primary differentiator)** |
| Knowledge graph | No | No | No | No | No | No | No | No | **Yes (spatial hierarchy + properties)** |
| Anomaly detection | No | No | No | No | No | No | No | Volunteer-based | **Yes (automated ML + flagging)** |
| AI/NL querying | No | No | No | No | No | SQL only | Query language | No | **Yes (conversational, LLM-powered)** |
| Catalog cross-matching | No | Yes (CDS) | Yes | Limited | Yes | Yes | Yes (core feature) | No | Yes (automated pipeline stage) |
| FITS viewer | No | Limited | Yes | No | Yes (Jdaviz) | No | No | No | Yes (JS9 or Jdaviz integration) |
| Data download/export | No | Yes | Yes | Yes | Yes | Yes (CasJobs) | Yes | No | Yes |
| Temporal tracking | No | No | No | No | No | No | No | No | **Yes (future, with Rubin data)** |
| Citizen contributions | No | No | No | No | No | No | No | Yes (core feature) | Lightweight flagging only |
| 3D navigation | Yes (core) | No | No | No | No | No | No | No | No (deliberate anti-feature) |

**Key takeaway:** No existing platform combines automated segmentation, knowledge graph, and encyclopedia-style browsing. The four rightmost "Yes" entries in our column that are "No" across all competitors represent the differentiation surface. Existing tools are either archives (MAST, NED, SIMBAD), visualizers (WWT, Aladin, ESASky), or citizen science platforms (Zooniverse). None attempt the full pipeline from raw image to navigable encyclopedia.

## Sources

- [WorldWide Telescope](https://worldwidetelescope.org/home) -- Open source sky visualization, 3D navigation, multi-survey overlays
- [Aladin Sky Atlas / Aladin Lite](https://aladin.cds.unistra.fr/) -- HiPS-based sky browsing, 1100+ surveys, embeddable JS widget
- [ESASky](https://sci.esa.int/web/astrophysics/-/60099-explore-the-cosmos-with-esasky) -- Multi-mission discovery portal, 500K+ images, 1B+ catalog sources
- [Legacy Survey Viewer](https://www.legacysurvey.org/viewer) -- Leaflet.js + Django, 370M objects, map-like browsing
- [MAST Portal](https://archive.stsci.edu/) -- Jdaviz integration, cloud-based analysis (TIKE), multi-mission archive
- [SDSS SkyServer / CasJobs](https://skyserver.sdss.org/) -- SQL-based catalog query, batch processing, imaging query forms
- [SIMBAD](http://simbad.u-strasbg.fr/) -- 20M+ objects, cross-ID reference database, astroquery API
- [NED](https://ned.ipac.caltech.edu/) -- Extragalactic database, cross-references with SIMBAD
- [Zooniverse](https://www.zooniverse.org/) -- 2.7M volunteers, Project Builder, citizen science infrastructure
- [HiPS Standard (IVOA)](https://aladin.cds.unistra.fr/hips/) -- Hierarchical progressive surveys, multi-resolution tiling
- [JS9](https://js9.si.edu/) -- Web-based FITS viewer with zoom, pan, regions, WCS
- [SAM for galaxy segmentation (2025 A&A)](https://www.aanda.org/articles/aa/full_html/2025/01/aa52482-24/aa52482-24.html) -- Automated galaxy sizes in Euclid images using SAM
- [DeepDISC (MNRAS 2023)](https://academic.oup.com/mnras/article/526/1/1122/7273850) -- Detectron2-based detection, segmentation, classification for surveys
- [AstroSage-Llama / AstroMLab 3](https://arxiv.org/abs/2411.09012) -- Specialized 8B astronomy LLM achieving GPT-4o performance
- [Anomaly detection for LSST transients (MNRAS 2025)](https://academic.oup.com/mnras/article/543/1/351/8249279) -- Anomaly detection for time series data
- [Astronomical knowledge graphs (arXiv 2024)](https://arxiv.org/html/2406.01391v2) -- LLM-driven knowledge graph construction in astronomy
- [astroquery documentation](https://astroquery.readthedocs.io/en/latest/simbad/simbad.html) -- Python API for SIMBAD, NED, VizieR queries

---
*Feature research for: Astronomical data exploration platform + galactic encyclopedia*
*Researched: 2026-02-21*
