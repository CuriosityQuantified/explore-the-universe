# Knowledge Graph (graphify)

This repo is indexed by [graphify](https://github.com/Graphify-Labs/graphify), which turns the
codebase and the `.planning/` design record into a queryable knowledge graph under `graphify-out/`.

The point is to **query relationships instead of grepping**. Asking "what happens after
`detect_sources` finishes?" returns a scoped subgraph in a few hundred tokens instead of
opening half of `pipeline/tasks/`.

## Setup

```bash
pip install -e ".[graph]"     # installs graphifyy + the MCP server extra
```

That is all that is required to *query* the graph — `graphify-out/graph.json` is committed, so
queries work immediately after a clone.

To *rebuild* the graph you need nothing extra for code (tree-sitter runs locally), and an LLM
backend only for docs and images. See [Rebuilding](#rebuilding) below.

## Querying

| Command | What it does |
|---|---|
| `graphify query "how does a FITS file become tiles?"` | BFS over the graph, returns a scoped subgraph |
| `graphify explain "segment_sam"` | Plain-language summary of one node and its neighbours |
| `graphify path "ingest_observation" "generate_cutouts"` | Shortest path between two nodes |
| `graphify affected "Observation"` | Reverse traversal — what breaks if you change this |
| `graphify god-nodes --top 15` | The most connected nodes (architectural hubs) |

Useful flags: `--budget N` caps output tokens (default 2000), `--graph PATH` points at a
different `graph.json`.

## How agents use it

Three integration points are committed to the repo, so a fresh clone is wired up automatically:

1. **`CLAUDE.md`** — instructs the agent to prefer `graphify query` over grep for codebase
   questions.
2. **`.claude/settings.json`** — `PreToolUse` hooks that nudge the agent toward the graph when it
   reaches for Grep/Bash-search or reads a source file. The hook is written as
   `command -v graphify >/dev/null 2>&1 && graphify hook-guard search || true` so it silently
   no-ops for anyone who has not installed graphify, rather than erroring on every tool call.
   (The upstream installer hardcodes an absolute interpreter path here, which is not portable
   across machines — do not let `graphify install` overwrite this without re-applying the fix.)
3. **`.mcp.json`** — registers the `graphify-mcp` stdio server, exposing `query_graph`,
   `get_node`, `get_neighbors`, `get_community`, `god_nodes`, and `shortest_path` as MCP tools.

The `/graphify` slash command is available via `.claude/skills/graphify/`.

## Rebuilding

**After changing code** — deterministic, local, no API cost:

```bash
graphify update .
```

This re-runs the tree-sitter AST pass over changed files only. Run it after any refactor;
a stale graph is worse than no graph. If a refactor deleted code and the rebuild has fewer
nodes than before, graphify refuses to shrink the graph unless you pass `--force`.

**Full rebuild including docs** — needs an LLM backend for the markdown under `.planning/`
and `docs/`:

```bash
graphify extract . --backend claude-cli      # uses the local `claude` CLI, no API key
graphify extract . --backend anthropic       # uses ANTHROPIC_API_KEY
graphify extract . --code-only               # skips docs entirely, fully offline
```

`--code-only` is the fallback when no backend is available. It produces a smaller graph
(code symbols only) but needs no credentials and takes about a second.

**Regenerate the report/visualisation** without re-extracting:

```bash
graphify cluster-only .
```

### Staying fresh automatically

Two committed mechanisms keep the graph in step with the code, so nobody has to remember:

**1. Every Claude Code session** — `.claude/settings.json` registers a `SessionStart` hook that
runs `.claude/hooks/graph-refresh.sh`, which is just a guarded `graphify update .`. It takes
about a second, needs no API key, and is byte-for-byte idempotent, so when nothing changed it
touches nothing and prints nothing. It exits 0 silently if graphify is not installed — a
knowledge graph is an optimisation, not a dependency. When it *does* rebuild, it says so, and
`graphify-out/` will have changes to fold into your next commit.

**2. Every pull request** — `.github/workflows/knowledge-graph.yml` runs
`scripts/check_graph_fresh.py`, which rebuilds AST-only and fails if the result does not match
the committed graph. It compares node ids and edge triples, ignoring volatile metadata like
`built_at_commit`, so it only fires on real drift. Run it yourself before pushing:

```bash
python3 scripts/check_graph_fresh.py            # check only
python3 scripts/check_graph_fresh.py --write    # check and keep the rebuild to commit
```

The gate is AST-only, which is what makes it free to run. That means **it catches stale code
but not stale docs** — editing `.planning/` needs a full `graphify extract .` to reach the
graph, and no automation will remind you.

**3. Occasionally, by hand.** Two kinds of quality decay that no hook can fix:

```bash
graphify extract . --backend claude-cli   # after .planning/ or docs/ changes
graphify label .    --backend claude-cli  # refresh community names
```

`update` splits and merges communities as code moves, and names the new ones after their hub
node rather than calling an LLM — so labels drift from "Cutout Generation Task" toward
`detect_sources.py` over time. Harmless for querying, worse for navigation. Re-label when
`GRAPH_REPORT.md`'s community list stops reading like a table of contents.

### Optional: rebuild on every commit

```bash
graphify hook install     # post-commit + post-checkout git hooks
```

Not committed to the repo (git hooks live in `.git/`, which is not version controlled), so each
developer opts in individually. Largely redundant with the SessionStart hook unless you work
outside Claude Code.

### If graph.json starts conflicting

It is a generated file, so parallel branches will collide on it. graphify ships a union merge
driver:

```bash
git config merge.graphify.driver 'graphify merge-driver %O %A %B'
echo 'graphify-out/graph.json merge=graphify' >> .git/info/attributes
```

Not set up by default — with one active developer, re-running `graphify update .` after a merge
is simpler than maintaining the driver.

## Keeping it used

Three committed nudges, in increasing order of force:

1. **`CLAUDE.md`** states the rule: query the graph before grepping.
2. **`PreToolUse` hooks** inject that reminder at the moment an agent reaches for Grep, a
   Bash search, or a raw `Read`. This is what does the real work — it arrives exactly when the
   agent is about to do the wrong thing, rather than thousands of tokens earlier.
3. **The MCP server** exposes the graph as first-class tools, so querying is a tool call rather
   than a shell command an agent has to remember the syntax for.

Deliberately *not* enabled: graphify's `--strict` mode, which hard-denies the first raw file
read per session until a query happens. It is one flag away (`graphify install --project
--strict --platform claude`, then re-apply the portable hook command — see below), but blocking
a real tool call to enforce a convention is a large hammer, and the soft nudge is being followed.

To check whether it is actually earning its keep:

```bash
graphify benchmark                 # token reduction vs reading raw files (26.6x at last run)
GRAPHIFY_QUERY_LOG_ENABLE=1 ...    # log every query to ~/.cache/graphify-queries.log
```

Query logging is off by default and writes outside the repo. Turn it on for a week if you want
evidence of real usage rather than a number from a synthetic benchmark.

## What is committed

| Path | Committed | Why |
|---|---|---|
| `graphify-out/graph.json` | yes | The queryable artifact — makes a fresh clone useful immediately |
| `graphify-out/.graphify_analysis.json` | yes | Community/centrality analysis that accompanies the graph |
| `graphify-out/.graphify_labels.json{,.sig}` | yes | LLM-generated community names — committed so a clone gets them without re-running the LLM |
| `graphify-out/GRAPH_REPORT.md` | yes | Human-readable architecture summary |
| `graphify-out/graph.html` | yes | Interactive visualisation — open directly in a browser (loads vis-network from unpkg.com, so it needs network access to render) |
| `graphify-out/manifest.json` | no | Incremental-build state keyed on local mtimes |
| `graphify-out/cache/` | no | AST + semantic caches |
| `graphify-out/.graphify_root` | no | Absolute path to this checkout |
| `graphify-out/memory/`, `reflections/` | no | Per-developer query memory |

`graph.json` is a generated file that several people may regenerate independently, so it will
conflict on merge. graphify ships a union merge driver for exactly this:

```bash
git config merge.graphify.driver 'graphify merge-driver %O %A %B'
echo 'graphify-out/graph.json merge=graphify' >> .git/info/attributes
```

## Caveats

### Planned code appears as if it exists

This is the one that will bite you. The semantic pass indexes `.planning/`, and the phase PLAN
documents describe files *before they are written*. The extractor attributes those nodes to the
source path the plan names, so the graph contains entries like `query_gaia_region` at
`pipeline/catalog_clients/gaia_client.py` — a file that does not exist yet.

A full `graphify extract` introduced **31 such nodes across 12 files**, all Phase 5
(classification & cross-matching) work that is planned but not implemented. Ask the graph
"how are objects cross-matched against catalogs?" and you get a confident, detailed answer
describing code nobody has written.

**`graphify update .` prunes them.** The AST pass finds no such files and drops the nodes,
while leaving the doc-derived nodes intact — measured at 31 → 0 phantoms with `.planning/`
coverage going *up* (145 → 156 nodes). Since the SessionStart hook runs `update` on every
session, phantoms introduced by a full extract are cleared automatically. They only
reappear if you re-run `graphify extract` and do not follow it with an update.

Re-check at any time:

```bash
python3 -c "
import json, os
from collections import Counter
nodes = json.load(open('graphify-out/graph.json'))['nodes']
missing = Counter(n['source_file'] for n in nodes
                  if n.get('source_file') and not os.path.exists(n['source_file']))
print(f'{sum(missing.values())} nodes across {len(missing)} non-existent files')
for f, c in missing.most_common(): print(f'  {c:3d}  {f}')
"
```

This should normally print zero. If it does not, run `graphify update .`. If a phantom
survives an update, the file genuinely is referenced by code that expects it to exist.

**Before acting on a graph result, confirm the cited file exists.**

### Other things to know

- **The graph reflects the last rebuild, not the working tree.** `graphify query` will happily
  describe code you just deleted. Re-run `graphify update .` after edits. `GRAPH_REPORT.md`
  records the commit it was built from — compare against `git rev-parse HEAD`.
- **Two different graphs live in this project.** This one indexes *source code and docs*. The
  Neo4j graph described in `.planning/` indexes *astronomical objects* (galaxy → system → star →
  planet). They are unrelated; don't wire them together.
- **7% of edges are `INFERRED`** (avg confidence 0.65) rather than extracted from an AST. Edges
  carry their provenance — `EXTRACTED`, `INFERRED`, or `AMBIGUOUS` — and `graphify explain`
  prints it. Treat `INFERRED` as a hint, not a fact.
- **`settings.json` and `.planning/config.json` produce zero nodes** and are absent from the
  graph — graphify has no extractor for plain JSON config. Harmless, but it means the graph is
  not a complete file inventory.
- **The semantic pass mis-attributes some nodes.** The last run dropped 43 nodes that the model
  assigned to files it was never given. graphify catches and discards these itself; the count is
  printed at the end of `graphify extract`.
