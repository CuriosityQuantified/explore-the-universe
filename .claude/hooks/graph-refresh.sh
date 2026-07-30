#!/usr/bin/env bash
# SessionStart hook: keep the graphify knowledge graph in step with the source tree.
#
# `graphify update .` is AST-only (no LLM, no API key), takes about a second, and is
# byte-for-byte idempotent — so when nothing changed this leaves the working tree
# untouched and prints nothing.
#
# Never fails a session: if graphify is not installed, or the rebuild errors, this
# exits 0 silently. A knowledge graph is an optimisation, not a dependency.
#
# Registered in .claude/settings.json. See docs/knowledge-graph.md.

set -u

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

command -v graphify >/dev/null 2>&1 || exit 0
[ -f graphify-out/graph.json ] || exit 0

before=$(cksum graphify-out/graph.json 2>/dev/null)

# Discard output: the rebuild is chatty (tree-sitter warnings, tips) and none of it
# belongs in the session context. Real staleness is reported by the diff below.
if ! timeout 120 graphify update . >/dev/null 2>&1; then
    exit 0
fi

after=$(cksum graphify-out/graph.json 2>/dev/null)

if [ "$before" != "$after" ]; then
    nodes=$(python3 -c "import json;g=json.load(open('graphify-out/graph.json'));print(len(g['nodes']),len(g['links']))" 2>/dev/null)
    echo "Knowledge graph refreshed from the current source tree (${nodes:-updated} nodes/edges); graphify-out/ now has uncommitted changes to include in your next commit."
fi

exit 0
