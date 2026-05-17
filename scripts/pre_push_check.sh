#!/usr/bin/env bash
# scripts/pre_push_check.sh
#
# Machine-checkable pre-push verification protocol.
# Run before every git push and post the complete output as evidence.
#
# Usage:
#   bash scripts/pre_push_check.sh [--suite pipeline|gameworks|all]
#
# --suite pipeline  (default) python -m unittest discover -s tests
# --suite gameworks pytest tests/test_gameworks_engine.py + renderer headless
# --suite all       same as pipeline (full repo suite)
#
# Exit code: 0 = all mechanical checks passed
#            1 = one or more mechanical checks failed
#
# Steps 3, 4, and 7 require reasoning and cannot be automated; this script
# covers Steps 1, 2, 5, and 6 only.

set -uo pipefail

# ── Argument parsing ──────────────────────────────────────────────────────────
SUITE="pipeline"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --suite) SUITE="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# ── Paths ─────────────────────────────────────────────────────────────────────
BASELINE="${TMPDIR:-/tmp}/pre_push_baseline.txt"
AFTER="${TMPDIR:-/tmp}/pre_push_after.txt"

# ── Helpers ───────────────────────────────────────────────────────────────────
STATUS=0
CHECKS_RUN=0
CHECKS_PASSED=0

hr() {
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
}

pass() { echo "  PASS: $1"; CHECKS_PASSED=$((CHECKS_PASSED + 1)); }
fail() { echo "  FAIL: $1"; STATUS=1; }
warn() { echo "  WARN: $1"; }

check_start() { CHECKS_RUN=$((CHECKS_RUN + 1)); }

# ── Header ────────────────────────────────────────────────────────────────────
hr
echo " PRE-PUSH VERIFICATION  —  $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo " Suite: $SUITE"
echo " Baseline: $BASELINE"
hr

# ── Step 1: Staged diff (ground truth) ───────────────────────────────────────
echo ""
echo "── STEP 1: STAGED DIFF ─────────────────────────────────────────────────"
check_start
STAGED="$(git diff --staged 2>&1)"
if [ -z "$STAGED" ]; then
    warn "Nothing is staged. Did you forget 'git add'?"
    warn "If intentional (e.g. checking clean tree), this is fine."
else
    echo "$STAGED"
    pass "Staged diff printed — read every hunk before continuing."
fi

# ── Step 2: Diff stat — scope cross-check ────────────────────────────────────
echo ""
echo "── STEP 2: DIFF STAT ───────────────────────────────────────────────────"
check_start
STAT="$(git diff --staged --stat 2>&1)"
if [ -z "$STAT" ]; then
    warn "No staged changes — stat is empty."
else
    echo "$STAT"
    echo ""
    echo "  Review counts above against stated task scope."
    echo "  Draft the commit message AFTER reading this — not before."
    pass "Diff stat printed."
fi

# ── Step 5a: AST parse ────────────────────────────────────────────────────────
echo ""
echo "── STEP 5: AST PARSE ───────────────────────────────────────────────────"
# Use process substitution to avoid word-splitting issues with filenames.
mapfile -t PY_FILES < <(git diff --staged --name-only | grep '\.py$' || true)

check_start
if [ ${#PY_FILES[@]} -eq 0 ]; then
    pass "No .py files in staged diff — skipping AST parse."
else
    AST_FAIL=0
    for f in "${PY_FILES[@]}"; do
        if [ ! -f "$f" ]; then
            warn "Staged file not found on disk (deleted?): $f"
            continue
        fi
        if python -c "import ast; ast.parse(open('$f').read())" 2>&1; then
            echo "  AST OK: $f"
        else
            fail "AST parse failed: $f"
            AST_FAIL=1
        fi
    done
    if [ $AST_FAIL -eq 0 ]; then
        pass "All ${#PY_FILES[@]} staged .py file(s) parse cleanly."
    fi
fi

# ── Step 5b: Pyflakes ─────────────────────────────────────────────────────────
echo ""
echo "── STEP 5: PYFLAKES ────────────────────────────────────────────────────"
check_start
if [ ${#PY_FILES[@]} -eq 0 ]; then
    pass "No .py files in staged diff — skipping pyflakes."
elif ! python -m pyflakes --version >/dev/null 2>&1; then
    warn "pyflakes not installed. Install with: pip install pyflakes"
    warn "Skipping — resolve before pushing in a pyflakes-capable environment."
else
    PYFLAKES_OUT="$(python -m pyflakes "${PY_FILES[@]}" 2>&1 || true)"
    if [ -z "$PYFLAKES_OUT" ]; then
        pass "Pyflakes clean on all ${#PY_FILES[@]} staged .py file(s)."
    else
        echo "$PYFLAKES_OUT"
        fail "Pyflakes reported issues — resolve above before pushing."
    fi
fi

# ── Step 6: Test suite ────────────────────────────────────────────────────────
echo ""
echo "── STEP 6: TEST SUITE ($SUITE) ─────────────────────────────────────────"
check_start

run_suite() {
    case "$1" in
        gameworks)
            if command -v pytest >/dev/null 2>&1; then
                SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
                    pytest tests/test_gameworks_engine.py \
                           tests/test_gameworks_renderer_headless.py -v
            else
                echo "pytest not found — install with: pip install pytest" >&2
                return 1
            fi
            ;;
        all|pipeline|*)
            python -m unittest discover -s tests -p "test_*.py"
            ;;
    esac
}

set +e
run_suite "$SUITE" 2>&1 | tee "$AFTER"
SUITE_EXIT=${PIPESTATUS[0]}
set -e

if [ "$SUITE_EXIT" -eq 0 ]; then
    pass "Test suite exited 0."
else
    fail "Test suite exited $SUITE_EXIT — review output above."
fi

# ── Step 6: Baseline comparison ───────────────────────────────────────────────
echo ""
echo "── STEP 6: BASELINE COMPARISON ─────────────────────────────────────────"
check_start
if [ ! -f "$BASELINE" ]; then
    warn "No baseline file found at $BASELINE"
    warn "Capture it before your next edit session with:"
    warn "  git stash"
    warn "  python -m unittest discover -s tests -p \"test_*.py\" 2>&1 | tee $BASELINE"
    warn "  git stash pop"
    warn "Skipping comparison — pre-existing vs new failures cannot be distinguished."
else
    DIFF_OUT="$(diff "$BASELINE" "$AFTER" || true)"
    if [ -z "$DIFF_OUT" ]; then
        pass "Test results identical to baseline — no new failures introduced."
    else
        echo "$DIFF_OUT"
        echo ""
        echo "  Lines prefixed '+' appear only in the after-run (potential new failures)."
        echo "  Lines prefixed '-' appear only in the baseline (tests that now pass or changed)."
        echo "  Review every '+' line. New FAIL or ERROR lines are regressions."
        # Not a hard failure — agent must reason about the diff
        pass "Baseline diff printed — agent must classify new vs pre-existing failures."
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
hr
echo " MECHANICAL CHECKS SUMMARY"
echo " Ran: $CHECKS_RUN  |  Passed: $CHECKS_PASSED  |  Failed: $((CHECKS_RUN - CHECKS_PASSED))"
echo ""
if [ $STATUS -eq 0 ]; then
    echo " ALL MECHANICAL CHECKS PASSED."
    echo ""
    echo " Still required before pushing (cannot be automated):"
    echo "   Step 3 — Trace each fix end-to-end; name the concrete wrong value on regression."
    echo "   Step 4 — Audit for partial fixes and out-of-scope hunks in the diff."
    echo "   Step 7 — Verify each new test would fail without the change (Method A or B)."
else
    echo " ONE OR MORE MECHANICAL CHECKS FAILED — do not push until resolved."
fi
hr

exit $STATUS
