# Iter9 Visual Solver Demo

Standalone visual playback of MineStreaker solver events. Reads artifacts produced by
`run_iter9.py` and replays the solver decision sequence frame-by-frame in a Pygame window.

**Parent repo:** https://github.com/SevWren/MineStreakerContrastCampaign
**Pipeline branch:** `perf/board-gen-10x`

---

## Requirements

Python 3.10, 3.11, or 3.12. Install:

```bash
pip install -r requirements.txt
pip install pygame || pip install pygame-ce  # pygame-ce if source build fails on 3.13+
```

---

## Artifacts Required

Run `run_iter9.py` on the parent repo first. Required outputs:

| File | Required | Description |
|---|---|---|
| `results/<run_id>/grid_iter9_<board>.npy` | Yes | Board mine layout |
| `results/<run_id>/metrics_iter9_<board>.json` | Yes | Run metadata |
| `results/<run_id>/solver_event_trace.json` | Optional | Solver event replay |

Full schema: `demo/docs/artifact_consumption_contract.md`

---

## Running

```bash
python -m demos.iter9_visual_solver.cli.commands \
    --config configs/demo/iter9_visual_solver_demo.default.json
```

Windows prompted launcher:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File demo\run_iter9_visual_solver_demo_prompted.ps1
```

Edit `configs/demo/iter9_visual_solver_demo.default.json` to point at your pipeline
output directory. Schema: `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json`

---

## Testing

```bash
# Full suite
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"

# Architecture boundaries
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries

# Headless pygame
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes

# Lint
pyflakes demos tests/demo
```

---

## Documentation

All contracts live under `demo/docs/`:
- `architecture_decisions.md` — ADR-001–ADR-013
- `artifact_consumption_contract.md` — what artifacts the demo reads
- `playback_speed_contract.md` — playback speed SSOT
- `runtime_package_contract.md` — module ownership and import boundaries
- `json_schemas/` — JSON schema specs for config and event-trace formats
