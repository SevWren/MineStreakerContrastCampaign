# Contributing

## Prerequisites

- **Python:** 3.10, 3.11, or 3.12. Python 3.13+ is not yet supported for pre-built
  `pygame` wheels — see `requirements.txt` for the workaround.
- **Dependencies:** `pip install -r requirements.txt`
- **Developer setup:** `docs/DEVELOPER_SETUP.md`

For AI agents (Claude, Gemini, etc.), the binding instruction sets are `CLAUDE.md`,
`AGENTS.md`, and `GEMINI.md` at repo root. All contribution rules below apply to both
humans and agents.

---

## Branch Naming

| Prefix | Use for |
|---|---|
| `feature/<name>` | New features |
| `fix/<name>` | Bug fixes |
| `docs/<name>` | Documentation-only changes |
| `test/<name>` | Test additions or fixes |
| `perf/<name>` | Performance improvements |
| `working-changes` | Active development branch (current) |

Never commit directly to `main` or `frontend-game-mockup`.

---

## Commit Message Format

- Use imperative mood: `Add`, `Fix`, `Update`, `Remove` — not `Added`, `Fixed`.
- Keep the subject line under 72 characters.
- Reference the relevant doc or bug tracker entry when applicable (e.g., `Fixes BUGS.md § FA-023`).
- Always include the co-author line:

```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**Example:**
```
Fix figsize in explained_report_artifact_contract.md

Contract doc had (22, 14.5) but report.py and AGENTS.md both
specify (24, 15.5). Updated contract doc to match source of truth.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

---

## Pre-Merge Checklist

Before opening a PR or merging, verify all of the following:

- [ ] All pipeline contract tests pass: `python -m unittest discover -s tests -p "test_*.py"`
- [ ] All gameworks tests pass (headless): `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v`
- [ ] No pyflakes issues: `pyflakes gameworks/ gameworks/tests/`
- [ ] No hardcoded local paths (e.g., `C:\Users\`, `D:\Github\`) in any committed file
- [ ] If JSON output fields changed: schema doc in `docs/json_schema/` is updated
- [ ] If a bug was resolved: `gameworks/docs/BUGS.md` status is updated
- [ ] If a new doc was added: `docs/DOCS_INDEX.md` entry is added
- [ ] No artifacts under `results/` are committed (directory is git-ignored)

---

## Where to Add Tests

| What changed | Where to add tests |
|---|---|
| Pipeline module (`core.py`, `repair.py`, etc.) | `tests/test_<module_name>.py` |
| Pipeline JSON output schema | `tests/test_<artifact>_contract.py` |
| Gameworks engine or board logic | `gameworks/tests/unit/` |
| Gameworks renderer | `gameworks/tests/renderer/` |
| Gameworks CLI | `gameworks/tests/cli/` |
| Gameworks integration | `gameworks/tests/integration/` |
| Import boundary (engine must not import pygame) | `gameworks/tests/architecture/` |
| Demo subsystem | `tests/demo/iter9_visual_solver/` |

See `docs/TESTING_STRATEGY.md` for the full test strategy and runner commands.

---

## Documentation Standards

- All non-archived active docs are indexed in `docs/DOCS_INDEX.md`. Add an entry when
  creating a new document.
- Do not embed hardcoded file system paths, run IDs, or session-specific values in docs.
  Use generic placeholders like `<run_id>`, `<board>`, `results/iter9/<run_id>/`.
- If you update a schema constant (e.g., `figsize`, `SCHEMA_VERSION`), update both the
  code and the corresponding contract/schema doc in the same commit.
- For gameworks, `gameworks/docs/` is the self-contained documentation tree. Do not
  duplicate gameworks contracts in root `docs/`.

---

## Archival Policy

Documents are archived (moved to `archives/`) when they meet the criteria in
`docs/DOCS_INDEX.md § Archival Criteria`. In brief: a doc is archivable when it
describes completed, non-reversible work with no ongoing maintenance requirement.

Archived documents are **not deleted**. They serve as historical reference. Do not
delete docs that may be needed for future archaeology.

---

## Module Ownership Boundaries

These are hard rules, not style guidelines:

| Module | Must NOT import |
|---|---|
| `engine.py` | `pygame`, `renderer`, `main` |
| `renderer.py` | `main`, pipeline modules |
| `core.py`, `sa.py` | Any I/O, `pygame`, mutable globals |
| `report.py` | Pipeline route decision logic |
| `pipeline.py` | Report rendering logic |

Crossing a boundary is a bug. The architecture boundary test in
`gameworks/tests/architecture/` will catch `engine.py` importing `pygame`.

---

## Reporting Bugs

Add entries to the appropriate tracker:
- **Gameworks bugs:** `gameworks/docs/BUGS.md` (canonical flat register)
- **Pipeline backlog items:** `docs/back_log.md`
- **External consumer impact** (schema field changes): `for_user_review.md`
