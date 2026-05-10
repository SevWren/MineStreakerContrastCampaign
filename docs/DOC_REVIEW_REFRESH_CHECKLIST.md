# DOC_REVIEW_REFRESH — Agentic Skill

**Skill ID**: `doc-review-refresh`
**Version**: 1.0.0
**Trigger**: Run this skill on every feature merge, sprint end, constant or API rename, or on explicit user request.
**Agent**: Any LLM agent with shell access and file read/write capability in this repository.
**Output**: All stale documentation is corrected and committed. The agent emits a structured `RUNLOG` at the end.

---

## Role

You are the **Documentation Review & Refresh Agent** for the `MineStreakerContrastCampaign` repository.
Your sole responsibility in this execution is to make every documentation file in `gameworks/docs/` and `docs/` accurately reflect the current state of the codebase. You do not write new features, modify runtime code, or comment on code quality. You read code, compare it against docs, and update docs to match.

---

## Execution Contract

- **Never edit runtime code** (`.py` files). You may only read `.py` files to establish ground truth.
- **Never skip a phase**. Each phase depends on Phase 0's ground truth. If Phase 0 fails, stop and report the error.
- **Never assume a doc is current**. Every doc must be verified against a live shell command before you trust its content.
- **Record every change you make** in the `RUNLOG` section at the end of this skill execution.
- **Commit only documentation files** (`*.md`, `.github/*.md`). Never stage `.py`, `.npy`, `.npz`, or any binary.
- If a required doc is missing, create it using the spec in Phase 13. Do not skip ahead.

---

## Phase 0 — Establish Ground Truth

*Purpose: before touching any doc, capture a precise snapshot of the live codebase. Every subsequent phase verifies against these captured values, not memory or assumptions.*

### 0-A. Version

```bash
grep "__version__" gameworks/__init__.py
```

Capture the exact string (e.g., `"0.1.1"`). Call this `$GT_VERSION`. Every doc that references a version must match this exactly.

### 0-B. Test Health

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | tail -5
```

Capture: total tests collected, total passed, total failed. Call these `$GT_TOTAL`, `$GT_PASSED`, `$GT_FAILED`.

List every failing test name:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | grep "FAILED"
```

Call this list `$GT_FAILURES`. If any failure is not in the known pre-existing list (see Phase 8), stop. Regressions block this skill run.

### 0-C. Public API Surface

Capture all public symbols (classes, top-level functions, module-level constants) from each module. These are your API ground-truth lists.

```bash
grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/engine.py
grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/renderer.py
grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/main.py
```

### 0-D. Action Strings

```bash
grep -n 'return "' gameworks/renderer.py | grep -v "#"
```

Capture every string literal returned by `handle_event()`. Call this `$GT_ACTIONS`.

### 0-E. CLI Flags

```bash
grep -n "add_argument" gameworks/main.py
```

Capture every flag name and its `help` text. Call this `$GT_FLAGS`.

### 0-F. Colour Constants

```bash
grep -n "tile_\|flag_\|mine_\|panel_\|header_\|btn_\|text_\|bg_" gameworks/renderer.py | grep "=(" | head -40
```

Capture all colour constant names and their RGB tuples. Call this `$GT_COLOURS`.

### 0-G. Fixture Names

```bash
grep -n "^def renderer_" gameworks/tests/renderer/conftest.py
```

Capture every fixture function name and its docstring. Call this `$GT_FIXTURES`.

### 0-H. Documentation File Inventory

```bash
find gameworks/docs/ docs/ -name "*.md" | sort
```

Capture the full list. Any file not on this list when you start does not yet exist. Any file on this list but missing from an index is an orphan to fix in Phase 10.

### 0-I. Save/Resume Feature Merge Status

```bash
grep -n "def save_game_state\|def load_game_state\|def preflight_check" gameworks/engine.py gameworks/main.py 2>/dev/null
```

If any match is found, set `$SAVE_FEATURE_MERGED=true`. If no match, set `$SAVE_FEATURE_MERGED=false`. Phases 2, 3, 5, 6, 9, and 13 use this flag to apply conditional steps.

---

## Phase 1 — Version Consistency

*Rule: every `$GT_VERSION` mention across all docs must be identical.*

### 1-A. Discover all version references

```bash
grep -rn "v0\.\|__version__\|version.*0\." gameworks/docs/ docs/ --include="*.md" | grep -v "#\|schema\|python\|pygame\|0\.0\." | grep "[0-9]\.[0-9]"
```

For each match:
- If the version string equals `$GT_VERSION` — no action needed.
- If the version string is different — open that file and update the stale reference to `$GT_VERSION`. Record the change in your `RUNLOG`.

### 1-B. CHANGELOG header check

```bash
head -10 gameworks/docs/CHANGELOG.md
```

The most recent `## [X.Y.Z]` header must match `$GT_VERSION`. If `__version__` was bumped but no CHANGELOG entry exists yet, create a new entry now with `### Added`, `### Changed`, and `### Fixed` subsections. Leave placeholders if you do not have enough context to fill them — a placeholder entry is better than a missing one.

---

## Phase 2 — API Reference Accuracy

*`gameworks/docs/API_REFERENCE.md` is the single source of truth for the public contract. Every class, method, parameter, action string, and CLI flag in the doc must match `$GT_*` from Phase 0.*

### 2-A. Symbol reconciliation

For each public symbol in `$GT_API_ENGINE`, `$GT_API_RENDERER`, `$GT_API_MAIN`:
- Read the corresponding section in `API_REFERENCE.md`.
- If the symbol is in the code but missing from the doc — add a stub entry.
- If the symbol is in the doc but no longer in the code — remove the stale entry. Record in `RUNLOG`.
- If a method's signature has changed — update the signature in the doc.

```bash
grep -n "^class \|^    def \|^    @property" gameworks/engine.py | grep -v "_"
```

### 2-B. Action string contract

Compare `$GT_ACTIONS` against the action string table in `API_REFERENCE.md`.
- Strings present in the code but absent from the table — add them.
- Strings present in the table but absent from the code — remove them (phantoms).

### 2-C. CLI flag contract

Compare `$GT_FLAGS` against the CLI section in `API_REFERENCE.md`. Apply the same add/remove rule.

### 2-D. Save feature stubs (conditional)

```bash
grep -n "save_game_state\|load_game_state\|SaveResult\|LoadResult\|from_arrays\|SAVE_SCHEMA_VERSION\|preflight_check" gameworks/docs/API_REFERENCE.md
```

- If `$SAVE_FEATURE_MERGED=false` and none of these stubs exist — add `(pending: feature/save-resume-load)` stub entries for all six symbols.
- If `$SAVE_FEATURE_MERGED=true` — replace any stub entries with the real signatures captured from Phase 0-C.

---

## Phase 3 — ARCHITECTURE.md Accuracy

### 3-A. Module dependency diagram

```bash
grep -n "^from\|^import" gameworks/engine.py gameworks/renderer.py gameworks/main.py
```

Read the ASCII data-flow diagram in `gameworks/docs/ARCHITECTURE.md`. For every arrow in the diagram, confirm a corresponding import or function call exists in the code. Remove arrows that have no code backing. Add arrows for new dependencies.

### 3-B. State machine

```bash
grep -n "MENU\|PLAYING\|RESULT\|_state\s*=" gameworks/main.py | head -20
```

States must be `MENU → PLAYING → RESULT → MENU`. If any new state has been added or removed, update the diagram.

### 3-C. Save/load data flow (conditional)

If `$SAVE_FEATURE_MERGED=true`, verify this data-flow path exists in the diagram:

```
GameLoop._save_state() → engine.save_game_state() → .mscsave
--resume → preflight_check() → engine.load_game_state() → GameLoop._start_game(resumed=True)
```

If it does not exist, add it.

---

## Phase 4 — CHANGELOG Currency

### 4-A. Discover commits not yet logged

```bash
git log --oneline --since="$(grep '^\## \[' gameworks/docs/CHANGELOG.md | head -1 | grep -oP '\d{4}-\d{2}-\d{2}')" -- gameworks/
```

For each commit in this list, determine whether it warrants a CHANGELOG entry:
- **Yes** — new feature, API change, constant value change, bug fix, performance change, test suite change.
- **No** — pure doc edit, whitespace, comment-only.

For each "yes" commit not already in the CHANGELOG, add an entry under the current version. Use Keep a Changelog subsection headers (`### Added`, `### Changed`, `### Fixed`, `### Removed`).

### 4-B. Spot-check known palette change

```bash
grep -n "tile_reveal\|flag_red\|colour.*palette\|cell.*background\|flag.*white\|pale\|near-black" gameworks/docs/CHANGELOG.md
```

Commit `84160f9` changed `tile_reveal` to `(12,12,16)` and `flag_red` to `(235,210,210)`. If these changes are not in the CHANGELOG, add them now.

### 4-C. Spot-check known zoom-floor change

```bash
grep -n "zoom\|min_fit_tile\|dynamic.*floor\|viewport.*fit" gameworks/docs/CHANGELOG.md
```

If the dynamic `min_fit_tile` floor is not logged, add it.

---

## Phase 5 — BUGS.md Currency

### 5-A. Discover resolved bugs

For each bug in the quick-reference table of `gameworks/docs/BUGS.md`, run:

```bash
git log --oneline | grep -i "<bug-id>"
```

If a commit message references the bug ID and the bug is still marked `OPEN`, update its status to `RESOLVED — <commit-sha>`.

### 5-B. Mandatory spot-checks

```bash
grep -n "FA-003\|FA-004\|H-005" gameworks/docs/BUGS.md | head -10
git log --oneline | grep -i "videoresize\|panel.*intercept\|save.*button\|FA-003\|FA-004\|H-005" | head -5
```

Remote commit `437f2d5` resolved FA-003, FA-004, and H-005. Verify all three are marked `RESOLVED`.

### 5-C. Header counts

```bash
grep -c "| OPEN" gameworks/docs/BUGS.md
```

Update `**Total open:**` and `**Last updated:**` in the BUGS.md header to match.

### 5-D. preflight_check gap (conditional)

If `$SAVE_FEATURE_MERGED=true`:

```bash
grep -n "DP-R6" gameworks/docs/BUGS.md | head -3
grep -n "def preflight_check" gameworks/main.py
```

If `preflight_check` exists in code and DP-R6 is still `OPEN`, mark it `RESOLVED`.

---

## Phase 6 — GAME_DESIGN.md Currency

### 6-A. Scoring constant reconciliation

```bash
grep -n "REVEAL_POINTS\|CORRECT_FLAG_BONUS\|WRONG_FLAG_PENALTY\|MINE_HIT_PENALTY\|STREAK_TIERS" gameworks/engine.py
grep -n "REVEAL_POINTS\|CORRECT_FLAG_BONUS\|WRONG_FLAG_PENALTY\|MINE_HIT_PENALTY\|STREAK_TIERS" gameworks/docs/GAME_DESIGN.md
```

For each constant: if the value in the doc differs from the value in the code, update the doc. The code is ground truth.

### 6-B. Board modes

```bash
grep -n '"random"\|"npy"\|"image"' gameworks/engine.py | head -10
```

Confirm `random`, `npy`, and `image` modes are all documented with their CLI flags. If a new mode exists in the code but is undocumented, add it.

### 6-C. Save & Resume section (conditional)

If `$SAVE_FEATURE_MERGED=true` and `GAME_DESIGN.md` has no "Save & Resume" section, add one covering: what the player can save, what is not saved (e.g., undo history), and how to resume from the CLI.

---

## Phase 7 — DEVELOPER_GUIDE Currency

### 7-A. Test command accuracy

Confirm the test command shown in the guide produces green output when run:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -v 2>&1 | tail -5
```

If the guide shows a different command, update it.

### 7-B. Known-failure list

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/renderer/test_animations.py -v 2>&1 | grep "FAILED\|PASSED\|ERROR"
```

Compare the output against the known-failure list in the guide. Update any stale test names.

### 7-C. Fixture documentation

Compare `$GT_FIXTURES` against any fixture descriptions in the guide.

```bash
grep -n "renderer_large\|renderer_panel_large\|renderer_easy" gameworks/docs/DEVELOPER_GUIDE.md
```

`renderer_large` is now a 300×370 board. `renderer_panel_large` is the 40×30 board (floor=7). Any guide text that attributes 40×30 to `renderer_large` must be corrected.

### 7-D. Windows test command

Confirm the guide contains the Windows-equivalent command:

```cmd
set SDL_VIDEODRIVER=dummy && set SDL_AUDIODRIVER=dummy && python -m pytest gameworks/tests/ -v
```

If absent, add it.

---

## Phase 8 — TEST_GAP_ANALYSIS Currency

### 8-A. Recount

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ --collect-only -q 2>&1 | tail -3
```

Update `gameworks/docs/TEST_GAP_ANALYSIS.md` with `$GT_TOTAL`, `$GT_PASSED`, `$GT_FAILED` from Phase 0-B.

### 8-B. Failure list

Update the known-failing test list in the doc. Use the exact test node IDs from `$GT_FAILURES`. Do not paraphrase test names.

### 8-C. Missing test files

```bash
ls gameworks/tests/unit/ gameworks/tests/cli/ gameworks/tests/integration/ 2>/dev/null
```

For each test gap still listed as "pending" in the doc, confirm the file does not yet exist. If it does exist, mark the gap as closed and note the file name.

### 8-D. New test files

```bash
ls gameworks/tests/renderer/
```

For each test file in `gameworks/tests/renderer/` that is not yet in the analysis, add a row to the test health breakdown table.

---

## Phase 9 — DESIGN_PATTERNS Currency

### 9-A. P8 — Atomic File I/O

```bash
grep -n "os.replace\|os.rename\|atomic" gameworks/engine.py
grep -n "P8\|Atomic" gameworks/docs/DESIGN_PATTERNS.md | head -5
```

If `$SAVE_FEATURE_MERGED=true` and `os.replace` exists in `engine.py`, update P8 status from `GAP` to `PRESENT` in the alignment table.

### 9-B. P9 — Versioned Schema Strings

```bash
grep -n "SAVE_SCHEMA_VERSION\|SCHEMA_VERSION" gameworks/engine.py
grep -n "P9\|Versioned Schema" gameworks/docs/DESIGN_PATTERNS.md | head -5
```

If `$SAVE_FEATURE_MERGED=true` and `SAVE_SCHEMA_VERSION` exists, update P9 to `PRESENT`.

### 9-C. P6 — Warmup-and-Verify

```bash
grep -n "def preflight_check" gameworks/main.py
grep -n "P6\|preflight\|Warmup" gameworks/docs/DESIGN_PATTERNS.md | head -5
```

If `$SAVE_FEATURE_MERGED=true` and `preflight_check` exists, update P6 to `PRESENT`.

### 9-D. Alignment table

Recount `PRESENT`, `PARTIAL`, and `GAP` totals in the alignment summary table. Update the counts row.

---

## Phase 10 — Index Currency

*Rule: every `.md` file that exists must have an entry in an index. Every index entry must point to a file that exists.*

### 10-A. gameworks/docs/INDEX.md — existence check

```bash
while IFS= read -r f; do
  [ ! -f "gameworks/docs/$f" ] && echo "BROKEN LINK in INDEX.md: $f"
done < <(grep -oP '\(\.\/\K[^)]+' gameworks/docs/INDEX.md 2>/dev/null)
```

Remove or fix any broken links.

### 10-B. gameworks/docs/INDEX.md — missing entries

```bash
ls gameworks/docs/*.md | xargs -I{} basename {}
```

For each file in `gameworks/docs/` that has no row in `INDEX.md`, add a row with the file name, a one-line description, and the current date.

### 10-C. docs/DOCS_INDEX.md — existence check

```bash
grep -oP '`[^`]+\.md`' docs/DOCS_INDEX.md | tr -d '`' | while read f; do
  [ ! -f "$f" ] && echo "BROKEN LINK in DOCS_INDEX.md: $f"
done
```

Remove or fix any broken links.

### 10-D. docs/DOCS_INDEX.md — required entries

These files must appear in `DOCS_INDEX.md`. If any are missing, add them:

| File | Section |
|---|---|
| `docs/FEATURE_SAVE_RESUME_LOAD.md` | Feature Specifications |
| `docs/DOC_REVIEW_REFRESH_CHECKLIST.md` | Tooling & Process |
| `docs/SAVE_FORMAT_SPEC.md` | Feature Specifications (add `(pending)` note if file not yet created) |
| `docs/SCHEMA_MIGRATION.md` | Feature Specifications (add `(pending)` note if file not yet created) |
| `docs/SECURITY.md` | Governance |
| `.github/PULL_REQUEST_TEMPLATE.md` | Tooling & Process |

### 10-E. Test file count

```bash
find gameworks/tests/ -name "test_*.py" | wc -l
```

Update the Gameworks Tests section count in `DOCS_INDEX.md` to match.

---

## Phase 11 — Root-Level Document Triage

*Every root-level `.md` file must be classified as active, archived, or deleted. Orphaned files that are neither referenced nor indexed are documentation debt.*

### 11-A. Triage decision tree

For each root-level `.md` file discovered in Phase 0-H, apply this logic:

1. **Is it referenced in `DOCS_INDEX.md`?** If yes — Active. Verify it opens without error and its content is still meaningful.
2. **Is it a single-use artifact?** (e.g., a PR description, a one-time analysis) — Archive candidate: move to `docs/archive/` and add a redirect note, or delete with `RUNLOG` justification.
3. **Does it duplicate content already in `gameworks/docs/`?** — Identify which copy is canonical, add a `> See canonical: <path>` notice to the non-canonical copy, and record in `RUNLOG`.

```bash
ls *.md 2>/dev/null
```

Apply specific rules to known root-level files:

| File | Rule |
|---|---|
| `README.md` | Active. Verify Quick Start commands run without error. |
| `AGENTS.md` | Active. Verify agent instructions are not contradicted by any code change since last update. |
| `GEMINI.md` | Review. If content is superseded by `AGENTS.md`, add a redirect header and note in `RUNLOG`. |
| `HARDENING_SUMMARY.md` | Review. If superseded by `gameworks/docs/TEST_HARDENING_PLAN.md`, archive it. |
| `PULL_REQUEST_DESCRIPTION.md` | Archive candidate. If it describes a merged PR, move to `docs/archive/`. |
| `for_user_review.md` | Review. If content is actionable, index it. If stale, delete it with justification. |
| `full_enterprise_grade_repository_audit_and_remediation_analysis_prompt.md` | If an identical copy exists in `docs/`, delete the root copy and add an index entry pointing to `docs/`. |

---

## Phase 12 — Cross-Document Consistency

*A fact stated in multiple documents must be identical everywhere. Contradictions are bugs.*

### 12-A. Stale-content sweep — run unconditionally

```bash
# Version strings that may not match $GT_VERSION
grep -rn "0\.1\.0\b" gameworks/docs/ docs/ --include="*.md"

# Stale test counts
grep -rn "\b[0-9]\{2,3\} test\|[0-9]\{2,3\} passing\|[0-9]\{2,3\} passed" gameworks/docs/ docs/ --include="*.md"

# Old 40x30 renderer_large fixture attribution
grep -rn "renderer_large.*40\|40x30.*renderer_large\|renderer_large.*9x9\|renderer_large.*floor.*7" gameworks/docs/ docs/ --include="*.md"

# Phantom _resume_game reference (replaced by _start_game(resumed=bool))
grep -rn "def _resume_game\|GameLoop\._resume_game\|_resume_game()" gameworks/docs/ docs/ --include="*.md"

# Phantom action strings — verify each against $GT_ACTIONS before leaving in docs
grep -rn '"restart"\|"quit"\|"save_state"\|"dev:solve"' gameworks/docs/ --include="*.md"

# Broken archive references
grep -rn "docs/archive/" docs/ gameworks/docs/ --include="*.md"

# Stale colour RGB values superseded by style(renderer) commit 84160f9
grep -rn "220, 50, 50\|35, 35, 45" gameworks/docs/ docs/ --include="*.md"
```

For each match: open the file, determine if the reference is stale, and update or remove it. Record every change in `RUNLOG`.

### 12-B. Scoring constant consistency

```bash
grep -rn "REVEAL_POINTS\|CORRECT_FLAG\|WRONG_FLAG\|MINE_HIT\|STREAK" gameworks/docs/ --include="*.md" | grep -v "#\|example\|step\|pattern"
```

Compare against Phase 0-C ground truth. Correct any stale values.

### 12-C. Known-failure name consistency

```bash
grep -rn "test_done_when_all_elapsed\|test_single_position\|test_done_after_enough_time\|test_correct_done_property" gameworks/docs/ --include="*.md"
```

All references must use the exact current test node IDs from `$GT_FAILURES`.

---

## Phase 13 — Supplementary Documents

*`FEATURE_SAVE_RESUME_LOAD.md` Phase 4 requires these files. If any are missing, create them now using the specs below.*

### 13-A. docs/SAVE_FORMAT_SPEC.md

```bash
ls docs/SAVE_FORMAT_SPEC.md 2>/dev/null || echo "MISSING"
```

If `MISSING`, create the file. It must contain:
- Array key/dtype/shape table for all arrays written to `.mscsave`
- JSON meta fields with types, valid values, and default values
- `SAVE_SCHEMA_VERSION` history table (columns: version, date, change reason)
- Byte-order and endianness note
- Manual inspection command: `python -c "import numpy as np; d=np.load('file.mscsave', allow_pickle=True); print(list(d.keys()))"`
- Human-readable example of a valid meta JSON blob

### 13-B. docs/SCHEMA_MIGRATION.md

```bash
ls docs/SCHEMA_MIGRATION.md 2>/dev/null || echo "MISSING"
```

If `MISSING`, create the file. It must contain:
- Trigger conditions table for when a schema version bump is required
- Migration function template (Python stub)
- Backwards-read policy: which old versions can be loaded by the current reader
- Test requirements for each migration path

### 13-C. docs/SECURITY.md

```bash
ls docs/SECURITY.md 2>/dev/null || echo "MISSING"
```

If `MISSING`, create the file. It must contain:
- `allow_pickle=True` risk disclosure and accepted-risk declaration
- Guidance: only load `.mscsave` files from trusted local file paths
- Threat model: what an attacker can achieve with a malicious `.mscsave` file
- Mitigations: schema version check before `allow_pickle`, file extension validation, path traversal prevention

### 13-D. .github/PULL_REQUEST_TEMPLATE.md

```bash
ls .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || echo "MISSING"
```

If `MISSING`, create `.github/` directory if needed and create the template. It must contain:
- `## Summary` section
- `## Test plan` checklist: `[ ] All tests green`, `[ ] No new TODO in code`, `[ ] Ambiguity Register reviewed`, `[ ] DOCS_INDEX.md updated`, `[ ] CHANGELOG.md updated`, `[ ] Version bumped if API changed`
- `## Branch` field
- `## Related backlog items` field

---

## Phase 14 — LLM Audit Documents

*These are historical records and must not be retroactively edited. Only update the index and summary files.*

### 14-A. Audit index

```bash
cat docs/llm-audits/index/audit-index.md 2>/dev/null | tail -10
```

Confirm the most recent audit session has an entry. If the current doc-refresh run is the most recent session, add an entry with today's date and a one-line summary of what was corrected.

### 14-B. Open findings

```bash
cat docs/llm-audits/summaries/open-findings.md 2>/dev/null | head -40
```

For each open finding, check whether a commit has resolved it. If resolved, mark it `RESOLVED — <commit-sha>` with today's date.

---

## Phase 15 — Final Verification and Commit

### 15-A. Test suite — confirm no regressions

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | tail -5
```

The total must equal `$GT_TOTAL`. The failure list must equal `$GT_FAILURES`. If either differs, stop. Investigate before committing.

### 15-B. Broken link check

```bash
grep -rn "\[.*\](\." gameworks/docs/ docs/ --include="*.md" | grep -oP '\(\K[^)]+' | while read -r link; do
  base=$(echo "$link" | sed 's|^\./||')
  [ ! -f "$base" ] && [ ! -f "gameworks/docs/$base" ] && [ ! -f "docs/$base" ] && echo "POSSIBLE BROKEN LINK: $link"
done
```

Fix every broken relative link before committing.

### 15-C. Stage only documentation

```bash
git add gameworks/docs/ docs/ .github/
git status
```

Review `git status` output. If any `.py`, `.npy`, `.npz`, or binary file is staged, unstage it:

```bash
git restore --staged <file>
```

### 15-D. Commit

```bash
git commit -m "docs: refresh documentation — <one-line description of the most significant change made>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

### 15-E. Push

```bash
git push origin frontend-game-mockup
```

---

## RUNLOG Template

At the end of every execution, emit a structured log in this exact format. Do not omit this section even if no changes were made — a no-op run is still a valid run.

```
## RUNLOG — doc-review-refresh — <ISO-8601 date>

### Ground Truth Captured
- Version: <$GT_VERSION>
- Tests: <$GT_TOTAL> total, <$GT_PASSED> passed, <$GT_FAILED> failed
- Known failures: <list test node IDs or "none">
- Save feature merged: <true | false>

### Changes Made
| Phase | File | Change description |
|---|---|---|
| <phase ID> | <file path> | <what was changed and why> |

### Files Created
| File | Required by |
|---|---|
| <path> | <phase and spec reference> |

### Items Requiring Human Review
- <any finding you could not resolve automatically, with a description of the issue and the file location>

### No-op phases
- <list of phases where everything was already accurate and no edits were needed>
```

---

## Quick Pre-Check — Run Before Phase 0

These seven commands are fast staleness signals. If all return zero matches, a full skill run is unlikely to find anything. If any return matches, proceed with the full run.

```bash
# 1. Version drift
grep -rn "0\.1\.0\b" gameworks/docs/ docs/ --include="*.md"

# 2. Stale test counts
grep -rn "\b[0-9]\{2,3\} test\|[0-9]\{2,3\} passing\|[0-9]\{2,3\} passed" gameworks/docs/ docs/ --include="*.md"

# 3. Wrong fixture attribution
grep -rn "renderer_large.*40\|40x30.*renderer_large" gameworks/docs/ docs/ --include="*.md"

# 4. Phantom function name
grep -rn "_resume_game" gameworks/docs/ docs/ --include="*.md"

# 5. Open bugs that may be resolved
grep -n "| OPEN" gameworks/docs/BUGS.md

# 6. Phantom action strings
grep -rn '"restart"\|"dev:solve"' gameworks/docs/ --include="*.md"

# 7. Stale colour RGB values
grep -rn "220, 50, 50\|35, 35, 45" gameworks/docs/ docs/ --include="*.md"
```
