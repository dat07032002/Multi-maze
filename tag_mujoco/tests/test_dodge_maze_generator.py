import json
import unittest
from pathlib import Path

import numpy as np

from tag_mujoco.dodge_maze_generator import (
    DodgeMazeConfig,
    generate_dodge_maze,
)
from tag_mujoco.maze_dataset import load_split
from tag_mujoco.route_planner import (
    PlannerConfig,
    signed_ball_clearance,
    validate_route,
)


ROOT = Path(__file__).resolve().parents[2]
DODGE_MANIFEST = ROOT / "tag_mujoco" / "generated_dodge_mazes" / "maze_splits_dodge.json"


class DodgeMazeGeneratorTests(unittest.TestCase):
    def test_generated_dodge_maze_blocks_reference_and_replans_safe_path(self):
        layout, metadata = generate_dodge_maze(
            40000,
            DodgeMazeConfig(),
            PlannerConfig(),
        )
        reference = np.asarray(layout["reference_waypoints"], dtype=np.float64)
        safe = np.asarray(layout["waypoints"], dtype=np.float64)
        self.assertLess(float(np.min(signed_ball_clearance(layout, reference))), 0.0)
        self.assertTrue(validate_route(layout, safe, PlannerConfig()).passed)
        self.assertLess(metadata["original_route_min_clearance_m"], 0.0)
        self.assertGreaterEqual(
            metadata["safe_route_min_clearance_m"],
            PlannerConfig().safety_margin_m,
        )

    def test_preview_manifest_uses_standard_train_validation_test_splits(self):
        manifest = json.loads(DODGE_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["dataset_id"], "tag_dodge_curriculum_v1")
        self.assertGreaterEqual(len(manifest["train"]), 1)
        self.assertGreaterEqual(len(manifest["validation"]), 1)
        self.assertGreaterEqual(len(manifest["test"]), 1)
        train = load_split("train", DODGE_MANIFEST)
        validation = load_split("validation", DODGE_MANIFEST)
        test = load_split("test", DODGE_MANIFEST)
        self.assertFalse(set(train.paths) & set(validation.paths))
        self.assertFalse(set(train.paths) & set(test.paths))
        self.assertEqual(train.metadata[0]["curriculum_stage"], "easy_dodge_holes")


if __name__ == "__main__":
    unittest.main()
