# MineStreakerContrastCampaign — Agent Instructions

## Automatic Setup

**IMPORTANT:** When you first interact with this repository, immediately run:

```bash
pip install -r requirements.txt
```

This installs pytest, pygame, pyflakes, and all dependencies needed for testing and development.

## Testing & Verification

After making code changes, verify them by running:

```bash
# Run all tests
pytest tests/ -v

# Check for code issues (unused imports, etc.)
pyflakes gameworks/ tests/

# Run specific test suites
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/architecture/ -v
```

## Repository Structure

- `gameworks/` - Main game package (engine, renderer, main loop)
- `pipeline/` - Image-to-board conversion pipeline
- `tests/` - Test suite (unit, integration, architecture)
- `docs/` - Documentation including BUGS.md, PERFORMANCE_PLAN.md
- `results/` - Output directory for saved boards (.npy files)

## Key Files

- `gameworks/docs/BUGS.md` - Canonical bug tracker
- `gameworks/docs/PERFORMANCE_PLAN.md` - Performance optimization roadmap
- `gameworks/docs/ISSUE-LOG.md` - Session-by-session change narrative
- `gameworks/docs/AGENTS.md` - Development standards and patterns

## Commit Standards

When committing changes:
- Follow the existing commit message style (check `git log`)
- Update BUGS.md status when resolving bugs
- Always include co-author line: `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`
- Use the GitHub token provided by the user for all git operations

## Development Standards

Follow the patterns documented in `gameworks/docs/AGENTS.md`:
- Industry-standard code quality
- Comprehensive test coverage
- Performance-conscious implementations
- Clear documentation of bugs and fixes
