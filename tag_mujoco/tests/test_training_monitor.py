import json
import math
import tempfile
import unittest
from pathlib import Path

from tag_mujoco.training_monitor import (
    PlateauConfig,
    dreamer_health,
    meaningful_validation_improvement,
    plateau_state,
    validation_weakness_report,
)


def _result(step, completion, falls, progress):
    return {
        "completed": True,
        "mode": "canonical",
        "trigger_step": step,
        "checkpoint": f"/run/step_{step}/checkpoint.ckpt",
        "summary": {
            "completion_rate": completion,
            "fall_rate": falls,
            "mean_max_route_completion": progress,
            "mean_cross_track_error_m": 0.01,
        },
        "episodes": [],
    }


class TrainingMonitorTests(unittest.TestCase):
    def test_meaningful_improvement_accepts_completion_delta(self):
        best = _result(0, 0.80, 0.10, 0.90)
        candidate = _result(500_000, 0.82, 0.10, 0.90)
        self.assertTrue(
            meaningful_validation_improvement(
                best, candidate, PlateauConfig(min_completion_delta=0.01)
            )
        )

    def test_plateau_trips_after_patience_without_meaningful_gain(self):
        config = PlateauConfig(
            patience=2,
            min_completion_delta=0.01,
            min_route_delta=0.005,
            max_fall_delta=0.005,
        )
        state = plateau_state(
            [
                _result(0, 0.90, 0.05, 0.95),
                _result(500_000, 0.905, 0.05, 0.951),
                _result(1_000_000, 0.904, 0.05, 0.952),
            ],
            config,
        )
        self.assertTrue(state["plateaued"])
        self.assertEqual(state["stale_count"], 2)
        self.assertEqual(state["best_trigger_step"], 0)

    def test_dreamer_health_marks_core_nonfinite_as_critical(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            (run_dir / "checkpoint.ckpt").write_bytes(b"ckpt")
            (run_dir / "metrics.jsonl").write_text(
                json.dumps(
                    {
                        "step": 100,
                        "episode/score": 1.0,
                        "train/model_opt_loss": math.nan,
                    },
                    allow_nan=True,
                )
                + "\n",
                encoding="utf-8",
            )
            health = dreamer_health(run_dir, stale_checkpoint_seconds=999999)
            self.assertEqual(health["status"], "critical")
            self.assertEqual(health["core_nonfinite_count"], 1)

    def test_weakness_report_ranks_failed_layouts(self):
        result = _result(500_000, 0.50, 0.25, 0.80)
        result["episodes"] = [
            {
                "layout": "easy.json",
                "difficulty_band": "easy",
                "success": True,
                "fall": False,
                "max_route_completion": 1.0,
                "mean_cross_track_error_m": 0.002,
                "minimum_clearance_m": 0.01,
            },
            {
                "layout": "hard.json",
                "difficulty_band": "hard",
                "success": False,
                "fall": True,
                "max_route_completion": 0.40,
                "mean_cross_track_error_m": 0.020,
                "minimum_clearance_m": -0.01,
            },
        ]
        report = validation_weakness_report(result, top_k=3)
        self.assertEqual(report["episodes"], 2)
        self.assertEqual(report["weaknesses"][0]["name"], "hard.json")
        self.assertEqual(report["weaknesses"][0]["kind"], "layout")


if __name__ == "__main__":
    unittest.main()
