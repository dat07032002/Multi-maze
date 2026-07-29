import unittest

import numpy as np

from tag_mujoco.validation_metrics import (
    episode_record,
    evaluation_env_overrides,
    summarize_records,
)


class ValidationMetricsTests(unittest.TestCase):
    def test_robust_evaluation_randomizes_plant_but_keeps_full_start(self):
        canonical = evaluation_env_overrides("canonical")
        robust = evaluation_env_overrides("robust")
        self.assertFalse(canonical["random_start"])
        self.assertFalse(canonical["randomize_plant"])
        self.assertFalse(robust["random_start"])
        self.assertTrue(robust["randomize_plant"])

    def test_unknown_evaluation_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluation_env_overrides("easy")

    def test_robust_evaluation_can_use_a_fixed_partial_strength(self):
        robust = evaluation_env_overrides("robust", 0.10, "physics")
        self.assertTrue(robust["randomize_plant"])
        self.assertTrue(robust["randomization_curriculum"])
        self.assertEqual(robust["randomization_initial_strength"], 0.10)
        self.assertEqual(robust["randomization_expand_step"], 0.0)
        self.assertEqual(robust["randomization_groups"], "physics")
        with self.assertRaises(ValueError):
            evaluation_env_overrides("canonical", 0.10)
        with self.assertRaises(ValueError):
            evaluation_env_overrides("robust", 0.0)

    def test_episode_and_aggregate_metrics(self):
        episode = {
            "reward": np.asarray([0.0, 0.2, 9.8], dtype=np.float32),
            "log_progress": np.asarray([[0.0], [0.4], [1.0]], dtype=np.float32),
            "log_cross_track_error": np.asarray([[0.01], [0.02], [0.03]]),
            "log_clearance_cost": np.asarray([[0.0], [0.1], [0.2]]),
            "log_min_clearance": np.asarray([[0.02], [0.015], [0.01]]),
            "log_success": np.asarray([[0.0], [0.0], [1.0]]),
            "log_fall_cost": np.zeros((3, 1)),
            "action": np.zeros((3, 2)),
            "log_dr_phys_mass": np.full((3, 1), 0.011),
        }
        record = episode_record(
            episode,
            layout="maze.json",
            layout_seed=42,
            difficulty_score=0.4,
            difficulty_band="medium",
            evaluation_seed=7,
        )
        self.assertTrue(record["success"])
        self.assertFalse(record["fall"])
        self.assertEqual(record["steps"], 2)
        self.assertAlmostEqual(record["max_route_completion"], 1.0)
        self.assertAlmostEqual(
            record["domain_randomization"]["dr_phys_mass"], 0.011
        )
        summary = summarize_records([record])["summary"]
        self.assertEqual(summary["completion_rate"], 1.0)
        self.assertEqual(summary["fall_rate"], 0.0)
        self.assertEqual(summary["mean_steps_to_goal"], 2.0)

    def test_nonfinite_action_is_rejected(self):
        episode = {
            "reward": np.zeros(2),
            "log_progress": np.zeros((2, 1)),
            "log_cross_track_error": np.zeros((2, 1)),
            "log_clearance_cost": np.zeros((2, 1)),
            "log_min_clearance": np.zeros((2, 1)),
            "log_success": np.zeros((2, 1)),
            "log_fall_cost": np.zeros((2, 1)),
            "action": np.asarray([[0.0, 0.0], [np.nan, 0.0]]),
        }
        with self.assertRaises(ValueError):
            episode_record(
                episode,
                layout="maze.json",
                layout_seed=1,
                difficulty_score=0.1,
                difficulty_band="easy",
                evaluation_seed=1,
            )


if __name__ == "__main__":
    unittest.main()
