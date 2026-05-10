# DOC_REVIEW_REFRESH — Agentic Skill

**Skill ID**: `doc-review-refresh`
**Version**: 2.0.0
**Trigger**: Execute on every feature merge, sprint end, API or constant rename, or explicit request.
**Agent**: Any LLM agent with shell access and read/write capability in this repository.
**Output**: Every documentation file in `gameworks/docs/` and `docs/` accurately reflects the live codebase. A structured RUNLOG is emitted at completion.

---

## Role

You are the **Documentation Review & Refresh Agent**. Your job is to make docs match code. You do not write features, modify `.py` files, or comment on code quality. You read code to establish ground truth, compare docs against that truth, and update docs to match. The skill is complete only when every discrepancy you discover has been resolved or escalated in the RUNLOG.

---

## Execution Contract

| Rule | Detail |
|---|---|
| Never edit `.py` files | You may read them to establish ground truth only |
| Never skip a phase | Later phases depend on Phase 0's ground truth variables |
| Never assume a doc is current | Every claim in a doc must be verified against a live command |
| Adapt to what you discover | Do not assume which entities exist — discover them with shell commands first, then act on each discovery |
| Stage only `.md` and `.github/` files | Never stage `.py`, `.npy`, `.npz`, binaries, or generated artifacts |
| Emit a RUNLOG | Record every change made and every item requiring human review |

---

## Phase 0 — Ground Truth Capture

*Capture the live state of the codebase before touching any doc. Every subsequent phase acts on these captured values. If any 0-* step fails, stop and report the failure before proceeding.*

### 0-A. Version string

```bash
grep "__version__" gameworks/__init__.py
```

Store the result as `$GT_VERSION`. This is the canonical version. Every occurrence of a version string in any doc must equal this value.

### 0-B. Test health

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | tail -5
```

Store: total collected (`$GT_TOTAL`), total passed (`$GT_PASSED`), total failed (`$GT_FAILED`).

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | grep "FAILED"
```

Store the exact list of failing test node IDs as `$GT_FAILURES`. If this list contains any test not present in the known-failures list recorded in `gameworks/docs/TEST_GAP_ANALYSIS.md`, a regression exists. Stop and report it before proceeding.

### 0-C. Public symbols per module

For each of `engine.py`, `renderer.py`, `main.py`, capture all public classes, top-level functions, and module-level constants:

```bash
grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/engine.py
grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/renderer.py
grep -n "^class \|^def \|^[A-Z_]\{3,\} " gameworks/main.py
```

Store these as `$GT_SYMBOLS_ENGINE`, `$GT_SYMBOLS_RENDERER`, `$GT_SYMBOLS_MAIN`.

### 0-D. Action strings

```bash
grep -n 'return "' gameworks/renderer.py | grep -v "#"
```

Store every string literal returned by `handle_event()` as `$GT_ACTIONS`.

### 0-E. CLI flags

```bash
grep -n "add_argument" gameworks/main.py
```

Store every flag name and help text as `$GT_FLAGS`.

### 0-F. Colour constants

```bash
grep -n "^\s\+[a-z_]\+\s*=(" gameworks/renderer.py | head -60
```

Store every constant name and RGB tuple as `$GT_COLOURS`.

### 0-G. Test fixture names

```bash
grep -n "^def " gameworks/tests/renderer/conftest.py
```

Store every fixture function name and its docstring as `$GT_FIXTURES`.

### 0-H. Documentation inventory

```bash
find gameworks/docs/ docs/ -name "*.md" | sort
find . -maxdepth 1 -name "*.md" | sort
```

Store the complete file list as `$GT_DOCS`. Any file not on this list does not exist yet.

### 0-I. Feature merge probes

For each feature branch listed in `docs/back_log.md` as "pending", check whether its sentinel symbols now exist in the codebase:

```bash
grep -n "TODO:\|Branch:" docs/back_log.md
```

For each pending feature, extract the branch name and identify one or two symbols that would only exist if the feature were merged. Search for them:

```bash
grep -rn "<symbol>" gameworks/ 2>/dev/null
```

Store the merge status of each pending feature as a boolean variable (e.g., `$FEATURE_SAVE_MERGED`). Phases that depend on a feature's merge status use these variables for conditional logic.

---

## Phase 1 — Version Consistency

*Rule: `$GT_VERSION` is the single source of truth for the package version. Every version reference in every doc must match it.*

### 1-A. Discover all version references

```bash
grep -rn "[0-9]\+\.[0-9]\+\.[0-9]\+" gameworks/docs/ docs/ --include="*.md" | grep -v "python\|pygame\|schema\|schema_version\|#"
```

For each match returned:
1. Compare the matched version string to `$GT_VERSION`.
2. If it matches — no action.
3. If it differs — open the file, update the stale value to `$GT_VERSION`, record the change in RUNLOG with the file path and old value.

### 1-B. CHANGELOG leading entry

```bash
head -5 gameworks/docs/CHANGELOG.md
```

The first `## [X.Y.Z]` header must match `$GT_VERSION`. If it does not:
- If `$GT_VERSION` is higher than the leading entry, a new release was cut without a CHANGELOG entry. Add a new `## [$GT_VERSION] — <today's date>` entry with `### Added`, `### Changed`, `### Fixed` subsections. Use placeholder lines for content you cannot determine from context.
- If `$GT_VERSION` is lower, the CHANGELOG is ahead of the code. Record this as a human-review item in RUNLOG.

---

## Phase 2 — API Reference Accuracy

*`gameworks/docs/API_REFERENCE.md` must accurately list every public class, method, parameter, action string, and CLI flag. The live code is ground truth.*

### 2-A. Symbol reconciliation — discovery loop

Read `gameworks/docs/API_REFERENCE.md` and extract every documented symbol name:

```bash
grep -n "^### \|^#### \|^`def \|^`class " gameworks/docs/API_REFERENCE.md
```

For each symbol documented in the API reference:
- Check whether it still exists in the corresponding `$GT_SYMBOLS_*` list.
- If it no longer exists in code — it is a phantom. Remove the entry. Record in RUNLOG.

For each symbol in `$GT_SYMBOLS_ENGINE`, `$GT_SYMBOLS_RENDERER`, `$GT_SYMBOLS_MAIN`:
- Check whether a corresponding entry exists in the API reference.
- If it does not — it is a gap. Add a stub entry with the symbol name and a `TODO: document` note. Record in RUNLOG.

### 2-B. Action string reconciliation — discovery loop

Extract every action string currently documented in `API_REFERENCE.md`:

```bash
grep -n '"[a-z_:]*"' gameworks/docs/API_REFERENCE.md | grep -i "action\|return\|event"
```

Compare against `$GT_ACTIONS`:
- String in doc but not in `$GT_ACTIONS` — phantom. Remove it. Record in RUNLOG.
- String in `$GT_ACTIONS` but not in doc — gap. Add it. Record in RUNLOG.

### 2-C. CLI flag reconciliation — discovery loop

Extract every CLI flag currently documented in `API_REFERENCE.md`:

```bash
grep -n "\-\-[a-z\-]*" gameworks/docs/API_REFERENCE.md
```

Compare against `$GT_FLAGS`:
- Flag in doc but not in `$GT_FLAGS` — phantom. Remove it. Record in RUNLOG.
- Flag in `$GT_FLAGS` but not in doc — gap. Add it. Record in RUNLOG.

### 2-D. Pending feature stubs — discovery loop

For each feature in `$GT_DOCS` whose `back_log.md` entry lists symbols not yet in the codebase:
- Check whether stub entries already exist in `API_REFERENCE.md`.
- If no stubs exist — add them, clearly marked `(pending: <branch-name>)`.
- If stubs exist but the feature has since merged (`$FEATURE_*=true`) — replace the stubs with real signatures from `$GT_SYMBOLS_*`.

---

## Phase 3 — ARCHITECTURE.md Accuracy

### 3-A. Module dependency diagram verification

```bash
grep -n "^from\|^import" gameworks/engine.py gameworks/renderer.py gameworks/main.py
```

Read the data-flow diagram in `gameworks/docs/ARCHITECTURE.md`. For every arrow or dependency shown:
- Confirm a corresponding import or function call exists in the code above.
- If no code evidence exists for the arrow — it is a phantom. Remove or update the arrow. Record in RUNLOG.

For any new import discovered above that is not reflected in the diagram — add it. Record in RUNLOG.

### 3-B. State machine verification

```bash
grep -n "_state\s*=\|_state ==" gameworks/main.py | head -30
```

Extract every state value assigned to `_state`. Compare against the state machine diagram in `ARCHITECTURE.md`. For each state in code not in the diagram — add it. For each state in the diagram not in code — remove it. Record all changes in RUNLOG.

### 3-C. Pending feature data flows — discovery loop

For each feature whose merge status is `true` (from Phase 0-I):
1. Read the feature's design doc (from `$GT_DOCS`) to identify the data flow it introduces.
2. Check whether that data flow is depicted in `ARCHITECTURE.md`.
3. If absent — add it. Record in RUNLOG.

---

## Phase 4 — CHANGELOG Currency

### 4-A. Discover unlisted commits

```bash
git log --oneline --since="$(grep -oP '^\## \[\K[^\]]+' gameworks/docs/CHANGELOG.md | head -1 | grep -oP '\d{4}-\d{2}-\d{2}')" -- gameworks/
```

For each commit returned, determine whether it warrants a CHANGELOG entry. Criteria:
- **Requires entry**: new feature, API change, constant value change, bug fix, performance change, test suite structural change.
- **Does not require entry**: doc-only edit, whitespace, comment-only, merge commit.

For each commit that requires an entry and is not already represented in the CHANGELOG — add the entry under the current version using Keep a Changelog format (`### Added`, `### Changed`, `### Fixed`, `### Removed`). Record each addition in RUNLOG.

### 4-B. Colour constant change verification

```bash
grep -n "tile_reveal\|flag_red" gameworks/renderer.py
grep -n "tile_reveal\|flag_red" gameworks/docs/CHANGELOG.md
```

If the current RGB values in `renderer.py` differ from any values mentioned in the CHANGELOG, a colour change occurred that was not logged. Add the appropriate entry.

### 4-C. Formatting compliance

```bash
grep -n "^## \[" gameworks/docs/CHANGELOG.md
```

Every version header must use `## [X.Y.Z] — YYYY-MM-DD` format. Every change block must use `### Added`, `### Changed`, `### Fixed`, or `### Removed` subsections. No freeform paragraphs at the version level. Correct any violations.

---

## Phase 5 — BUGS.md Currency

### 5-A. Open bug reconciliation — discovery loop

```bash
grep -n "| OPEN" gameworks/docs/BUGS.md
```

For each row returned, extract the bug ID:
1. Search git log for that ID: `git log --oneline | grep -i "<bug-id>"`
2. Search commit messages for keywords from the bug title: `git log --oneline | grep -i "<keyword>"`
3. If a resolution commit is found and the status is still `OPEN` — update to `RESOLVED — <sha>`. Record in RUNLOG.

### 5-B. Header metadata update

```bash
grep -c "| OPEN" gameworks/docs/BUGS.md
```

Update `**Total open:**` to the count above. Update `**Last updated:**` to today's date. Record in RUNLOG if changed.

### 5-C. Feature-gated gap closure — discovery loop

For each feature whose merge status is `true` (from Phase 0-I):
1. Read the feature's design doc to identify which bug IDs or gap entries it was supposed to close.
2. For each such entry still marked `OPEN` in `BUGS.md` — verify the closing code exists, then update to `RESOLVED`. Record in RUNLOG.

---

## Phase 6 — GAME_DESIGN.md Currency

### 6-A. Scoring constant reconciliation — discovery loop

```bash
grep -n "^[A-Z_]\{3,\}\s*=" gameworks/engine.py | grep -i "point\|penalty\|bonus\|tier\|score\|streak"
```

For each constant returned, search for it in `gameworks/docs/GAME_DESIGN.md`:

```bash
grep -n "<constant-name>" gameworks/docs/GAME_DESIGN.md
```

If the value in the doc differs from the value in the code — update the doc. The code is ground truth. Record in RUNLOG.

If the constant is not documented at all — add a stub entry. Record in RUNLOG.

### 6-B. Board mode reconciliation — discovery loop

```bash
grep -n '"random"\|"npy"\|"image"\|mode.*=' gameworks/engine.py | head -15
```

Extract every board mode string. For each mode:
- Confirm it is documented in `GAME_DESIGN.md` with its corresponding CLI flag.
- If absent — add it. Record in RUNLOG.

### 6-C. Feature-gated sections — discovery loop

For each feature whose merge status is `true` (from Phase 0-I):
1. Determine from the feature's design doc what player-visible behaviour it adds.
2. Check whether a corresponding section exists in `GAME_DESIGN.md`.
3. If absent — add it. Record in RUNLOG.

---

## Phase 7 — DEVELOPER_GUIDE Currency

### 7-A. Test command verification

Extract the test command currently shown in `gameworks/docs/DEVELOPER_GUIDE.md`:

```bash
grep -n "pytest\|SDL_VIDEODRIVER" gameworks/docs/DEVELOPER_GUIDE.md
```

Run the extracted command. If output differs from expectations stated in the guide — update the guide to reflect current behaviour. Record in RUNLOG.

### 7-B. Known-failure list reconciliation

Extract the list of known-failing tests from the guide:

```bash
grep -n "FAIL\|xfail\|skip" gameworks/docs/DEVELOPER_GUIDE.md
```

Compare against `$GT_FAILURES`:
- Test in the guide's known-failures list but not in `$GT_FAILURES` — it has been fixed. Remove from the list. Record in RUNLOG.
- Test in `$GT_FAILURES` but not in the guide — add it. Record in RUNLOG.

### 7-C. Fixture name reconciliation — discovery loop

Extract every fixture name mentioned in the guide:

```bash
grep -n "renderer_\|engine_\|conftest" gameworks/docs/DEVELOPER_GUIDE.md
```

For each fixture name found, verify it exists in `$GT_FIXTURES`. If the name does not appear in `$GT_FIXTURES` — it has been renamed or removed. Search `$GT_FIXTURES` for the closest match and update the reference. Record in RUNLOG.

### 7-D. Platform command completeness

```bash
grep -n "SDL_VIDEODRIVER\|set SDL\|Windows\|cmd\|powershell" gameworks/docs/DEVELOPER_GUIDE.md
```

Both Linux/macOS and Windows test commands must be present. If either is absent, add it. Record in RUNLOG.

---

## Phase 8 — TEST_GAP_ANALYSIS Currency

### 8-A. Test count update

Replace any stale test count in `gameworks/docs/TEST_GAP_ANALYSIS.md` with `$GT_TOTAL`, `$GT_PASSED`, `$GT_FAILED` from Phase 0-B. Use exact values.

```bash
grep -n "[0-9]\+ test\|[0-9]\+ pass\|[0-9]\+ fail" gameworks/docs/TEST_GAP_ANALYSIS.md
```

Update every count that does not match ground truth. Record in RUNLOG.

### 8-B. Known-failure list update

Replace the known-failures list in the document with `$GT_FAILURES`. Use exact test node IDs. Do not paraphrase test names.

### 8-C. Pending gap reconciliation — discovery loop

```bash
grep -n "pending\|not yet\|TODO\|missing\|no test" gameworks/docs/TEST_GAP_ANALYSIS.md
```

For each pending gap entry returned:
1. Extract the expected test file path or test ID from the entry.
2. Check whether it now exists: `find gameworks/tests/ -name "<filename>"` or `grep -rn "<test-id>" gameworks/tests/`.
3. If it now exists — mark the gap as closed and record the file path. Record in RUNLOG.
4. If it still does not exist — leave the entry unchanged.

### 8-D. New test file discovery

```bash
find gameworks/tests/ -name "test_*.py" | sort
```

For each test file returned, check whether it has a corresponding row in the test health breakdown table in the document. If not — add a row. Record in RUNLOG.

---

## Phase 9 — DESIGN_PATTERNS Currency

### 9-A. GAP and PARTIAL pattern reconciliation — discovery loop

```bash
grep -n "GAP\|PARTIAL" gameworks/docs/DESIGN_PATTERNS.md
```

For each row returned:
1. Note the pattern ID and name from that row.
2. Read the pattern's description section in the document to understand what implementation evidence would advance its status to PRESENT.
3. Search the codebase for that evidence using terms from the description as search keys:
   ```bash
   grep -rn "<term-from-description>" gameworks/
   ```
4. Decision logic:
   - Evidence found and complete — update status to PRESENT. Record in RUNLOG.
   - Evidence found but incomplete — verify whether PARTIAL is still accurate or whether the status should advance. Update accordingly. Record in RUNLOG.
   - No evidence found — leave the status unchanged.

### 9-B. PRESENT pattern regression check — discovery loop

```bash
grep -n "PRESENT" gameworks/docs/DESIGN_PATTERNS.md
```

For each PRESENT pattern:
1. Read the pattern's description to understand what code backs the PRESENT status.
2. Verify that backing code still exists:
   ```bash
   grep -rn "<backing-symbol-or-pattern>" gameworks/
   ```
3. If the backing code no longer exists (e.g., the function was removed or renamed) — downgrade the status and record the regression in RUNLOG as a human-review item.

### 9-C. Alignment summary table update

```bash
grep -c "| PRESENT\|| PARTIAL\|| GAP" gameworks/docs/DESIGN_PATTERNS.md
```

Recount and update the totals row in the alignment summary table to reflect all changes made in 9-A and 9-B.

---

## Phase 10 — Index Currency

*Rule: every `.md` file that exists must have at least one index entry. Every index entry must point to a file that exists.*

### 10-A. Broken link detection — discovery loop

For each index file in `$GT_DOCS` (`gameworks/docs/INDEX.md`, `docs/DOCS_INDEX.md`):

```bash
grep -oP '\[.*?\]\(\K[^)]+' <index-file>
```

For each link path returned, check whether the target file exists:

```bash
[ -f "<path>" ] && echo "OK" || echo "BROKEN: <path>"
```

For every broken link — either fix the path or remove the entry. Record in RUNLOG.

### 10-B. Orphan detection — discovery loop

For each `.md` file in `$GT_DOCS`:
1. Check whether it is referenced by any index file:
   ```bash
   grep -rn "<filename>" gameworks/docs/INDEX.md docs/DOCS_INDEX.md
   ```
2. If not referenced anywhere — it is an orphan. Add an entry to the most appropriate index. Record in RUNLOG.

### 10-C. Required entries from back_log

For each feature listed in `docs/back_log.md` that has an associated design doc:

```bash
grep -n "docs/.*\.md" docs/back_log.md
```

For each path returned, verify it is indexed in `docs/DOCS_INDEX.md`. If absent — add it. Record in RUNLOG.

### 10-D. Test file count update

```bash
find gameworks/tests/ -name "test_*.py" | wc -l
```

Update every count reference in index files to match. Record in RUNLOG if changed.

---

## Phase 11 — Root-Level Document Triage

### 11-A. Discover all root-level markdown files

```bash
find . -maxdepth 1 -name "*.md" | sort
```

For each file returned, apply the following decision tree:

1. **Is this file referenced in `docs/DOCS_INDEX.md`?**
   - Yes → Active. Proceed to step 3.
   - No → Orphan. Proceed to step 2.

2. **Orphan classification:**
   - Is the content still relevant and actionable? → Add it to `docs/DOCS_INDEX.md`. Record in RUNLOG.
   - Is it a single-use artifact (one-time PR description, one-time analysis)? → Move to `docs/archive/` and update any references. Record in RUNLOG.
   - Is it entirely superseded by a file in `gameworks/docs/` or `docs/`? → Add a redirect header `> This document has been superseded by <path>.` and record in RUNLOG as a human-review item for potential deletion.
   - Is the content stale with no path to relevance? → Record as a human-review item in RUNLOG with a deletion recommendation. Do not delete without human confirmation.

3. **Active file verification:**
   - Read the first 20 lines. Does the content reflect the current state of the project?
   - If obviously stale (references a feature, version, or state that no longer exists) — record as a human-review item in RUNLOG with a description of the staleness.

---

## Phase 12 — Cross-Document Consistency

*Any fact stated in more than one document must be identical in all of them. A contradiction between docs is a bug.*

### 12-A. Version string sweep

```bash
grep -rn "[0-9]\+\.[0-9]\+\.[0-9]\+" gameworks/docs/ docs/ --include="*.md" | grep -v "python\|pygame\|schema\|#"
```

Every version string in the output must equal `$GT_VERSION`. For each that does not — update it. Record in RUNLOG.

### 12-B. Test count sweep

```bash
grep -rn "\b[0-9]\{2,3\} test\|\b[0-9]\{2,3\} passing\|\b[0-9]\{2,3\} passed" gameworks/docs/ docs/ --include="*.md"
```

Every count in the output must match `$GT_TOTAL` and `$GT_PASSED`. For each that does not — update it. Record in RUNLOG.

### 12-C. Fixture name sweep

```bash
grep -rn "renderer_\|engine_fixture\|conftest" gameworks/docs/ docs/ --include="*.md"
```

Every fixture name referenced must exist in `$GT_FIXTURES`. For each that does not — look up the correct current name in `$GT_FIXTURES` and replace it. Record in RUNLOG.

### 12-D. Colour constant sweep

```bash
grep -rn "[0-9]\{1,3\},\s*[0-9]\{1,3\},\s*[0-9]\{1,3\}" gameworks/docs/ docs/ --include="*.md"
```

For each RGB triple found in a doc, check whether the same constant name appears in `$GT_COLOURS` with a different value. If so — the doc references a superseded colour value. Update it. Record in RUNLOG.

### 12-E. Symbol name sweep

```bash
grep -rn "def \|class \|GameLoop\.\|GameEngine\.\|Board\." gameworks/docs/ docs/ --include="*.md" | grep -v "^[^:]*\.md:#\|example\|stub"
```

For each symbol reference found in a doc, verify it still exists in `$GT_SYMBOLS_*`. If not — search `$GT_SYMBOLS_*` for a close match (rename) or mark it as a phantom. Record in RUNLOG.

---

## Phase 13 — Supplementary Documents

*Some features require companion documents that must exist before or alongside the feature code. Discover which are required and create any that are missing.*

### 13-A. Discover required supplementary docs

For each feature design doc in `$GT_DOCS`:

```bash
grep -n "requires\|supplementary\|companion doc\|must create\|see docs/" <feature-doc-path>
```

For each referenced path returned:
1. Check whether the file exists: `ls <path> 2>/dev/null || echo "MISSING"`
2. If `MISSING` — read the feature doc's specification for that file and create it with the required content.
3. Record the creation in RUNLOG with the spec source.

The content requirements for each file are defined in the feature's design doc. Use those specifications exactly — do not invent content.

---

## Phase 14 — LLM Audit Documents

*Files in `docs/llm-audits/` are historical records. Do not retroactively edit audit snapshots. Only update the index and summary files.*

### 14-A. Audit index currency

```bash
ls docs/llm-audits/index/ 2>/dev/null
cat docs/llm-audits/index/audit-index.md 2>/dev/null | tail -10
```

The most recent audit session must have an entry. If this doc-refresh run is the most recent activity and no entry exists for it — add one with today's date and a one-line summary of the most significant correction made.

### 14-B. Open-findings resolution sweep

```bash
grep -n "OPEN\|unresolved\|pending" docs/llm-audits/summaries/open-findings.md 2>/dev/null
```

For each open finding, extract the finding ID or description and check whether a commit has addressed it:

```bash
git log --oneline | grep -i "<finding-keyword>"
```

If a resolution commit exists — update the entry to `RESOLVED — <sha>` with today's date. Record in RUNLOG.

---

## Phase 15 — Final Verification and Commit

### 15-A. Regression gate

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q 2>&1 | tail -5
```

The total count must equal `$GT_TOTAL`. The failure list must equal `$GT_FAILURES`. If either differs — stop. Do not commit. Record the discrepancy in RUNLOG as a blocking human-review item. Investigate whether a doc edit inadvertently modified a Python file.

### 15-B. Broken internal link check

```bash
grep -rEoh '\[.*?\]\(([^)]+)\)' gameworks/docs/ docs/ --include="*.md" | grep -oP '\(\K[^)]+' | grep -v "^http" | while read -r link; do
  resolved="$(dirname "$link")/$link"
  [ ! -f "$link" ] && [ ! -f "gameworks/docs/$link" ] && [ ! -f "docs/$link" ] && echo "POSSIBLE BROKEN LINK: $link"
done
```

Fix every confirmed broken relative link. Record in RUNLOG.

### 15-C. Stage review

```bash
git add gameworks/docs/ docs/ .github/
git status
```

Inspect the staged files. If any file outside of `*.md` and `.github/` is staged — unstage it immediately:

```bash
git restore --staged <file>
```

Proceed only when staged set contains exclusively documentation files.

### 15-D. Commit and push

```bash
git commit -m "docs: refresh documentation — <one-line summary of the most significant change>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push origin frontend-game-mockup
```

---

## RUNLOG

Emit this structure at the end of every execution. A no-op run (nothing changed) still requires a RUNLOG entry.

```
## RUNLOG — doc-review-refresh — <ISO-8601 date>

### Ground Truth
| Variable | Value |
|---|---|
| $GT_VERSION | |
| $GT_TOTAL / $GT_PASSED / $GT_FAILED | |
| $GT_FAILURES | |
| Feature merge statuses | |

### Changes Made
| Phase | File | Old value / state | New value / state |
|---|---|---|---|

### Files Created
| File | Required by |
|---|---|

### Human Review Required
| Issue | File | Description |
|---|---|---|

### No-op phases
<list phases where every check passed with no changes needed>
```

---

## Quick Pre-Check

Run these before Phase 0. If all return zero lines, a full run is unlikely to be necessary. Any match is a trigger to proceed with the full skill.

```bash
# Version drift across docs
grep -rn "[0-9]\+\.[0-9]\+\.[0-9]\+" gameworks/docs/ docs/ --include="*.md" | grep -v "python\|pygame\|schema\|#" | grep -v "$(grep -oP '\"[0-9.]+\"' gameworks/__init__.py | tr -d '\"')"

# Stale test counts — any number that might no longer reflect reality
grep -rn "\b[0-9]\{2,3\} test\|\b[0-9]\{2,3\} pass" gameworks/docs/ docs/ --include="*.md"

# Bugs marked OPEN
grep -c "| OPEN" gameworks/docs/BUGS.md

# GAP or PARTIAL patterns that may now be satisfied
grep -c "| GAP\|| PARTIAL" gameworks/docs/DESIGN_PATTERNS.md

# Pending gaps in test analysis that may now have test files
grep -c "pending\|not yet\|TODO" gameworks/docs/TEST_GAP_ANALYSIS.md

# Symbol references in docs that may no longer exist in code
grep -rn "_resume_game\|GameLoop\._" gameworks/docs/ docs/ --include="*.md"

# Superseded colour values
grep -rn "[0-9]\{1,3\},\s*[0-9]\{1,3\},\s*[0-9]\{1,3\}" gameworks/docs/ --include="*.md" | wc -l
```
