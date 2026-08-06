# Summary

<!-- What does this PR do, and why? One or two sentences. -->

Closes #<!-- ticket number -->

## Changes

<!-- Bullet the notable changes. Call out anything reviewers should look at closely. -->

-

## Type of change

- [ ] ✨ Feature (new functionality)
- [ ] 🐛 Bug fix
- [ ] 🎨 UI / styling
- [ ] 📝 Docs
- [ ] 🔧 Tooling / CI / chore
- [ ] ♻️ Refactor (no behavior change)

## How was this tested?

<!-- Exact commands, not "tests pass". The CI gates are:
     - Python:  docker compose up -d --wait && python -m alembic upgrade head &&
                python -m pytest -m "not slow"
     - Web:     cd web && npm ci && npm run build
     The `slow` marker is the full MAST pipeline integration — never run in CI,
     manual only. Tests must stay offline by construction (no live network). -->

- [ ] Python tests: `python -m pytest -m "not slow"` (expect 21 passed)
- [ ] Web build: `npm run build` succeeds
- [ ] Manual flows exercised (list them)

## Screenshots

<!-- For UI changes: before/after, including a narrow viewport if the view is
     responsive. Delete this section otherwise. -->

## Checklist

- [ ] **Ticket binding** — the diff matches the issue's acceptance criteria; no
      scope creep, no unrelated files. (The issue body is the spec.)
- [ ] **Graph fresh** — `graphify update .` ran and `graphify-out/` is in this
      diff; `python3 scripts/check_graph_fresh.py` reports "current". CI's
      knowledge-graph.yml fails otherwise. If it reports "no topology changes,
      outputs left untouched", that is fine — but confirm the label.
- [ ] **Migrations** — if the schema changed, a new `alembic` migration is
      included and `alembic upgrade head` runs clean from an empty DB.
- [ ] **No secrets** — variable names only, never values (MAST token, S3
      credentials, Neo4j password are all dev defaults in `shared/config.py`;
      nothing real in the diff). Checked the full diff.
- [ ] **Tests offline by construction** — no test hits the live network; the
      MAST-download suite stays behind the `slow` marker.
- [ ] **CI green** — all three checks pass on this branch: Python tests, Web
      build, Knowledge graph.
- [ ] **Docs updated** where relevant (`.planning/`, `docs/`, `CLAUDE.md`
      agent-skills block).
- [ ] **Deviations** — anything done differently from the issue's checklist is
      called out in the PR description, with the reason.

## Notes for the issue-worker

<!-- Delete this section for human-authored PRs. -->

- Acceptance criteria addressed: (checklist from the issue)
- Files changed: (paths only)
- Deviations from spec: (or "none")
- CI/CD added or strengthened: (named jobs touched in .github/workflows/)
