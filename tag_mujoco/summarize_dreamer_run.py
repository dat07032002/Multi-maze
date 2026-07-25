"""Print a compact, read-only summary of a Dreamer JSONL run."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


def _finite_mean(values: List[float]) -> float | None:
    finite = [value for value in values if math.isfinite(value)]
    return float(np.mean(finite)) if finite else None


def summarize(logdir: Path) -> Dict[str, Any]:
    metrics_path = logdir / "metrics.jsonl"
    records = [
        json.loads(line)
        for line in metrics_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    episodes = [record for record in records if "episode/score" in record]
    train_records = [record for record in records if "train/model_opt_grad_steps" in record]
    latest = max(records, key=lambda record: float(record.get("step", -1)))
    latest_train = train_records[-1] if train_records else {}
    recent = episodes[-20:]
    checkpoint = logdir / "checkpoint.ckpt"
    return {
        "logdir": str(logdir),
        "latest_step": int(latest.get("step", 0)),
        "metric_records": len(records),
        "episodes_logged": len(episodes),
        "successful_episodes": sum(
            float(record.get("stats/sum_log_success", 0.0)) > 0.0 for record in episodes
        ),
        "fall_episodes": sum(
            float(record.get("stats/sum_log_fall_cost", 0.0)) > 0.0 for record in episodes
        ),
        "recent_mean_score": _finite_mean(
            [float(record["episode/score"]) for record in recent]
        ),
        "recent_mean_progress": _finite_mean(
            [float(record.get("stats/mean_log_progress", math.nan)) for record in recent]
        ),
        "recent_mean_cross_track_error_m": _finite_mean(
            [
                float(record.get("stats/mean_log_cross_track_error", math.nan))
                for record in recent
            ]
        ),
        "latest_train": {
            key: latest_train.get(key)
            for key in (
                "step",
                "train/model_loss_mean",
                "train/image_loss_mean",
                "train/reward_loss_mean",
                "train/model_opt_grad_norm",
                "train/model_opt_grad_steps",
                "train/model_opt_model_opt_grad_overflow",
                "train/model_opt_model_opt_grad_scale",
                "train/actor_opt_grad_steps",
                "train/extr_critic_critic_opt_grad_steps",
                "fps",
                "replay/size",
            )
            if key in latest_train
        },
        "checkpoint_exists": checkpoint.is_file(),
        "checkpoint_bytes": checkpoint.stat().st_size if checkpoint.is_file() else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("logdir", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.logdir), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
