from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


def _path_to_posix(path: Path) -> str:
    return path.as_posix()


def _resolve_path(value: str | Path, *, base_root: Path | None = None) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() and base_root is not None:
        candidate = base_root / candidate
    return candidate.resolve()


@dataclass(frozen=True)
class SourceImageConfig:
    command_arg: str
    absolute_path: Path
    project_relative_path: str | None
    name: str
    stem: str
    sha256: str
    size_bytes: int
    allow_noncanonical: bool
    manifest_path: str | None

    def to_metrics_dict(self) -> dict:
        return {
            "command_arg": self.command_arg,
            "project_relative_path": self.project_relative_path,
            "absolute_path": _path_to_posix(self.absolute_path),
            "name": self.name,
            "stem": self.stem,
            "sha256": self.sha256,
            "size_bytes": int(self.size_bytes),
            "allow_noncanonical": bool(self.allow_noncanonical),
            "manifest_path": self.manifest_path,
        }


def compute_file_sha256(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().lower()


def project_relative_or_none(path: Path, project_root: Path) -> str | None:
    path_resolved = path.resolve()
    root_resolved = project_root.resolve()
    try:
        relative = path_resolved.relative_to(root_resolved)
    except ValueError:
        return None
    return relative.as_posix()


def resolve_source_image_config(
    image_path: str,
    *,
    project_root: str | Path | None = None,
    allow_noncanonical: bool = False,
    manifest_path: str | None = None,
) -> SourceImageConfig:
    root = Path(project_root).resolve() if project_root is not None else None
    path = _resolve_path(image_path, base_root=root)
    if not path.exists():
        raise FileNotFoundError(f"Source image not found: {image_path}")
    if not path.is_file():
        raise FileNotFoundError(f"Source image is not a file: {image_path}")

    relative_root = root if root is not None else Path.cwd().resolve()
    project_relative = project_relative_or_none(path, relative_root)
    normalized_manifest = (
        _resolve_path(manifest_path, base_root=root).as_posix() if manifest_path else None
    )

    return SourceImageConfig(
        command_arg=image_path,
        absolute_path=path,
        project_relative_path=project_relative,
        name=path.name,
        stem=path.stem,
        sha256=compute_file_sha256(path),
        size_bytes=int(path.stat().st_size),
        allow_noncanonical=bool(allow_noncanonical),
        manifest_path=normalized_manifest,
    )
