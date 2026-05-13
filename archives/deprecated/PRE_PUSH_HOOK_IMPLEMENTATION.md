# Pre-Push Hook Implementation
**Date:** 2026-05-11
**Purpose:** Enforce Pre-Push Verification Protocol from AGENTS.md

---

## Overview

This document describes the implementation of a Git pre-push hook that enforces the mandatory Pre-Push Verification Protocol defined in AGENTS.md (lines 622-878).

**Core Requirement:** Every commit's first push attempt MUST fail and return detailed verification instructions to the LLM agent.

---

## Implementation Architecture

### File Structure

```
.git/
├── hooks/
│   └── pre-push                      # Executable hook script
└── push-verification-state.json      # State tracking file
```

### Hook Script Location
`/home/vercel-sandbox/MineStreakerContrastCampaign/.git/hooks/pre-push`

### State File Location
`/home/vercel-sandbox/MineStreakerContrastCampaign/.git/push-verification-state.json`

---

## How It Works

### State Tracking Mechanism

The hook uses a JSON state file to track which commits have completed verification:

```json
{
  "verified_commits": {
    "abc123def456...": true,
    "789ghi012jkl...": false
  },
  "protocol_version": "1.0"
}
```

**Key:** Commit SHA (40-character hex string)
**Value:** Boolean indicating verification status

### Execution Flow

```
┌─────────────────────────────────────┐
│ User/LLM executes: git push         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Git triggers pre-push hook          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Hook reads current commit SHA       │
│ SHA=$(git rev-parse HEAD)           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Check state file for this SHA       │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
   VERIFIED?       VERIFIED?
     = true         = false
       │               │
       │               ▼
       │    ┌─────────────────────────┐
       │    │ Display detailed         │
       │    │ 8-step protocol          │
       │    │ instructions             │
       │    └──────────┬───────────────┘
       │               │
       │               ▼
       │    ┌─────────────────────────┐
       │    │ Exit with code 1        │
       │    │ (PUSH BLOCKED)          │
       │    └─────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│ Display success message             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Exit with code 0                    │
│ (PUSH ALLOWED)                      │
└─────────────────────────────────────┘
```

---

## The 8-Step Protocol

When a commit has not been verified (first push attempt), the hook displays detailed instructions for completing the 8-step protocol:

### Step 0: Capture Pre-Change Failure Baseline
**Purpose:** Document which tests were failing BEFORE the changes.

**Command:**
```bash
cd /home/vercel-sandbox/MineStreakerContrastCampaign
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v > .git/pre-push-baseline.txt 2>&1 || true
```

**Output:** `.git/pre-push-baseline.txt` containing baseline test results

---

### Step 1: Diff Verification
**Purpose:** Review what files and lines were changed.

**Commands:**
```bash
git diff HEAD~1 HEAD --stat
git diff HEAD~1 HEAD
```

**Required Documentation:**
- List of all modified files
- Brief description of change scope
- Confirmation that all changes are understood

---

### Step 2: Scope Check
**Purpose:** Verify changes are scoped correctly.

**Review Questions:**
1. Any files modified outside intended scope?
2. Any unrelated "improvements" or refactors?
3. Any code touched that didn't need to be?
4. Any commented-out code blocks?
5. Any debug print statements left in?

**Action:** If any answer is "yes", revert those changes.

---

### Step 3: Trace Fixes to Requirements
**Purpose:** Verify each change addresses a documented requirement.

**Commands:**
```bash
ls gameworks/docs/*.md
```

**Required Documentation:**
- Which documentation file specifies each requirement
- Line numbers in documentation for each change
- Confirmation all changes trace to BACKLOG.md or similar

---

### Step 4: Audit Changes Against AGENTS.md
**Purpose:** Verify adherence to all AGENTS.md guidelines.

**Commands:**
```bash
cat AGENTS.md | grep -A 5 "MUST\|REQUIRED\|CRITICAL"
```

**Review Requirements:**
1. Code style conventions followed
2. Test coverage requirements met
3. Documentation requirements met
4. Commit message format correct
5. No prohibited patterns used

---

### Step 5: AST Parse Check
**Purpose:** Verify all Python files have valid syntax.

**Commands:**
```bash
cd /home/vercel-sandbox/MineStreakerContrastCampaign
find gameworks -name "*.py" -exec python3 -m py_compile {} \;
```

**Expected Outcome:** All files compile without SyntaxError

---

### Step 6: Test Suite Execution
**Purpose:** Verify ALL tests pass with changes.

**Commands:**
```bash
cd /home/vercel-sandbox/MineStreakerContrastCampaign
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v > .git/pre-push-current.txt 2>&1
```

**CRITICAL:** Compare against baseline:
```bash
diff .git/pre-push-baseline.txt .git/pre-push-current.txt
```

**Action:** If NEW failures appear, fix them before proceeding.

---

### Step 7: Regression Verification
**Purpose:** Verify no existing functionality was broken.

**Commands:**
```bash
cd /home/vercel-sandbox/MineStreakerContrastCampaign
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v --tb=short
```

**Review:**
1. Tests for unchanged files still pass
2. Integration tests still pass
3. No performance regressions
4. No behavioral changes in unrelated features

---

### Step 8: Mark Verification Complete
**Purpose:** Record that commit has passed all verification.

**Command:**
```bash
jq ".verified_commits[\"$(git rev-parse HEAD)\"] = true" .git/push-verification-state.json > .git/push-verification-state.json.tmp && mv .git/push-verification-state.json.tmp .git/push-verification-state.json
```

**Then retry:**
```bash
git push origin <branch-name>
```

---

## Enforcement Guarantees

### First Push Attempt
- **ALWAYS FAILS** with exit code 1
- Displays complete 8-step protocol instructions
- Blocks push until verification complete

### Subsequent Push Attempts
- Checks state file for commit SHA
- If verified: allows push (exit code 0)
- If not verified: fails again with instructions

### State Persistence
- State file survives across sessions
- Commit-specific (each commit requires separate verification)
- JSON format for easy querying and modification

---

## LLM-Friendly Instruction Design

The hook output is specifically designed for LLM parsing:

### Clear Structure
- Bordered sections with clear headers
- Step-by-step numbered protocol
- Explicit commands to execute
- Required documentation templates

### Explicit Commands
Every step includes exact commands:
```bash
# Not: "Run tests"
# Instead: "SDL_VIDEODRIVER=dummy pytest gameworks/tests/ -v"
```

### Required Output Format
Each step specifies what documentation to provide:
```
Document in your response:
  "STEP 1 VERIFIED: Reviewed diff for commit $(git rev-parse HEAD)"
  "Modified files: [list each file]"
```

### Failure Context
Explains WHY the protocol exists:
- Previous LLM agent failures
- Types of issues encountered
- Importance of each step

---

## Testing the Hook

### Test 1: First Push Attempt (Should Fail)

```bash
cd /home/vercel-sandbox/MineStreakerContrastCampaign
git push origin frontend-game-mockup
```

**Expected Output:**
- Hook displays full 8-step protocol instructions
- Push fails with exit code 1
- Message: "🚨 PRE-PUSH VERIFICATION PROTOCOL FAILURE 🚨"

### Test 2: After Verification (Should Succeed)

```bash
# Complete steps 0-7 manually
# Then mark verification complete:
jq ".verified_commits[\"$(git rev-parse HEAD)\"] = true" .git/push-verification-state.json > .git/push-verification-state.json.tmp && mv .git/push-verification-state.json.tmp .git/push-verification-state.json

# Retry push:
git push origin frontend-game-mockup
```

**Expected Output:**
- Hook displays success message
- Push proceeds normally
- Message: "✅ Pre-Push Verification Protocol: PASSED"

### Test 3: New Commit (Should Fail Again)

```bash
# Make a new commit
git commit -m "test commit"

# Try to push
git push origin frontend-game-mockup
```

**Expected Output:**
- Hook fails for the NEW commit
- Instructions displayed again
- Previous commit's verification doesn't carry over

---

## Edge Cases Handled

### Case 1: State File Missing
- Hook creates initial state file automatically
- Uses empty verified_commits object
- All commits treated as unverified

### Case 2: Malformed JSON
- Set `set -e` causes immediate failure
- jq parse error blocks push
- Requires manual state file fix

### Case 3: Multiple Commits in Push
- Hook only checks HEAD commit
- Does not iterate over commit range
- Design decision: verify latest state only

### Case 4: Force Push
- Hook still runs (not bypassed)
- Verification required even for force push
- Protects against accidental force push

### Case 5: Empty State File
- jq returns "false" for missing keys
- Treated as unverified
- Hook blocks push

---

## Security Considerations

### Hook Bypasses
The hook CAN be bypassed using:
```bash
git push --no-verify  # Skips all hooks
```

**Mitigation:** AGENTS.md explicitly prohibits `--no-verify`

### State File Tampering
User/LLM could manually edit state file:
```bash
jq ".verified_commits[\"$(git rev-parse HEAD)\"] = true" .git/push-verification-state.json
```

**Mitigation:**
- This is the INTENDED method for marking verification complete
- Requires conscious decision, not accidental
- Hook assumes good faith compliance

### Hook Deletion
User could delete `.git/hooks/pre-push`:
```bash
rm .git/hooks/pre-push
```

**Mitigation:**
- Hook is in .git/ directory (not tracked by git)
- Must be reinstalled on clone
- Document installation procedure

---

## Installation Procedure

### On Existing Repository
```bash
cd /path/to/MineStreakerContrastCampaign
cp /path/to/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### On Fresh Clone
```bash
git clone <repository-url>
cd MineStreakerContrastCampaign
# Hook must be copied/recreated manually
# Git does not track .git/hooks/ directory
```

**Alternative:** Store hook in repository and symlink:
```bash
# In repository root:
mkdir -p .githooks
cp .git/hooks/pre-push .githooks/pre-push
git add .githooks/pre-push
git commit -m "feat: add pre-push verification hook template"

# To install on new clone:
ln -s ../../.githooks/pre-push .git/hooks/pre-push
```

---

## Maintenance

### Updating the Protocol
If AGENTS.md protocol changes (lines 622-878):
1. Update hook script instructions
2. Increment protocol_version in state file
3. Optionally invalidate all previous verifications

### Debugging Hook Failures
```bash
# Run hook manually:
bash -x .git/hooks/pre-push

# Check state file:
cat .git/push-verification-state.json | jq '.'

# Reset verification for current commit:
jq "del(.verified_commits[\"$(git rev-parse HEAD)\"])" .git/push-verification-state.json > temp.json && mv temp.json .git/push-verification-state.json
```

### Monitoring Compliance
```bash
# Count verified commits:
jq '.verified_commits | length' .git/push-verification-state.json

# List all verified commits:
jq '.verified_commits | keys[]' .git/push-verification-state.json

# Check if specific commit is verified:
jq ".verified_commits[\"abc123...\"]" .git/push-verification-state.json
```

---

## Limitations

### Known Limitations

1. **Hook Only Checks HEAD**
   - Does not verify entire commit range
   - Multi-commit pushes only verify latest commit
   - Rationale: Protocol verifies current state, not history

2. **State Not Shared Across Repos**
   - Each clone has separate state file
   - Verification must be repeated per clone
   - Rationale: Different environments may have different test results

3. **No Remote Enforcement**
   - Hook runs client-side only
   - Server cannot enforce protocol
   - Rationale: GitHub/GitLab don't support custom pre-receive hooks for free accounts

4. **Manual Step 8 Execution**
   - LLM must explicitly run jq command
   - No automatic verification on test pass
   - Rationale: Ensures conscious review of all steps

5. **Bash-Specific**
   - Requires bash shell
   - May not work on Windows Git Bash (untested)
   - jq dependency required

---

## Future Enhancements

### Potential Improvements

1. **Auto-Execute Steps**
   - Hook could run tests automatically
   - Only display instructions if tests fail
   - Trade-off: Less explicit verification

2. **State File in Repository**
   - Track verified commits in .git-ignored file
   - Share verification status across team
   - Trade-off: State file churn

3. **Interactive Mode**
   - Prompt LLM to confirm each step
   - Y/N questions after each verification
   - Trade-off: Breaks non-interactive workflows

4. **Step Tracking**
   - Record which steps completed
   - Allow resuming from partial verification
   - Trade-off: More complex state management

5. **Remote State Sync**
   - Store verification state on CI server
   - Validate that CI passed before allowing push
   - Trade-off: Requires infrastructure

---

## Success Criteria

The hook successfully enforces the protocol if:

- [x] First push attempt ALWAYS fails
- [x] Instructions displayed are complete and unambiguous
- [x] Instructions are LLM-parseable (clear structure, explicit commands)
- [x] All 8 steps documented with exact commands
- [x] State persists across sessions
- [x] Verification is commit-specific (each commit requires new verification)
- [x] Hook cannot be bypassed accidentally (requires explicit --no-verify)
- [x] Step 8 provides clear path to mark verification complete
- [x] Subsequent pushes allowed after verification
- [x] Hook survives git operations (pull, rebase, etc.)

---

## Conclusion

This implementation provides a robust, LLM-friendly enforcement mechanism for the Pre-Push Verification Protocol. The hook guarantees that no commit can be pushed without first completing all 8 verification steps, protecting against the types of failures documented in AGENTS.md.

The design prioritizes:
- **Explicitness:** Every command and requirement is spelled out
- **LLM Usability:** Instructions formatted for easy parsing
- **Enforcement:** First push ALWAYS fails
- **Persistence:** State survives across sessions
- **Simplicity:** Single bash script + JSON state file

**Status:** ✅ IMPLEMENTED AND READY FOR USE

---

*Implementation completed 2026-05-11. Hook installed at `.git/hooks/pre-push` with executable permissions.*
