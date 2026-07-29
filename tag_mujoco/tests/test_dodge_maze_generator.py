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
PROGRESS_MANIFEST = (
    ROOT
    / "tag_mujoco"
    / "generated_singlepath_progress_mazes"
    / "maze_splits_progress.json"
)
BRANCH_MANIFEST = (
    ROOT
    / "tag_mujoco"
    / "generated_branch_blocker_mazes"
    / "maze_splits_branch_blockers.json"
)


class DodgeMazeGeneratorTests(unittest.TestCase):
    def test_generated_dodge_maze_blocks_reference_and_replans_safe_path(self):
        layout, metadata = generate_dodge_maze(
            40003,
            DodgeMazeConfig(),
            PlannerConfig(),
        )
        reference = np.asarray(layout["reference_waypoints"], dtype=np.float64)
        safe = np.asarray(layout["waypoints"], dtype=np.float64)
        solution_cells = {tuple(cell) for cell in layout["solution_cells"]}
        branch_blocker_cells = {
            tuple(cell) for cell in metadata["branch_blocker_cells"]
        }
        self.assertEqual(metadata["config"]["loop_fraction"], 0.0)
        self.assertTrue(metadata["single_solution_topology"])
        self.assertGreater(metadata["wrong_branch_count"], 0)
        self.assertEqual(
            metadata["wrong_branch_count"], len(metadata["branch_blocker_cells"])
        )
        self.assertFalse(solution_cells & branch_blocker_cells)
        self.assertLess(float(np.min(signed_ball_clearance(layout, reference))), 0.0)
        self.assertTrue(validate_route(layout, safe, PlannerConfig()).passed)
        self.assertLess(metadata["original_route_min_clearance_m"], 0.0)
        self.assertGreaterEqual(
            metadata["safe_route_min_clearance_m"],
            PlannerConfig().safety_margin_m,
        )

    def test_staged_generation_can_remove_route_hazards_until_later_stage(self):
        progress_layout, progress_meta = generate_dodge_maze(
            40000,
            DodgeMazeConfig(block_wrong_branches=False, dodge_holes=0),
            PlannerConfig(),
        )
        self.assertTrue(progress_meta["single_solution_topology"])
        self.assertEqual(progress_meta["branch_blocker_cells"], [])
        self.assertEqual(progress_meta["dodge_hole_cells"], [])
        self.assertEqual(progress_layout["holes"], [])
        self.assertGreater(progress_meta["original_route_min_clearance_m"], 0.0)

        branch_layout, branch_meta = generate_dodge_maze(
            40000,
            DodgeMazeConfig(block_wrong_branches=True, dodge_holes=0),
            PlannerConfig(),
        )
        self.assertGreater(len(branch_meta["branch_blocker_cells"]), 0)
        self.assertEqual(branch_meta["dodge_hole_cells"], [])
        self.assertEqual(
            len(branch_layout["holes"]),
            len(branch_meta["branch_blocker_cells"]),
        )
        self.assertGreater(branch_meta["original_route_min_clearance_m"], 0.0)

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
        self.assertTrue(train.metadata[0]["single_solution_topology"])
        self.assertGreater(train.metadata[0]["branch_blocker_count"], 0)

    def test_staged_manifests_have_expected_hazard_progression(self):
        expected = (
            (
                PROGRESS_MANIFEST,
                "tag_singlepath_progress_v1",
                "singlepath_progress",
                0,
                0,
            ),
            (
                BRANCH_MANIFEST,
                "tag_singlepath_branch_blockers_v1",
                "singlepath_branch_blockers",
                1,
                0,
            ),
            (
                DODGE_MANIFEST,
                "tag_dodge_curriculum_v1",
                "easy_dodge_holes",
                1,
                1,
            ),
        )
        for manifest_path, dataset_id, stage, min_blockers, min_dodge in expected:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["dataset_id"], dataset_id)
            train = load_split("train", manifest_path)
            self.assertGreaterEqual(len(train.paths), 1)
            metadata = train.metadata[0]
            self.assertEqual(metadata["curriculum_stage"], stage)
            self.assertTrue(metadata["single_solution_topology"])
            self.assertGreaterEqual(metadata["branch_blocker_count"], min_blockers)
            self.assertGreaterEqual(metadata["dodge_hole_count"], min_dodge)


if __name__ == "__main__":
    unittest.main()
