"""Offline command-line tools for weakness reports and promotion decisions."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .promotion import PromotionGate, evaluation_summary
from .weakness import analyze_file


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def weaknesses_main() -> None:
    """Run the offline weakness analyzer CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze_file(args.episodes)
    _write(args.output, report)
    print(json.dumps(report["slices_worst_first"][:10], indent=2))


def promotion_main() -> None:
    """Run the non-mutating champion/candidate gate CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--champion-target", type=Path)
    parser.add_argument("--candidate-target", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    champion = evaluation_summary(
        json.loads(args.champion.read_text(encoding="utf-8"))
    )
    candidate = evaluation_summary(
        json.loads(args.candidate.read_text(encoding="utf-8"))
    )
    champion_target = (
        json.loads(args.champion_target.read_text(encoding="utf-8"))
        if args.champion_target
        else None
    )
    candidate_target = (
        json.loads(args.candidate_target.read_text(encoding="utf-8"))
        if args.candidate_target
        else None
    )
    decision = PromotionGate().evaluate(
        champion,
        candidate,
        champion_target=champion_target,
        candidate_target=candidate_target,
    )
    _write(args.output, decision)
    print(json.dumps(decision, indent=2))
    if not decision["passed"]:
        raise SystemExit(1)
