from __future__ import annotations

import argparse
import fnmatch
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
    files = collect_files(ROOT)
    included = [str(path).replace("\\", "/") for path in files if not is_ignored(path, patterns)]

    output_path = (ROOT / args.output).resolve()
    output_path.write_text("\n".join(included) + ("\n" if included else ""), encoding="utf-8")
    print(f"Wrote {len(included)} file paths to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
