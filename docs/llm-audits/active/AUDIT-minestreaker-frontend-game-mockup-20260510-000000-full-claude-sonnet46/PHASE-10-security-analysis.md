# PHASE 10 — Security Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Attack Surface Overview

This is a local desktop application with no network capabilities and no user authentication. The attack surface is narrow:
- File loading (`--image`, `--load` CLI args)
- `.npy` file parsing
- Image file parsing (PIL)
- SA kernel execution

## 2. Unsafe File Access / Path Traversal

### gameworks/engine.py — load_board_from_pipeline
**Location**: `gameworks/engine.py` ~lines 175-258
**Risk**: LOW

The `image_path` parameter is passed directly to `PIL.Image.open()`. If the image path comes from untrusted input (future web context), path traversal could expose arbitrary files. Currently, paths come from CLI args which requires user intent.

**Mitigation for web deployment**: Validate path is within an allowed directory before opening.

### gameworks/main.py — _save_npy
**Location**: `gameworks/main.py` ~lines 265-280
**Risk**: LOW

`np.save(fname, grid)` saves to CWD with a timestamp filename. No path validation. If CWD is sensitive, data could be written there.

**Mitigation**: Add configurable output directory. Default to user's home or a project-specific results directory.

## 3. Unsafe Deserialization

### numpy .npy Loading
**Location**: `gameworks/engine.py::load_board_from_npy` ~lines 159-175
**Risk**: MEDIUM

`np.load(path)` with default `allow_pickle=False` (numpy ≥ 1.16.3). This is safe for `.npy` files. However, if the path extension is `.npz` or contains serialized objects, this could be exploited.

**Current protection**: `np.load(path)` — allow_pickle defaults to False in modern numpy. Safe.
**Recommendation**: Explicitly pass `allow_pickle=False` for defense in depth.

### pipeline.py JSON Loading
JSON loading uses standard `json.load()` — no pickle deserialization. Safe.

## 4. subprocess / eval Misuse

### run_iter9.py — subprocess usage
**Location**: `run_iter9.py` (imports `subprocess`)
**Finding**: `subprocess` is imported but searching the file shows it's used for system info gathering (platform detection), not for executing user-provided strings.
**Risk**: LOW — no shell=True pattern found.

### No eval() Usage
No `eval()`, `exec()`, or `compile()` found in gameworks/ or pipeline modules. Safe.

## 5. SA Kernel — Numba JIT

### Cache Poisoning
Numba caches compiled kernels in `__pycache__/.numba_cache/`. If an attacker can write to this directory, they could inject malicious cached bytecode.
**Risk**: LOW for local desktop use. Medium for shared environments.
**Mitigation**: Ensure cache directory has appropriate permissions in shared deployments.

## 6. Save-File Exploitability

`.npy` files loaded by gameworks can theoretically be crafted to:
- Contain mismatched dimensions → `ValueError` (handled)
- Contain values designed to create pathological board states (many mines in corner, etc.)
- Cause very long `Board.__init__` by creating large boards

**Current defense**: `load_board_from_npy` validates neighbour counts. Size is not validated.
**Recommendation**: Add max board size validation: `if w * h > 500_000: raise ValueError(...)`.

## 7. Dependency Vulnerabilities

Without pinned dependency versions, vulnerability scanning is impossible. Key dependencies to monitor:
- `Pillow` — historically has had CVEs for image parsing (heap overflow, DoS via crafted images)
- `numpy` — occasional buffer overflow in `.npy` parsing
- `pygame` — image loading via SDL (SDL CVEs)

**Recommendation**: Pin dependencies in requirements.txt and run `pip-audit` or `safety check` in CI.

## 8. sys.path Manipulation

**Location**: `gameworks/engine.py::load_board_from_pipeline` ~lines 175-180
```python
_backup = _sys.path.copy()
project = str(Path(__file__).resolve().parents[2])
if project not in _sys.path:
    _sys.path.insert(0, project)
```
Then in `finally: _sys.path = _backup`

**Risk**: LOW but bad practice. The sys.path manipulation affects the entire interpreter. The `finally` block restores it but there's a window where the path is modified. In a future multi-threaded context, this would be a race condition.

**Recommendation**: Use proper package installation instead of sys.path hacking. Or use `importlib.util.spec_from_file_location()` if dynamic loading is needed.

## 9. Summary Risk Table

| Issue | OWASP Category | Risk | Status |
|---|---|---|---|
| Unconstrained file path in load_board_from_npy | Path Traversal (A01) | LOW | No immediate action |
| np.load without explicit allow_pickle=False | Insecure Deserialization (A08) | LOW | Add explicit kwarg |
| Unpinned dependencies with known CVEs | Vulnerable Components (A06) | MEDIUM | Pin in requirements.txt |
| sys.path mutation in library code | Not OWASP | LOW | Remove in refactor |
| No input validation on board dimensions | Improper Input Validation (A03) | LOW | Add size limits |
