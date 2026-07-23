"""Immutable multi-maze dataset manifest loading and validation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "maze_splits.json"
SPLIT_NAMES = ("smoke", "train", "validation", "test")


@dataclass(frozen=True)
class MazeSplit:
    name: str
    manifest_path: Path
    paths: tuple[Path, ...]
    metadata: tuple[Mapping[str, Any], ...]

    @property
    def difficulty_scores(self) -> tuple[float, ...]:
        return tuple(float(item.get("difficulty_score", 0.5)) for item in self.metadata)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> Dict[str, Any]:
    manifest_path = Path(path).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, manifest_path)
    return manifest


def validate_manifest(manifest: Mapping[str, Any], manifest_path: Path) -> None:
    if int(manifest.get("schema_version", 0)) < 2:
        raise ValueError("Multi-maze manifests require schema_version >= 2")
    base = manifest_path.parent.resolve()
    metadata = manifest.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise TypeError("Manifest metadata must be an object keyed by relative path")

    split_sets: Dict[str, set[str]] = {}
    for name in SPLIT_NAMES:
        entries = manifest.get(name)
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Manifest split {name!r} must be a non-empty list")
        if len(entries) != len(set(entries)):
            raise ValueError(f"Manifest split {name!r} contains duplicates")
        split_sets[name] = set(entries)
        for relative in entries:
            if not isinstance(relative, str):
                raise TypeError(f"Manifest split {name!r} contains a non-string path")
            resolved = (base / relative).resolve()
            try:
                resolved.relative_to(base)
            except ValueError as exc:
                raise ValueError(f"Manifest path escapes its dataset directory: {relative}") from exc
            if not resolved.is_file():
                raise FileNotFoundError(f"Manifest layout does not exist: {resolved}")
            item = metadata.get(relative)
            if not isinstance(item, Mapping):
                raise ValueError(f"Manifest metadata is missing for {relative}")
            expected_hash = item.get("sha256")
            if expected_hash and file_sha256(resolved) != expected_hash:
                raise ValueError(f"Immutable maze hash mismatch: {resolved}")

    if not split_sets["smoke"].issubset(split_sets["train"]):
        raise ValueError("The smoke split must be a subset of the training split")
    held_out = ("train", "validation", "test")
    for index, first in enumerate(held_out):
        for second in held_out[index + 1 :]:
            overlap = split_sets[first] & split_sets[second]
            if overlap:
                raise ValueError(f"Dataset leakage between {first} and {second}: {sorted(overlap)}")


def load_split(
    name: str,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    verify_hashes: bool = True,
) -> MazeSplit:
    path = Path(manifest_path).expanduser().resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if verify_hashes:
        validate_manifest(manifest, path)
    elif name not in manifest:
        raise KeyError(f"Unknown maze split {name!r}")
    if name not in SPLIT_NAMES:
        raise KeyError(f"Unknown maze split {name!r}; choose from {SPLIT_NAMES}")
    relatives: Sequence[str] = manifest[name]
    metadata = manifest["metadata"]
    return MazeSplit(
        name=name,
        manifest_path=path,
        paths=tuple((path.parent / relative).resolve() for relative in relatives),
        metadata=tuple(metadata[relative] for relative in relatives),
    )


def manifest_summary(path: str | Path = DEFAULT_MANIFEST) -> Dict[str, Any]:
    manifest_path = Path(path).expanduser().resolve()
    manifest = load_manifest(manifest_path)
    return {
        "dataset_id": manifest.get("dataset_id"),
        "manifest": str(manifest_path),
        "counts": {name: len(manifest[name]) for name in SPLIT_NAMES},
        "seeds": {
            name: [int(manifest["metadata"][relative]["seed"]) for relative in manifest[name]]
            for name in SPLIT_NAMES
        },
    }
