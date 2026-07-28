"""Add a deterministic development subset of the training split to a manifest.

The mastery gate is measured on the held-out validation split. Choosing
hyperparameters from validation feedback would overfit the split that decides
the gate, and the test split must stay untouched for the final report. This
tool therefore carves a fixed development subset out of the training layouts.

The policy trains on these layouts, so absolute development scores are
optimistic. They are only valid for ranking configurations against each other.

The subset matches the validation split's difficulty-band composition and is
spread evenly across each band's difficulty ordering, so it is not accidentally
concentrated in the easiest or hardest layouts of a band.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from maze_dataset import load_manifest


def select_dev_layouts(
    manifest: dict, size: int, reference_split: str
) -> list[str]:
    metadata = manifest["metadata"]
    wanted = collections.Counter(
        metadata[relative]["difficulty_band"] for relative in manifest[reference_split]
    )
    total = sum(wanted.values())
    if total != size:
        # Rescale the reference composition to the requested size, largest
        # remainder first, so band proportions are preserved exactly.
        exact = {band: count * size / total for band, count in wanted.items()}
        wanted = collections.Counter({band: int(value) for band, value in exact.items()})
        remainder = sorted(
            exact, key=lambda band: exact[band] - int(exact[band]), reverse=True
        )
        for band in remainder[: size - sum(wanted.values())]:
            wanted[band] += 1

    by_band: dict[str, list[str]] = collections.defaultdict(list)
    for relative in manifest["train"]:
        by_band[metadata[relative]["difficulty_band"]].append(relative)

    selected: list[str] = []
    for band in sorted(wanted):
        count = wanted[band]
        # Deterministic order by difficulty then seed, then an even stride over
        # the band. No RNG, so the subset is reproducible from the manifest.
        candidates = sorted(
            by_band[band],
            key=lambda relative: (
                float(metadata[relative]["difficulty_score"]),
                int(metadata[relative]["seed"]),
            ),
        )
        if count > len(candidates):
            raise ValueError(
                f"Training band {band!r} has {len(candidates)} layouts, need {count}"
            )
        for index in range(count):
            position = round((index + 0.5) * len(candidates) / count) - 1
            selected.append(candidates[max(0, min(position, len(candidates) - 1))])

    if len(set(selected)) != size:
        raise ValueError(f"Selection produced {len(set(selected))} unique layouts, want {size}")
    # Store in manifest training order for a stable, reviewable diff.
    order = {relative: index for index, relative in enumerate(manifest["train"])}
    return sorted(selected, key=lambda relative: order[relative])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--size", type=int, default=64)
    parser.add_argument("--reference-split", default="validation")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing dev split"
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    if "dev" in manifest and not args.force:
        raise SystemExit("Manifest already defines a dev split; pass --force to replace")

    selected = select_dev_layouts(manifest, args.size, args.reference_split)
    manifest["dev"] = selected
    manifest.setdefault("split_policy_notes", {})["dev"] = (
        "Deterministic difficulty-stratified subset of train for tuning decisions. "
        "The policy trains on it, so scores are optimistic and only valid for ranking."
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )

    metadata = manifest["metadata"]
    bands = collections.Counter(metadata[relative]["difficulty_band"] for relative in selected)
    print(f"Wrote dev split of {len(selected)} layouts to {manifest_path}")
    print(f"Bands: {dict(sorted(bands.items()))}")
    scores = [float(metadata[relative]["difficulty_score"]) for relative in selected]
    print(f"Difficulty score range: {min(scores):.3f}-{max(scores):.3f}")
    # Re-validate from disk so a bad write fails here rather than mid-training.
    load_manifest(manifest_path)
    print("Manifest revalidated successfully")


if __name__ == "__main__":
    main()
