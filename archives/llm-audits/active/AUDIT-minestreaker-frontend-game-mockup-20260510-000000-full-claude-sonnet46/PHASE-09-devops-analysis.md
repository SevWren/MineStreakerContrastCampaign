# PHASE 09 — DevOps Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Current State

| Tool | Status |
|---|---|
| requirements.txt | ✗ Missing |
| pyproject.toml | ✗ Missing |
| setup.py / setup.cfg | ✗ Missing |
| .github/workflows/ | ✗ Missing |
| .pre-commit-config.yaml | ✗ Missing |
| mypy.ini / pyrightconfig.json | ✗ Missing |
| ruff.toml / .ruff.toml | ✗ Missing |
| pytest.ini / pyproject.toml [pytest] | ✗ Missing |
| Makefile | ✗ Missing |
| Dockerfile | ✗ Missing |

## 2. Dependency Management

### Recommended requirements.txt
```
numpy>=1.24,<3.0
scipy>=1.10,<2.0
numba>=0.58,<1.0
Pillow>=10.0,<12.0
matplotlib>=3.7,<4.0
scikit-image>=0.21,<0.24
pygame>=2.4,<3.0
```

### Recommended pyproject.toml
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "minestreaker"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "numpy>=1.24",
    "scipy>=1.10",
    "numba>=0.58",
    "Pillow>=10.0",
    "matplotlib>=3.7",
    "scikit-image>=0.21",
    "pygame>=2.4",
]

[project.scripts]
minesweeper = "gameworks.main:main"
run-iter9 = "run_iter9:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = false
ignore_missing_imports = true
```

## 3. GitHub Actions CI

### Recommended .github/workflows/ci.yml
```yaml
name: CI

on:
  push:
    branches: [main, frontend-game-mockup]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov ruff

      - name: Lint with ruff
        run: ruff check .

      - name: Run tests
        env:
          SDL_VIDEODRIVER: dummy
          SDL_AUDIODRIVER: dummy
        run: pytest tests/ -v --cov=gameworks --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
```

## 4. Pre-commit Configuration

### Recommended .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=500']
```

## 5. Type Checking

### Recommended mypy invocation
```bash
mypy gameworks/ --ignore-missing-imports --no-strict-optional
```

Known mypy issues to address:
- `Optional` not imported in main.py
- `Board._state` not annotated
- `MoveResult.flagged: bool` vs actual `str` from `toggle_flag`

## 6. Release Automation

For future releases:
```yaml
# .github/workflows/release.yml
on:
  push:
    tags: ['v*']
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: pip install build && python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```
