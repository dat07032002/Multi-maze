"""Build a finite, balanced, immutable replay rehearsal pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path
from typing import Any, Iterable

import numpy as np


REQUIRED_KEYS = {"image", "states", "goal", "action", "reward"}


def declared_length(path: Path, stored_length: int) -> int:
    try:
        length = int(path.stem.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return int(stored_length)
    return min(max(length, 0), int(stored_length))


def inspect_replay_file(path: Path) -> tuple[int, dict[str, Any]]:
    with np.load(path, allow_pickle=False) as episode:
        keys = tuple(episode.files)
        if not REQUIRED_KEYS.issubset(keys):
            raise ValueError(f"Incomplete replay file {path}: {sorted(keys)}")
        lengths = {len(episode[key]) for key in keys}
        if len(lengths) != 1:
            raise ValueError(f"Mismatched replay arrays in {path}: {sorted(lengths)}")
        stored = lengths.pop()
        valid = declared_length(path, stored)
        nonfinite = [
            key
            for key in keys
            if np.issubdtype(episode[key].dtype, np.number)
            and not np.all(np.isfinite(episode[key][:valid]))
        ]
    if nonfinite:
        raise ValueError(f"Non-finite valid replay prefix in {path}: {nonfinite}")
    return valid, {"stored_steps": stored, "valid_steps": valid, "keys": list(keys)}


def _stable_shuffle(paths: list[Path], label: str, seed: int) -> list[Path]:
    digest = hashlib.sha256(f"{seed}:{label}".encode()).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    result = list(paths)
    rng.shuffle(result)
    return result


def build_rehearsal_pack(
    sources: dict[str, Path],
    output: Path,
    *,
    steps_per_source: int = 10_000,
    quotas: dict[str, int] | None = None,
    before_mtimes: dict[str, float] | None = None,
    seed: int = 20260730,
) -> dict[str, Any]:
    if not sources:
        raise ValueError("At least one labeled replay source is required")
    if steps_per_source <= 0:
        raise ValueError("steps_per_source must be positive")
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Rehearsal output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    quotas = dict(quotas or {})
    before_mtimes = dict(before_mtimes or {})
    unknown = (set(quotas) | set(before_mtimes)).difference(sources)
    if unknown:
        raise ValueError(f"Quotas reference unknown sources: {sorted(unknown)}")

    report: dict[str, Any] = {
        "schema_version": 1,
        "selection": "deterministic shuffled complete files per labeled source",
        "seed": int(seed),
        "sources": {},
    }
    total_steps = 0
    for label, source in sorted(sources.items()):
        if not label or any(character in label for character in "/\\"):
            raise ValueError(f"Invalid rehearsal label: {label!r}")
        source = source.expanduser().resolve()
        if not source.is_dir():
            raise FileNotFoundError(f"Replay source does not exist: {source}")
        cutoff = before_mtimes.get(label)
        files = sorted(
            path
            for path in source.rglob("*.npz")
            if cutoff is None or path.stat().st_mtime <= float(cutoff)
        )
        if not files:
            raise ValueError(f"Replay source has no NPZ files: {source}")
        quota = int(quotas.get(label, steps_per_source))
        if quota <= 0:
            raise ValueError(f"Quota for {label!r} must be positive")
        destination_root = output / label
        destination_root.mkdir()
        selected = []
        selected_steps = 0
        rejected = []
        for path in _stable_shuffle(files, label, seed):
            try:
                valid, details = inspect_replay_file(path)
            except ValueError as error:
                rejected.append({"path": str(path), "reason": str(error)})
                continue
            destination = destination_root / path.name
            if destination.exists():
                destination = destination_root / f"{len(selected):06d}_{path.name}"
            # Use a real copy rather than a hard link: later replay writes or
            # cleanup in the source run must not mutate a promoted rehearsal
            # artifact through a shared inode.
            shutil.copy2(path, destination)
            transfer = "copy"
            selected.append(
                {
                    "source": str(path),
                    "destination": str(destination.relative_to(output)),
                    "valid_steps": valid,
                    "transfer": transfer,
                    **details,
                }
            )
            selected_steps += valid
            if selected_steps >= quota:
                break
        if selected_steps < quota:
            raise RuntimeError(
                f"Source {label!r} supplied {selected_steps}/{quota} finite steps"
            )
        report["sources"][label] = {
            "source": str(source),
            "before_mtime": cutoff,
            "quota_steps": quota,
            "selected_steps": selected_steps,
            "selected_files": selected,
            "rejected_files": rejected,
        }
        total_steps += selected_steps
    report["total_selected_steps"] = total_steps
    (output / "rehearsal_manifest.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return report


def _pairs(values: Iterable[str], name: str) -> dict[str, str]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{name} must use LABEL=VALUE syntax: {value!r}")
        label, item = value.split("=", 1)
        if label in result:
            raise ValueError(f"Duplicate {name} label: {label}")
        result[label] = item
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", default=[], metavar="LABEL=DIR")
    parser.add_argument("--quota", action="append", default=[], metavar="LABEL=STEPS")
    parser.add_argument(
        "--before-mtime", action="append", default=[], metavar="LABEL=EPOCH_SECONDS"
    )
    parser.add_argument("--steps-per-source", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260730)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_values = _pairs(args.source, "source")
    quota_values = _pairs(args.quota, "quota")
    before_values = _pairs(args.before_mtime, "before-mtime")
    report = build_rehearsal_pack(
        {label: Path(value) for label, value in source_values.items()},
        args.output,
        steps_per_source=args.steps_per_source,
        quotas={label: int(value) for label, value in quota_values.items()},
        before_mtimes={label: float(value) for label, value in before_values.items()},
        seed=args.seed,
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "sources": len(report["sources"]),
                "steps": report["total_selected_steps"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
