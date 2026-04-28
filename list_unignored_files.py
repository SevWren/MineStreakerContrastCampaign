from __future__ import annotations

import argparse
import fnmatch
import subprocess
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
GITIGNORE = ROOT / ".gitignore"


def load_patterns(path: Path) -> list[str]:
    patterns: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            continue
        patterns.append(line)
    return patterns


def path_variants(path: Path) -> list[str]:
    rel = path.as_posix()
    parts = rel.split("/")
    variants = {rel}
    for i in range(len(parts)):
        variants.add("/".join(parts[i:]))
    variants.add(path.name)
    return sorted(variants)


def matches_pattern(rel_path: Path, pattern: str) -> bool:
    rel = rel_path.as_posix()
    name = rel_path.name

    if pattern.endswith("/"):
        prefix = pattern[:-1].lstrip("./")
        if not prefix:
            return True
        return rel == prefix or rel.startswith(prefix + "/") or prefix in rel.split("/")

    anchored = pattern.startswith("/")
    body = pattern.lstrip("/")

    if "/" not in body:
        return fnmatch.fnmatch(name, body)

    candidates = [rel] if anchored else path_variants(rel_path)
    for candidate in candidates:
        if fnmatch.fnmatch(candidate, body):
            return True
    return False


def is_ignored(rel_path: Path, patterns: Iterable[str]) -> bool:
    ignored = False
    for pattern in patterns:
        if matches_pattern(rel_path, pattern):
            ignored = True
    return ignored


def collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.name != Path(__file__).name:
            files.append(path.relative_to(root))
    return sorted(files)


def _is_generated_binary_result(path: Path) -> bool:
    return path.parts[:1] == ("results",) and path.suffix.lower() in {
        ".png", ".jpg", ".jpeg", ".webp", ".npy", ".npz", ".gif", ".bmp", ".tif", ".tiff"
    }


def _run_git(root: Path, args: list[str]) -> list[str] | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root)] + args,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def collect_git_tracked_and_unignored_files(root: Path) -> list[Path]:
    """
    Prefer git ls-files / git check-ignore when available.
    Fall back to current pattern matcher otherwise.
    """
    tracked = _run_git(root, ["ls-files"])
    untracked = _run_git(root, ["ls-files", "--others", "--exclude-standard"])
    if tracked is None or untracked is None:
        return [path for path in collect_files(root) if not _is_generated_binary_result(path)]

    combined = {Path(line) for line in tracked}
    combined.update(Path(line) for line in untracked)
    filtered = [path for path in combined if (root / path).is_file() and not _is_generated_binary_result(path)]
    return sorted(filtered)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write a list of files that do not match .gitignore rules."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="unignored_files.txt",
        help="Output file path relative to the repo root.",
    )
    args = parser.parse_args()

    if not GITIGNORE.exists():
        raise FileNotFoundError(f"Missing .gitignore at {GITIGNORE}")

    patterns = load_patterns(GITIGNORE)
    files = collect_git_tracked_and_unignored_files(ROOT)
    if not files:
        files = collect_files(ROOT)
        files = [path for path in files if not _is_generated_binary_result(path)]
    included = [str(path).replace("\\", "/") for path in files if not is_ignored(path, patterns)]

    output_path = (ROOT / args.output).resolve()
    output_path.write_text("\n".join(included) + ("\n" if included else ""), encoding="utf-8")
    print(f"Wrote {len(included)} file paths to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
