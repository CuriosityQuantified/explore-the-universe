#!/usr/bin/env python3
"""Fail if graphify-out/graph.json is out of date with respect to the source tree.

Runs the AST-only rebuild (`graphify update .`, no LLM, no API key) and compares the
result against the committed graph. A difference means someone changed code without
rebuilding the graph, so agents querying it would get stale answers.

    python3 scripts/check_graph_fresh.py            # check, restore the committed graph
    python3 scripts/check_graph_fresh.py --write    # check, keep the rebuild so you can commit it

Only structural identity is compared — node ids and edge triples. Volatile metadata
such as `built_at_commit` is ignored, otherwise every commit that does not touch code
would still report the graph as stale.

LIMITATION: `graphify update` is AST-only, so this catches stale *code* but not stale
*docs*. A change to .planning/ needs a full `graphify extract .` to reach the graph.
See docs/knowledge-graph.md.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "graphify-out"
GRAPH = OUT / "graph.json"

# `graphify update` rewrites all of these, not just graph.json. Without --write the
# check must leave the working tree exactly as it found it, so every one gets restored
# — otherwise a read-only freshness check dirties the repo (and GRAPH_REPORT.md embeds
# a corpus word count that shifts whenever any doc changes).
ARTIFACTS = ("graph.json", "graph.html", "GRAPH_REPORT.md", ".graphify_labels.json",
             ".graphify_labels.json.sig", ".graphify_analysis.json")


def structure(path: Path) -> tuple[set, set]:
    graph = json.loads(path.read_text(encoding="utf-8"))
    nodes = {n["id"] for n in graph["nodes"]}
    edges = {
        (e.get("source"), e.get("target"), e.get("relation"))
        for e in graph["links"]
    }
    return nodes, edges


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="keep the rebuilt graph instead of restoring the committed one",
    )
    args = parser.parse_args()

    if not GRAPH.is_file():
        print(f"error: {GRAPH.relative_to(REPO_ROOT)} is missing", file=sys.stderr)
        print("Build it with: graphify extract . --code-only", file=sys.stderr)
        return 1

    if shutil.which("graphify") is None:
        print("error: graphify is not installed", file=sys.stderr)
        print('Install it with: pip install -e ".[graph]"', file=sys.stderr)
        return 1

    before_nodes, before_edges = structure(GRAPH)

    with tempfile.TemporaryDirectory() as tmp:
        backups = {}
        for name in ARTIFACTS:
            source = OUT / name
            if source.is_file():
                backups[name] = Path(tmp) / name
                shutil.copy2(source, backups[name])

        try:
            rebuild = subprocess.run(
                ["graphify", "update", "."],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            if rebuild.returncode != 0:
                print("error: `graphify update .` failed", file=sys.stderr)
                print(rebuild.stdout[-2000:], file=sys.stderr)
                print(rebuild.stderr[-2000:], file=sys.stderr)
                return 1

            after_nodes, after_edges = structure(GRAPH)
        finally:
            # Restore on the error path too — a failed rebuild can still have
            # overwritten some artifacts before giving up.
            if not args.write:
                for name, backup in backups.items():
                    shutil.copy2(backup, OUT / name)

    added_n, removed_n = after_nodes - before_nodes, before_nodes - after_nodes
    added_e, removed_e = after_edges - before_edges, before_edges - after_edges

    if not (added_n or removed_n or added_e or removed_e):
        print(f"Knowledge graph is current — {len(after_nodes)} nodes, {len(after_edges)} edges.")
        return 0

    print("Knowledge graph is STALE — an AST rebuild does not match the committed graph.")
    print(f"  nodes: +{len(added_n)} / -{len(removed_n)}")
    print(f"  edges: +{len(added_e)} / -{len(removed_e)}")

    for label, ids in (("would be added", added_n), ("would be removed", removed_n)):
        for node_id in sorted(ids)[:10]:
            print(f"    {label}: {node_id}")
        if len(ids) > 10:
            print(f"    ... and {len(ids) - 10} more {label}")

    print()
    print("Refresh it with:")
    print("    graphify update .           # code changes (no API key)")
    print("    graphify extract .          # if docs under .planning/ also changed")
    print("then commit graphify-out/.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
