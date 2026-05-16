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
# Full gameworks suite (requires dummy SDL for headless renderer tests)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v

# Check for code issues (unused imports, etc.)
pyflakes gameworks/ gameworks/tests/

# Run specific gameworks suites
pytest gameworks/tests/unit/ gameworks/tests/architecture/ gameworks/tests/cli/ gameworks/tests/integration/ -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -v

# Pipeline / reconstruction tests (root test suite)
python -m unittest discover -s tests -p "test_*.py"
```

## Repository Structure

- `gameworks/` - Main game package (engine, renderer, main loop)
- `core.py`, `sa.py`, `solver.py`, `repair.py`, `pipeline.py`, etc. - Reconstruction pipeline (root-level modules)
- `demos/iter9_visual_solver/` - Visual solver demo package
- `tests/` - Root test suite (pipeline, benchmark, gameworks legacy regression guard)
- `gameworks/tests/` - Package-local gameworks test suite (unit, integration, renderer, CLI, architecture)
- `gameworks/docs/` - Documentation including BUGS.md, PERFORMANCE_PLAN.md
- `docs/` - Pipeline and governance documentation
- `results/` - Output directory for saved boards (.npy files)

## Key Files

- `gameworks/docs/BUGS.md` - Canonical bug tracker
- `gameworks/docs/PERFORMANCE_PLAN.md` - Performance optimization roadmap
- `gameworks/docs/CHANGELOG.md` - Version history
- `AGENTS.md` - Development standards and patterns (repo root)
- `docs/DOCS_INDEX.md` - Active vs archived documentation index

## Image-Reveal Pipeline Contract

`engine.py::load_board_from_pipeline()` is the sole gameworks call site for
image → Board construction. `main.py` must not import pipeline modules directly.
When SA/solver constants change in `run_iter9.py`, update the matching defaults in
`load_board_from_pipeline()` in the same commit.
Full rules: `AGENTS.md § Image-Reveal Pipeline Contract`.

## Commit Standards

When committing changes:
- Follow the existing commit message style (check `git log`)
- Update BUGS.md status when resolving bugs
- Always include co-author line: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- Use the GitHub token provided by the user for all git operations

## Development Standards

Follow the patterns documented in `AGENTS.md` (repo root):
- Industry-standard code quality
- Comprehensive test coverage
- Performance-conscious implementations
- Clear documentation of bugs and fixes
