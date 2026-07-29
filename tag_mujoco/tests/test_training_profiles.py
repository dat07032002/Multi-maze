import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "dreamerv3" / "dreamerv3" / "configs.yaml"


def profile_block(name):
    text = CONFIGS.read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(name)}:\n(?P<body>.*?)(?=^\S|\Z)", text, re.M | re.S)
    if not match:
        raise AssertionError(f"Missing profile {name}")
    return match.group("body")


class TrainingProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = profile_block("tag_sim_v2_nominal_safe_resume")

    def test_nominal_safe_resume_uses_float32_after_checkpoint_transfer(self):
        self.assertIn("precision: float32", self.profile)
        self.assertIn("debug_nans: False", self.profile)

    def test_nominal_safe_resume_keeps_interpretable_no_dr_adaptation(self):
        for expected in (
            "random_start: False",
            "start_curriculum: False",
            "randomize_plant: False",
            "randomization_curriculum: False",
            "hole_clearance_penalty: 0.02",
        ):
            self.assertIn(expected, self.profile)

    def test_nominal_safe_resume_keeps_conservative_optimizers(self):
        for expected in (
            "train_ratio: 8",
            "train_fill: 50000",
            "count_prefill_steps: False",
            "demo_sampling: uniform_chunks",
            "model_opt: {opt: adam, lr: 3e-5",
            "actor_opt: {opt: adam, lr: 3e-6",
            "critic_opt: {opt: adam, lr: 3e-6",
        ):
            self.assertIn(expected, self.profile)

    def test_safe_path_tracking_profile_enables_path_and_wall_terms(self):
        profile = profile_block("tag_sim_v2_safe_path_tracking")
        for expected in (
            "precision: float32",
            "path_tracking_penalty: 0.20",
            "wall_riding_penalty: 0.05",
            "action_rate_penalty: 0.001",
            "hole_clearance_penalty: 0.02",
        ):
            self.assertIn(expected, profile)

    def test_easy_dodge_profile_enables_hole_path_and_wall_terms(self):
        profile = profile_block("tag_sim_v2_easy_dodge_holes")
        for expected in (
            "precision: float32",
            "maze_manifest: tag_mujoco/generated_dodge_mazes/maze_splits_dodge.json",
            "maze_split: train",
            "maze_sampling: plr",
            "hole_warning_m: 0.010",
            "hole_clearance_penalty: 0.05",
            "path_tracking_penalty: 0.15",
            "wall_riding_penalty: 0.05",
        ):
            self.assertIn(expected, profile)

    def test_v2_launcher_routes_dodge_profile_to_dodge_dataset(self):
        launcher = (ROOT / "scripts" / "run_tag_v2_gpu2.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("tag_sim_v2_easy_dodge_holes)", launcher)
        self.assertIn("generated_dodge_mazes/maze_splits_dodge.json", launcher)
        self.assertIn('dataset_id="tag_dodge_curriculum_v1"', launcher)
        self.assertIn("Scratch dodge training refuses TAG_FROM_CHECKPOINT", launcher)

    def test_dreamer_defaults_declare_path_and_wall_reward_keys(self):
        defaults = profile_block("defaults")
        for expected in (
            "path_tracking_tolerance_m: 0.004",
            "path_tracking_penalty: 0.0",
            "wall_warning_m: 0.003",
            "wall_riding_penalty: 0.0",
        ):
            self.assertIn(expected, defaults)


if __name__ == "__main__":
    unittest.main()
