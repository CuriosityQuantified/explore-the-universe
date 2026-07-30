# Explore the Universe

A galactic encyclopedia: ingests JWST and Rubin Observatory imagery, segments every
distinguishable object with SAM, classifies them against existing catalogs, and serves the
result through an interactive explorer.

- `pipeline/` — Celery tasks (ingest → tile → detect → segment → cutout)
- `api/` — FastAPI backend
- `shared/` — config, SQLAlchemy models, S3/MinIO helpers
- `web/` — Next.js sky viewer
- `.planning/` — phase-by-phase design record; `.planning/STATE.md` is the current position

Note: `neo4j` in this project stores the *astronomical object* graph (galaxy → system → star →
planet). That is unrelated to the graphify code graph described below.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

Caveat — the graph indexes `.planning/`, which describes code before it is written. Some nodes
carry a `source_file` that does not exist yet (Phase 5 catalog clients, classification, and
anomaly detection are the current cases). **Confirm a cited file exists before acting on it.**
See docs/knowledge-graph.md for the audit command.
