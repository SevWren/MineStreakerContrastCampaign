"""Prompted launcher for completed Iter9 demo runs."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from demos.iter9_visual_solver.cli.commands import main as commands_main
from demos.iter9_visual_solver.io.artifact_paths import DemoArtifactPaths, resolve_artifact_paths

DEFAULT_CONFIG_PATH = Path("configs/demo/iter9_visual_solver_demo.default.json")
TEMP_CONFIG_ROOT = Path("temp/iter9_visual_solver_demo_prompted")

InputFunc = Callable[[str], str]
PrintFunc = Callable[..., None]

_SPEED_RE = re.compile(r"^\s*(?P<value>\d+(?:\.\d+)?)\s*x?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class PromptedLaunchConfig:
    run_dir: Path
    artifacts: DemoArtifactPaths
    speed_modifier: float
    auto_close: bool
    generated_config_path: Path


def normalize_prompted_path(value: str) -> Path:
    cleaned = value.strip().strip('"').strip("'")
    if not cleaned:
        raise ValueError("results directory is required")
    return Path(cleaned).expanduser()


def parse_speed_modifier(value: str) -> float:
    match = _SPEED_RE.match(value)
    if not match:
        raise ValueError("Enter a positive speed modifier like 50x, 100x, 150x, 200x, or 300x")
    modifier = float(match.group("value"))
    if modifier <= 0:
        raise ValueError("speed modifier must be greater than 0")
    return modifier


def parse_yes_no(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"y", "yes"}:
        return True
    if normalized in {"n", "no"}:
        return False
    raise ValueError("Enter Y or N")


def build_prompted_config_dict(default_config: dict, *, speed_modifier: float, auto_close: bool) -> dict:
    config = copy.deepcopy(default_config)
    playback = config["playback"]
    playback["min_events_per_second"] = _scale_int(
        playback["min_events_per_second"],
        speed_modifier,
        maximum=1_000_000,
    )
    playback["base_events_per_second"] = _scale_int(
        playback["base_events_per_second"],
        speed_modifier,
        maximum=1_000_000,
    )
    playback["mine_count_multiplier"] = min(
        10_000.0,
        float(playback["mine_count_multiplier"]) * float(speed_modifier),
    )
    playback["max_events_per_second"] = _scale_int(
        playback["max_events_per_second"],
        speed_modifier,
        maximum=10_000_000,
    )
    if playback["min_events_per_second"] > playback["max_events_per_second"]:
        playback["min_events_per_second"] = playback["max_events_per_second"]
    if playback["base_events_per_second"] > playback["max_events_per_second"]:
        playback["base_events_per_second"] = playback["max_events_per_second"]

    finish_behavior = config["window"]["finish_behavior"]
    finish_behavior["mode"] = "close_immediately" if auto_close else "stay_open"
    finish_behavior["close_after_seconds"] = None
    return config


def write_prompted_config(
    *,
    default_config_path: Path,
    temp_config_root: Path,
    run_dir: Path,
    speed_modifier: float,
    auto_close: bool,
) -> Path:
    default_config = json.loads(default_config_path.read_text(encoding="utf-8"))
    prompted_config = build_prompted_config_dict(
        default_config,
        speed_modifier=speed_modifier,
        auto_close=auto_close,
    )
    temp_config_root.mkdir(parents=True, exist_ok=True)
    config_path = temp_config_root / _generated_config_filename(
        run_dir=run_dir,
        speed_modifier=speed_modifier,
        auto_close=auto_close,
    )
    config_path.write_text(json.dumps(prompted_config, indent=2), encoding="utf-8")
    return config_path


def build_demo_argv(*, artifacts: DemoArtifactPaths, config_path: Path) -> list[str]:
    argv = [
        "--grid",
        str(artifacts.grid_path),
        "--metrics",
        str(artifacts.metrics_path),
        "--config",
        str(config_path),
    ]
    if artifacts.event_trace_path is not None:
        argv.extend(["--event-trace", str(artifacts.event_trace_path)])
    return argv


def collect_prompted_launch_config(
    *,
    input_func: InputFunc = input,
    print_func: PrintFunc = print,
    default_config_path: Path = DEFAULT_CONFIG_PATH,
    temp_config_root: Path = TEMP_CONFIG_ROOT,
) -> PromptedLaunchConfig:
    run_dir, artifacts = _prompt_for_artifacts(input_func=input_func, print_func=print_func)
    speed_modifier = _prompt_until_valid(
        input_func=input_func,
        print_func=print_func,
        prompt="Playback speed modifier (examples: 50x, 100x, 150x, 200x, 300x): ",
        parser=parse_speed_modifier,
    )
    auto_close = _prompt_until_valid(
        input_func=input_func,
        print_func=print_func,
        prompt="Automatically close upon finishing the last mine/playback? [Y/N]: ",
        parser=parse_yes_no,
    )
    generated_config_path = write_prompted_config(
        default_config_path=default_config_path,
        temp_config_root=temp_config_root,
        run_dir=run_dir,
        speed_modifier=speed_modifier,
        auto_close=auto_close,
    )
    return PromptedLaunchConfig(
        run_dir=run_dir,
        artifacts=artifacts,
        speed_modifier=speed_modifier,
        auto_close=auto_close,
        generated_config_path=generated_config_path,
    )


def prompted_main(
    *,
    input_func: InputFunc = input,
    print_func: PrintFunc = print,
    default_config_path: Path = DEFAULT_CONFIG_PATH,
    temp_config_root: Path = TEMP_CONFIG_ROOT,
) -> int:
    launch_config = collect_prompted_launch_config(
        input_func=input_func,
        print_func=print_func,
        default_config_path=default_config_path,
        temp_config_root=temp_config_root,
    )
    argv = build_demo_argv(
        artifacts=launch_config.artifacts,
        config_path=launch_config.generated_config_path,
    )
    print_func("")
    print_func(f"Launching demo from: {launch_config.run_dir}")
    print_func(f"Generated config: {launch_config.generated_config_path}")
    print_func(f"Playback speed modifier: {launch_config.speed_modifier:g}x")
    print_func(f"Auto-close on finish: {'yes' if launch_config.auto_close else 'no'}")
    return int(commands_main(argv))


def _scale_int(value: int | float, modifier: float, *, maximum: int) -> int:
    return min(int(maximum), max(1, int(round(float(value) * float(modifier)))))


def _generated_config_filename(*, run_dir: Path, speed_modifier: float, auto_close: bool) -> str:
    resolved = str(run_dir.resolve())
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:10]
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", run_dir.name).strip("._") or "iter9_run"
    close_label = "autoclose" if auto_close else "stayopen"
    return f"{safe_stem}_{speed_modifier:g}x_{close_label}_{digest}.json"


def _prompt_for_artifacts(*, input_func: InputFunc, print_func: PrintFunc) -> tuple[Path, DemoArtifactPaths]:
    while True:
        try:
            run_dir = normalize_prompted_path(input_func("Results directory for demo playback: "))
            artifacts = resolve_artifact_paths(run_dir)
            return run_dir, artifacts
        except Exception as exc:  # noqa: BLE001 - user prompt should recover from any invalid path error.
            print_func(f"Could not resolve demo artifacts: {exc}")


def _prompt_until_valid(
    *,
    input_func: InputFunc,
    print_func: PrintFunc,
    prompt: str,
    parser: Callable[[str], object],
):
    while True:
        try:
            return parser(input_func(prompt))
        except ValueError as exc:
            print_func(str(exc))


if __name__ == "__main__":
    raise SystemExit(prompted_main())
