# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`.planning/PROJECT.md`** — core value proposition, requirements, constraints, key decisions.
- **`.planning/REQUIREMENTS.md`** — full requirement list with requirement IDs (INGEST-*, SEG-*, CLASS-*, BROWSE-*, GRAPH-*, INTEL-*, INFRA-*).
- **`.planning/ROADMAP.md`** — eight-phase delivery structure with per-phase success criteria.
- **`.planning/STATE.md`** — current position, accumulated decisions, pending todos, blockers.
- **`.planning/phases/<phase>/05-CONTEXT.md`** etc. — phase-specific implementation decisions for the current or target phase.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in (directory will be created as decisions are made).

If any of these files don't exist, proceed silently.

## Graphify first

This repo has a knowledge graph at `graphify-out/`. **Before reading raw source files**, orient yourself:

- `graphify query "<question>"` — scoped subgraph for a topic
- `graphify explain "<concept>"` — focused explanation of a node
- `graphify path "<A>" "<B>"` — relationship between two nodes

Only read raw files after graphify has oriented you, or to modify specific lines.

## File structure

Single-context repo:

```
/
├── .planning/          ← domain context, requirements, roadmap, phase plans
├── docs/
│   └── adr/           ← architectural decision records
└── shared/models.py   ← canonical data model
```

## Domain vocabulary

Use the project's domain terms exactly as defined in `.planning/`:

| Term | Meaning |
|------|---------|
| Observation | A JWST or Rubin Observatory exposure ingested from MAST or RSP |
| AstronomicalObject | A segmented object within an observation (galaxy, star, nebula, etc.) |
| CatalogCrossMatch | A record linking an AstronomicalObject to a match in an external catalog (SIMBAD, NED, SDSS, Gaia) |
| ObjectClassification | An ML classification record for an AstronomicalObject (append-only history) |
| pipeline | The Celery task chain (download → validate_wcs → tile → detect → segment → cutouts → cross_match → classify → anomalies) |
| segmentation mask | COCO RLE-encoded pixel mask per AstronomicalObject |
| feature vector | Morphological descriptor computed by statmorph (or SEP fallback) stored as JSONB |
| anomaly flag | Multi-signal flag on an object that does not match known categories |
| spatial hierarchy | The Neo4j graph relationship: galaxy → system → star → planet |

## Flag ADR conflicts

If your output contradicts an existing decision recorded in `.planning/STATE.md` or a phase CONTEXT file, surface it explicitly rather than silently overriding.
