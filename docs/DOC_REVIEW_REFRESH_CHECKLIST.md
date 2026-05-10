# Documentation Review & Refresh Checklist

**Type**: Reusable agentic runbook — execute on every feature merge, sprint end, or on-demand
**Scope**: All documentation in this repository
**Agent instructions**: Each step contains explicit commands to run, files to read, comparisons to make, and edits to perform. No step is complete until its verification command produces a clean result.

---

## How to Use This Checklist

Run this checklist in order. Each phase is independently executable. Mark each item `[x]` as you complete it. Reset all items to `[ ]` before the next run. Never skip a phase — later phases depend on Phase 0 establishing ground truth.

**Trigger conditions** (any one is sufficient to run this checklist):
- A feature branch is merged into `frontend-game-mockup`
- A bug is fixed and committed
- A constant, function signature, or class is renamed or removed
- A new file is added to `gameworks/`
- A new test file is added or test counts change
- `gameworks/__init__.py` version is bumped
- Scheduled: once per sprint regardless of changes

---

## Phase 0 — Establish Ground Truth

*Purpose: before touching any doc, capture the current state of the code so every doc comparison is against reality, not memory.*

- [ ] **Read `gameworks/__init__.py`** — record the current `__version__` string. Every doc that contains a version string must match this value exactly.
  ```bash
  grep "__version__" gameworks/__init__.py
  ```

- [ ] **Count all passing tests** — record the exact number. Any doc that cites a test count must be updated to this number.
  ```bash
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | tail -3
  ```

- [ ] **List all public symbols in `engine.py`** — every class, function, constant, and dataclass at module level. Any doc that lists the public API must be reconciled against this list.
  ```bash
  grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/engine.py
  ```

- [ ] **List all public symbols in `renderer.py`**
  ```bash
  grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/renderer.py
  ```

- [ ] **List all public symbols in `main.py`**
  ```bash
  grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/main.py
  ```

- [ ] **List all test files and their test counts**
  ```bash
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ --collect-only -q 2>&1 | grep "::"  | sed 's/::.*/::/g' | sort | uniq -c | sort -rn | head -30
  ```

- [ ] **List all currently failing tests** — these must match the known pre-existing failure list in `TEST_GAP_ANALYSIS.md`. Any new failures are regressions to fix before proceeding.
  ```bash
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | grep FAILED
  ```

- [ ] **List all action strings returned by `handle_event()`** — any doc that lists the action string contract must match this list.
  ```bash
  grep -n "return \"" gameworks/renderer.py | grep -v "#"
  ```

- [ ] **List all CLI flags** — any doc that describes CLI usage must match.
  ```bash
  grep -n "add_argument" gameworks/main.py
  ```

- [ ] **List all colour constants** (`C` dict) — any doc describing the colour palette must match.
  ```bash
  grep -n "^\s\+[a-z_]\+\s*=(" gameworks/renderer.py | head -40
  ```

- [ ] **List all files in `gameworks/docs/`**
  ```bash
  ls gameworks/docs/
  ```

- [ ] **List all files in `docs/`**
  ```bash
  find docs/ -name "*.md" | sort
  ```

---

## Phase 1 — Version Consistency

*Every document that contains a version string must match `__version__` from Phase 0.*

- [ ] **`gameworks/docs/CHANGELOG.md`** — confirm the most recent release header matches `__version__`. If the version was bumped since the last CHANGELOG entry, add a new entry now.
  ```bash
  head -10 gameworks/docs/CHANGELOG.md
  ```

- [ ] **`gameworks/docs/API_REFERENCE.md`** — find the `__version__` block and confirm it matches.
  ```bash
  grep "__version__" gameworks/docs/API_REFERENCE.md
  ```

- [ ] **`gameworks/docs/BUGS.md`** — find the `**Package version:**` header line and confirm it matches.
  ```bash
  grep "Package version" gameworks/docs/BUGS.md
  ```

- [ ] **`gameworks/docs/INDEX.md`** — find any version reference in the footer line (`*Gameworks v…*`) and confirm it matches.
  ```bash
  grep "v0\." gameworks/docs/INDEX.md
  ```

- [ ] **`docs/DOCS_INDEX.md`** — confirm no stale version references exist.
  ```bash
  grep "v0\." docs/DOCS_INDEX.md
  ```

---

## Phase 2 — API Reference Accuracy

*`gameworks/docs/API_REFERENCE.md` is the single source of truth for the public API. It must reflect the current code exactly.*

- [ ] **Cross-reference every `engine.py` public class against the API doc**
  Read `gameworks/docs/API_REFERENCE.md` sections for `CellState`, `Board`, `MoveResult`, `GameEngine`. For each: confirm every public method, property, and parameter listed matches the current source. Add any missing entries. Remove any entries for deleted symbols.
  ```bash
  grep -n "^class \|^    def \|^    @property" gameworks/engine.py | grep -v "_"
  ```

- [ ] **Confirm all new dataclasses are documented** — run the ground-truth symbol list from Phase 0 against the API Reference table of contents.
  ```bash
  grep "^@dataclass\|^class " gameworks/engine.py
  ```

- [ ] **Confirm `save_game_state`, `load_game_state`, `SaveResult`, `LoadResult`, `Board.from_arrays`, `SAVE_SCHEMA_VERSION`, `preflight_check` are present** — these are required by `FEATURE_SAVE_RESUME_LOAD.md` Phase 4 but not yet implemented. If the feature branch has been merged, add them now. If not, add a `(pending feature/save-resume-load)` stub.
  ```bash
  grep -n "save_game_state\|load_game_state\|SaveResult\|LoadResult\|from_arrays\|SAVE_SCHEMA\|preflight_check" gameworks/docs/API_REFERENCE.md
  ```

- [ ] **Confirm `_draw_cell` signature note is current** — v0.1.1 changed the signature from accepting a `CellState` to accepting raw numpy fields. The API doc has a note on this. Confirm it still accurately describes the current signature.
  ```bash
  grep -n "_draw_cell" gameworks/renderer.py | head -5
  grep -n "_draw_cell" gameworks/docs/API_REFERENCE.md | head -5
  ```

- [ ] **Confirm all action strings listed in the API doc match the ground-truth list from Phase 0.** Any string present in the doc but absent from the code is a phantom. Any string in the code but absent from the doc is a gap.

- [ ] **Confirm all CLI flags listed in the API doc match the ground-truth list from Phase 0.**

- [ ] **Confirm `handle_event()` return type contract is accurate** — the doc must state that `None` is returned for internal-state-only events.
  ```bash
  grep -n "handle_event\|return None\|return \"" gameworks/renderer.py | head -20
  ```

---

## Phase 3 — ARCHITECTURE.md Accuracy

*`gameworks/docs/ARCHITECTURE.md` must reflect the current module structure, state machine, and data flows.*

- [ ] **Verify the ASCII data flow diagram** — read the diagram in ARCHITECTURE.md, then read the actual imports and class relationships. Confirm every arrow in the diagram reflects a real dependency or call in the code.
  ```bash
  grep -n "^from\|^import" gameworks/engine.py gameworks/renderer.py gameworks/main.py
  ```

- [ ] **Confirm module responsibility lists are current** — the "Module Responsibilities" section lists what each file owns. Confirm no responsibility has moved to a different file since the last update.

- [ ] **Confirm the `GameLoop` state machine diagram is current** — states are `MENU → PLAYING → RESULT → MENU`. If any new state or transition has been added, update the diagram.
  ```bash
  grep -n "MENU\|PLAYING\|RESULT\|_state" gameworks/main.py | head -20
  ```

- [ ] **Add save/load data flow if `feature/save-resume-load` has been merged** — check for `save_game_state` in `engine.py`. If present, add the data flow: `GameLoop._save_state() → engine.save_game_state() → .mscsave` and `--resume → preflight_check() → engine.load_game_state() → GameLoop._start_game(resumed=True)`.
  ```bash
  grep -n "save_game_state" gameworks/engine.py
  ```

- [ ] **Confirm the "Key design choices" callouts are still accurate** — specifically: (a) mine hits are penalties not game-over, (b) renderer returns action strings, (c) `GameLoop` is the dispatcher.

---

## Phase 4 — CHANGELOG.md Currency

*`gameworks/docs/CHANGELOG.md` must have an entry for every commit that changed behaviour, API, or constants since the last entry.*

- [ ] **Get all commits since the last CHANGELOG entry date**
  ```bash
  git log --oneline --since="$(grep '^\## \[' gameworks/docs/CHANGELOG.md | head -1 | grep -oP '\d{4}-\d{2}-\d{2}')" -- gameworks/
  ```

- [ ] **For each commit, determine if it requires a CHANGELOG entry** — entries are required for: new features, API changes, constant value changes, bug fixes, performance improvements, and test suite changes. Entries are NOT required for: pure doc edits, whitespace, comment-only changes.

- [ ] **Confirm colour palette changes are logged** — commits `84160f9` changed `tile_reveal` and `flag_red`. Verify these appear in the CHANGELOG under the current version.
  ```bash
  grep -n "tile_reveal\|flag_red\|colour\|color.*palette\|cell.*background\|flag.*white" gameworks/docs/CHANGELOG.md
  ```

- [ ] **Confirm dynamic zoom-out floor feature is logged** — commit `9ada935` added the dynamic `min_fit_tile` floor. Verify this appears in the CHANGELOG.
  ```bash
  grep -n "zoom\|min_fit_tile\|dynamic.*floor\|viewport.*fit" gameworks/docs/CHANGELOG.md
  ```

- [ ] **Confirm the CHANGELOG entry format matches Keep a Changelog** — every entry must have `### Added`, `### Changed`, `### Fixed`, or `### Removed` subsections. No freeform paragraphs without a subsection header.

---

## Phase 5 — BUGS.md Currency

*`gameworks/docs/BUGS.md` is the canonical open bug register. It must accurately reflect which bugs are open, closed, and won't-fix.*

- [ ] **Check FA-001 through FA-005 and H-005 status** — commits `437f2d5` (remote) resolved FA-003, FA-004, and H-005. Verify their status in BUGS.md. If still marked OPEN but fixed, update to `RESOLVED — <commit-sha>`.
  ```bash
  grep -n "FA-003\|FA-004\|H-005" gameworks/docs/BUGS.md | head -10
  git log --oneline | grep -i "FA-003\|FA-004\|H-005\|videoresize\|panel.*intercept\|save.*button" | head -5
  ```

- [ ] **Check FA-001 and FA-002 status** — victory modal and timer. Confirm whether these were resolved in any recent commit.
  ```bash
  git log --oneline | grep -i "victory\|modal\|FA-001\|FA-002\|elapsed\|timer" | head -5
  grep -n "FA-001\|FA-002" gameworks/docs/BUGS.md | head -6
  ```

- [ ] **Update `**Last updated:**` date and `**Total open:**` count** — count open bugs (not RESOLVED, not WONT-FIX) from the quick-reference table and update the header.
  ```bash
  grep -c "| OPEN" gameworks/docs/BUGS.md
  ```

- [ ] **Confirm DP-R6 (`preflight_check` missing) status** — `FEATURE_SAVE_RESUME_LOAD.md` Step 13 creates `preflight_check()`. If the feature has been merged, mark DP-R6 as resolved.
  ```bash
  grep -n "def preflight_check" gameworks/main.py
  grep -n "DP-R6" gameworks/docs/BUGS.md | head -3
  ```

---

## Phase 6 — GAME_DESIGN.md Currency

*`gameworks/docs/GAME_DESIGN.md` documents rules, scoring constants, board modes, and win conditions.*

- [ ] **Verify all scoring constants match `engine.py`** — read `REVEAL_POINTS`, `CORRECT_FLAG_BONUS`, `WRONG_FLAG_PENALTY`, `MINE_HIT_PENALTY`, `STREAK_TIERS` from the source and confirm each value in the doc matches exactly.
  ```bash
  grep -n "REVEAL_POINTS\|CORRECT_FLAG\|WRONG_FLAG\|MINE_HIT\|STREAK_TIERS" gameworks/engine.py
  grep -n "REVEAL_POINTS\|CORRECT_FLAG\|WRONG_FLAG\|MINE_HIT\|STREAK_TIERS" gameworks/docs/GAME_DESIGN.md
  ```

- [ ] **Verify win/loss condition table is current** — there is no lose state; mine hits are penalties. Confirm the doc reflects this.

- [ ] **Verify board modes list is complete** — modes are `random`, `npy`, `image`. Confirm all three are documented with their CLI flags.
  ```bash
  grep -n "mode.*=\|\"random\"\|\"npy\"\|\"image\"" gameworks/engine.py | grep "GameEngine\|mode" | head -10
  ```

- [ ] **Add Save & Resume section if `feature/save-resume-load` has been merged** — check for `save_game_state` in code; if present, document what the player saves, what is not saved, and how to resume.
  ```bash
  grep -n "save_game_state" gameworks/engine.py
  ```

---

## Phase 7 — DEVELOPER_GUIDE.md Currency

*`gameworks/docs/DEVELOPER_GUIDE.md` must reflect the current development setup, test commands, and extension patterns.*

- [ ] **Verify the test run command is current and produces the expected output**
  ```bash
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -v 2>&1 | tail -5
  ```
  Confirm the command shown in the guide matches what was just run.

- [ ] **Verify the known-failing test list** — the guide (and `TEST_GAP_ANALYSIS.md`) lists 4 animation timing failures. Confirm the count and test names still match.
  ```bash
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/renderer/test_animations.py -v 2>&1 | grep FAILED
  ```

- [ ] **Verify `renderer_large` fixture documentation** — `conftest.py` now has `renderer_large` (300×370) and `renderer_panel_large` (40×30). Any guide text that describes `renderer_large` as a 40×30 fixture must be updated.
  ```bash
  grep -n "renderer_large\|renderer_panel_large" gameworks/tests/renderer/conftest.py
  grep -n "renderer_large\|40.*30\|300.*370" gameworks/docs/DEVELOPER_GUIDE.md
  ```

- [ ] **Verify the Windows test command** — the guide must include the Windows-equivalent test command using `set SDL_VIDEODRIVER=dummy`.

- [ ] **Verify Python version requirements** — confirm the listed supported Python range still applies.
  ```bash
  python --version
  ```

---

## Phase 8 — TEST_GAP_ANALYSIS.md Currency

*`gameworks/docs/TEST_GAP_ANALYSIS.md` documents test health, coverage gaps, and known failures.*

- [ ] **Update total test count** — replace the stale count with the value captured in Phase 0.

- [ ] **Update passing/failing breakdown** — recalculate from Phase 0 results.

- [ ] **Confirm known-failing animation tests are still the only failures** — if any new failures exist, they must be added to the gap analysis, not silently absorbed.

- [ ] **Confirm the "Missing test files" section matches reality** — the doc lists tests pending for R2, R3, R6, R8, R9. Confirm each is still pending (not yet implemented) or mark as completed.
  ```bash
  ls gameworks/tests/unit/ gameworks/tests/cli/ gameworks/tests/integration/
  ```

- [ ] **Add new test files to the analysis** — `test_zoom.py` and `test_save_resume.py` (if merged) must appear in the test health breakdown.
  ```bash
  ls gameworks/tests/renderer/
  ```

---

## Phase 9 — DESIGN_PATTERNS.md Currency

*`gameworks/docs/DESIGN_PATTERNS.md` audits 12 patterns (P1–P12) against the codebase. Pattern gaps must be updated when code closes them.*

- [ ] **Check P8 — Atomic File I/O** — currently listed as a gap. If `save_game_state` with `os.replace` has been merged, mark P8 as **PRESENT** and update the alignment table.
  ```bash
  grep -n "os.replace\|atomic" gameworks/engine.py
  grep -n "P8\|Atomic" gameworks/docs/DESIGN_PATTERNS.md | head -5
  ```

- [ ] **Check P9 — Versioned Schema Strings** — currently listed as a gap. If `SAVE_SCHEMA_VERSION` has been merged, mark P9 as **PRESENT**.
  ```bash
  grep -n "SAVE_SCHEMA_VERSION\|SCHEMA_VERSION" gameworks/engine.py
  grep -n "P9\|Versioned Schema" gameworks/docs/DESIGN_PATTERNS.md | head -5
  ```

- [ ] **Check P6 — Warmup-and-Verify (preflight)** — currently a gap. If `preflight_check()` has been merged, mark P6 as **PRESENT**.
  ```bash
  grep -n "def preflight_check" gameworks/main.py
  grep -n "P6\|preflight\|Warmup" gameworks/docs/DESIGN_PATTERNS.md | head -5
  ```

- [ ] **Update the alignment summary table** — every row must reflect current status (PRESENT / PARTIAL / GAP). Do not leave stale GAP entries for patterns that are now implemented.

---

## Phase 10 — DOCS_INDEX.md and gameworks/docs/INDEX.md Currency

*Both index files must enumerate all active documents. No document exists without an index entry; no index entry points to a non-existent file.*

- [ ] **`docs/DOCS_INDEX.md` — verify every listed file exists**
  ```bash
  while IFS= read -r line; do
    file=$(echo "$line" | grep -oP '`[^`]+\.md`' | tr -d '`')
    [ -n "$file" ] && [ ! -f "$file" ] && echo "MISSING: $file"
  done < docs/DOCS_INDEX.md
  ```

- [ ] **`docs/DOCS_INDEX.md` — add missing entries** — these are required but not yet listed:
  - `docs/FEATURE_SAVE_RESUME_LOAD.md`
  - `docs/DOC_REVIEW_REFRESH_CHECKLIST.md` (this file)
  - `docs/SAVE_FORMAT_SPEC.md` (when created)
  - `docs/SCHEMA_MIGRATION.md` (when created)
  - `docs/SECURITY.md` (when created)

- [ ] **`gameworks/docs/INDEX.md` — verify every listed file exists**
  ```bash
  while IFS= read -r line; do
    file=$(echo "$line" | grep -oP '\[.*\]\(\K[^)]+')
    [ -n "$file" ] && [ ! -f "gameworks/docs/$file" ] && echo "MISSING: gameworks/docs/$file"
  done < gameworks/docs/INDEX.md
  ```

- [ ] **`gameworks/docs/INDEX.md` — add missing entries** — the following files exist in `gameworks/docs/` but are not in the index table:
  - `PERFORMANCE_PLAN.md`
  - `TEST_GAP_ANALYSIS.md`
  - `TEST_HARDENING_PLAN.md`
  Confirm presence and add rows to the index table.
  ```bash
  ls gameworks/docs/ | grep -v -f <(grep -oP '\(.*\.md\)' gameworks/docs/INDEX.md | tr -d '()')
  ```

- [ ] **`docs/DOCS_INDEX.md` Gameworks Tests section** — the section states "22 files, scaffolded 2026-05-10". Recount and update.
  ```bash
  find gameworks/tests/ -name "test_*.py" | wc -l
  ```

---

## Phase 11 — Root-Level Document Triage

*Root-level `.md` files that are not in any index are orphans. Every root-level file must be classified: active, archive, or delete.*

- [ ] **Triage each root-level `.md` file** — open each and determine its current status:

  | File | Action |
  |---|---|
  | `README.md` | Active — verify it matches current launch instructions |
  | `AGENTS.md` | Active — verify agent instructions are current |
  | `GEMINI.md` | Review — confirm whether this is still applicable or can be archived |
  | `HARDENING_SUMMARY.md` | Review — confirm whether superseded by `gameworks/docs/TEST_HARDENING_PLAN.md`; if so, archive or add a redirect note |
  | `PULL_REQUEST_DESCRIPTION.md` | Archive candidate — single-use PR description; move to `docs/archive/` or delete |
  | `for_user_review.md` | Review — determine if content is still actionable or can be deleted |
  | `full_enterprise_grade_repository_audit_and_remediation_analysis_prompt.md` | Duplicate — also exists at `docs/`; confirm which is canonical and delete the other |

- [ ] **`README.md` — verify the Quick Start commands work** — run the exact commands shown in README and confirm they produce no errors.
  ```bash
  head -60 README.md
  ```

---

## Phase 12 — Cross-Document Consistency

*Facts stated in multiple documents must be identical. Contradictions between docs are bugs.*

- [ ] **Version string consistency** — search every doc for version references and confirm all match `__version__`:
  ```bash
  grep -rn "v0\.\|__version__\|version.*0\." gameworks/docs/ docs/ --include="*.md" | grep -v "#\|schema\|python\|pygame" | grep "[0-9]\.[0-9]"
  ```

- [ ] **Test count consistency** — search every doc that mentions a test count and confirm all match Phase 0:
  ```bash
  grep -rn "114\|passing\|tests pass\|test count\|total test" gameworks/docs/ docs/ --include="*.md"
  ```

- [ ] **`renderer_large` fixture name consistency** — confirm no doc still describes `renderer_large` as the 40×30 fixture (it is now 300×370; the 40×30 fixture is `renderer_panel_large`):
  ```bash
  grep -rn "renderer_large.*40\|40.*renderer_large\|renderer_large.*9×9\|renderer_large.*floor.*7" gameworks/docs/ docs/ --include="*.md"
  ```

- [ ] **Scoring constant consistency** — any doc that lists scoring values must match `engine.py`:
  ```bash
  grep -rn "250\|50\|25\|STREAK\|multiplier\|streak" gameworks/docs/ --include="*.md" | grep -v "#\|example\|step"
  ```

- [ ] **Known-failing test names consistency** — any doc that names the 4 animation failures must use the exact current test names:
  ```bash
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/renderer/test_animations.py -v 2>&1 | grep FAILED
  grep -rn "test_done_when_all_elapsed\|test_single_position\|test_done_after_enough_time\|test_correct_done_property" gameworks/docs/ --include="*.md"
  ```

---

## Phase 13 — Supplementary Documents Required by FEATURE_SAVE_RESUME_LOAD.md

*Phase 4 of `FEATURE_SAVE_RESUME_LOAD.md` requires three documents to be created. This phase tracks their existence and completeness.*

- [ ] **`docs/SAVE_FORMAT_SPEC.md`** — check if it exists. If not, create it. Must contain: array keys, dtypes, shapes, JSON meta field list with types and valid values, schema version history table, byte-order note, manual inspection command.
  ```bash
  ls docs/SAVE_FORMAT_SPEC.md 2>/dev/null || echo "MISSING"
  ```

- [ ] **`docs/SCHEMA_MIGRATION.md`** — check if it exists. If not, create it. Must contain: trigger conditions for schema bumps, migration function template, backwards-read policy.
  ```bash
  ls docs/SCHEMA_MIGRATION.md 2>/dev/null || echo "MISSING"
  ```

- [ ] **`docs/SECURITY.md`** — check if it exists. If not, create it. Must contain: `allow_pickle=True` risk, accepted-risk declaration, guidance to only load `.mscsave` files from trusted local sources.
  ```bash
  ls docs/SECURITY.md 2>/dev/null || echo "MISSING"
  ```

- [ ] **`.github/PULL_REQUEST_TEMPLATE.md`** — check if it exists. If not, create it. Must contain PR checklist: tests green, no TODO in code, Ambiguity Register reviewed, `DOCS_INDEX.md` updated, version bumped.
  ```bash
  ls .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || echo "MISSING"
  ```

---

## Phase 14 — LLM Audit Documents

*`docs/llm-audits/` contains timestamped audit snapshots. These are historical records — they must not be edited. However the index and summaries must stay current.*

- [ ] **`docs/llm-audits/index/audit-index.md`** — confirm the most recent audit entry is listed.
  ```bash
  cat docs/llm-audits/index/audit-index.md
  ```

- [ ] **`docs/llm-audits/summaries/open-findings.md`** — confirm any finding that has been resolved in code is marked resolved here.
  ```bash
  cat docs/llm-audits/summaries/open-findings.md | head -40
  ```

- [ ] **`docs/llm-audits/summaries/risk-trends.md`** — confirm the trend entry for the current sprint/session is present.

---

## Phase 15 — Final Verification

- [ ] **Run the full test suite one final time** — confirm no regressions were introduced by any doc-related edits (e.g., a conftest.py reference fixed in a doc was also fixed in the actual file).
  ```bash
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | tail -3
  ```

- [ ] **Confirm no broken internal doc links** — search for relative markdown links and verify each target file exists.
  ```bash
  grep -rn "\[.*\](\([^h][^t][^t][^p]\)" gameworks/docs/ docs/ --include="*.md" | grep -oP '\(\K[^)]+' | while read f; do
    [ ! -f "$(dirname $f)/$f" ] && echo "BROKEN LINK: $f"
  done
  ```

- [ ] **Confirm `back_log.md` is current** — any item completed in this sprint must be removed or marked done.
  ```bash
  cat docs/back_log.md
  ```

- [ ] **Stage and commit all documentation updates**
  ```bash
  git add gameworks/docs/ docs/
  git status   # review — confirm only .md files are staged
  git commit -m "docs: refresh documentation for <version/feature name>"
  git push origin frontend-game-mockup
  ```

---

## Stale-Content Patterns to Always Search For

Run these searches on every pass regardless of what changed. Each match is a candidate stale reference.

```bash
# Version strings that may not match __version__
grep -rn "0\.1\.0\b" gameworks/docs/ docs/ --include="*.md"

# Test counts that may be stale
grep -rn "\b[0-9]\{2,3\} test\|[0-9]\{2,3\} passing\|[0-9]\{2,3\} passed" gameworks/docs/ docs/ --include="*.md"

# Old fixture name for 40x30 board
grep -rn "renderer_large.*40\|40x30.*renderer_large" gameworks/docs/ docs/ --include="*.md"

# Resolved bugs still marked OPEN
grep -n "| OPEN" gameworks/docs/BUGS.md | head -20

# References to functions that no longer exist
grep -rn "def _resume_game\|GameLoop._resume_game" gameworks/docs/ docs/ --include="*.md"

# Phantom action strings (strings in docs not returned by renderer)
grep -rn '"restart"\|"quit"\|"save"\|"save_state"\|"dev:solve"' gameworks/docs/ --include="*.md"

# Docs that reference files in docs/archive/ that may not exist
grep -rn "docs/archive/" docs/ gameworks/docs/ --include="*.md"
```
