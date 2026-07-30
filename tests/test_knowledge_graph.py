"""Guards on the committed graphify knowledge-graph integration.

These are static checks on committed files — they do not need graphify installed and
do not run an extraction. Their job is to catch the integration silently rotting,
most notably a re-run of `graphify install` clobbering the portable hook command
with a machine-specific absolute path.

See docs/knowledge-graph.md.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_JSON = REPO_ROOT / "graphify-out" / "graph.json"
MCP_CONFIG = REPO_ROOT / ".mcp.json"
CLAUDE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_graph_json_is_committed_and_parseable():
    assert GRAPH_JSON.is_file(), (
        "graphify-out/graph.json is missing. Rebuild it with `graphify extract . --code-only`."
    )
    graph = _load(GRAPH_JSON)

    # networkx node-link format: edges live under "links", not "edges".
    assert graph["nodes"], "graph has no nodes"
    assert graph["links"], "graph has no edges"


def test_graph_covers_the_pipeline_and_api_packages():
    graph = _load(GRAPH_JSON)
    sources = {n.get("source_file", "") for n in graph["nodes"]}

    for package in ("pipeline/", "api/", "shared/"):
        assert any(s.startswith(package) for s in sources), (
            f"no nodes from {package} — the graph is stale, run `graphify update .`"
        )


def test_graph_json_has_no_absolute_paths():
    """graph.json is committed, so it must not embed this checkout's location."""
    assert "/home/" not in GRAPH_JSON.read_text(encoding="utf-8")


def test_mcp_server_is_registered():
    servers = _load(MCP_CONFIG)["mcpServers"]
    assert "graphify" in servers
    assert servers["graphify"]["command"] == "graphify-mcp"


def test_sessionstart_refresh_hook_is_registered_and_executable():
    """The graph only stays fresh if this hook survives; `graphify install` rewrites
    settings.json and does not know about it."""
    hooks = _load(CLAUDE_SETTINGS)["hooks"]
    assert "SessionStart" in hooks, (
        "SessionStart refresh hook is missing — the graph will go stale silently"
    )

    commands = [h["command"] for entry in hooks["SessionStart"] for h in entry["hooks"]]
    assert any("graph-refresh.sh" in c for c in commands)

    script = REPO_ROOT / ".claude" / "hooks" / "graph-refresh.sh"
    assert script.is_file(), f"{script} is referenced by settings.json but missing"
    assert script.stat().st_mode & 0o111, f"{script} is not executable"


def test_freshness_checker_exists():
    """CI (.github/workflows/knowledge-graph.yml) shells out to this."""
    assert (REPO_ROOT / "scripts" / "check_graph_fresh.py").is_file()


@pytest.mark.parametrize("matcher", ["Bash|Grep", "Read|Glob"])
def test_pretooluse_hook_command_is_portable(matcher):
    """`graphify install` hardcodes an absolute interpreter path here.

    That path only exists on the machine that ran the installer, so a committed copy
    breaks every tool call for everyone else. The command must resolve graphify from
    PATH and no-op when it is absent.
    """
    entries = _load(CLAUDE_SETTINGS)["hooks"]["PreToolUse"]
    matching = [e for e in entries if e["matcher"] == matcher]
    assert matching, f"no PreToolUse hook registered for {matcher}"

    for hook in matching[0]["hooks"]:
        command = hook["command"]
        assert not command.startswith("/"), (
            f"hook for {matcher} uses an absolute path ({command!r}). "
            "Re-apply the portable form — see docs/knowledge-graph.md."
        )
        assert "command -v graphify" in command, (
            f"hook for {matcher} must degrade gracefully when graphify is not installed"
        )
