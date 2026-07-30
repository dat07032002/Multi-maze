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
            "progress_reward_scale: 15.0",
            "hole_warning_m: 0.010",
            "hole_clearance_penalty: 0.03",
            "path_tracking_penalty: 0.08",
            "wall_riding_penalty: 0.03",
        ):
            self.assertIn(expected, profile)

    def test_scratch_curriculum_profiles_progress_before_style(self):
        progress = profile_block("tag_sim_v2_singlepath_progress")
        for expected in (
            "random_start: True",
            "start_curriculum: True",
            "maze_manifest: tag_mujoco/generated_singlepath_progress_mazes/maze_splits_progress.json",
            "progress_reward_scale: 15.0",
            "path_tracking_penalty: 0.0",
            "wall_riding_penalty: 0.0",
        ):
            self.assertIn(expected, progress)
        branch = profile_block("tag_sim_v2_branch_blockers")
        for expected in (
            "maze_manifest: tag_mujoco/generated_branch_blocker_mazes/maze_splits_branch_blockers.json",
            "hole_clearance_penalty: 0.01",
            "path_tracking_penalty: 0.02",
            "wall_riding_penalty: 0.0",
        ):
            self.assertIn(expected, branch)
        dodge = profile_block("tag_sim_v2_dodge_progress")
        for expected in (
            "maze_manifest: tag_mujoco/generated_dodge_mazes/maze_splits_dodge.json",
            "hole_clearance_penalty: 0.02",
            "path_tracking_penalty: 0.03",
            "wall_riding_penalty: 0.01",
        ):
            self.assertIn(expected, dodge)

    def test_v2_launcher_routes_scratch_curriculum_profiles_to_stage_datasets(self):
        launcher = (ROOT / "scripts" / "run_tag_v2_gpu2.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("tag_sim_v2_singlepath_progress)", launcher)
        self.assertIn("tag_sim_v2_branch_blockers)", launcher)
        self.assertIn("tag_sim_v2_dodge_progress|tag_sim_v2_easy_dodge_holes)", launcher)
        self.assertIn("generated_singlepath_progress_mazes/maze_splits_progress.json", launcher)
        self.assertIn("generated_branch_blocker_mazes/maze_splits_branch_blockers.json", launcher)
        self.assertIn("generated_dodge_mazes/maze_splits_dodge.json", launcher)
        self.assertIn('dataset_id="tag_singlepath_progress_v1"', launcher)
        self.assertIn('dataset_id="tag_singlepath_branch_blockers_v1"', launcher)
        self.assertIn('dataset_id="tag_dodge_curriculum_v1"', launcher)
        self.assertIn(
            "Curriculum skill continuation requires TAG_CHECKPOINT_MODE=agent_only",
            launcher,
        )

    def test_dreamer_defaults_declare_path_and_wall_reward_keys(self):
        defaults = profile_block("defaults")
        for expected in (
            "path_tracking_tolerance_m: 0.004",
            "path_tracking_penalty: 0.0",
            "wall_warning_m: 0.003",
            "wall_riding_penalty: 0.0",
        ):
            self.assertIn(expected, defaults)

    def test_paired_hole_profiles_are_float32_and_never_enable_dr(self):
        names = (
            "tag_sim_v2_phase1_noholes_fullstart_scratch",
            "tag_sim_v2_phase2_noholes_fullstart",
            "tag_sim_v2_phase3_branch_holes",
            "tag_sim_v2_phase4_easy_dodge",
            "tag_sim_v2_phase5_mixed_holes",
        )
        for name in names:
            profile = profile_block(name)
            self.assertIn("precision: float32", profile)
            self.assertIn("randomize_plant: False", profile)
            self.assertIn("randomization_curriculum: False", profile)
            self.assertIn("train_ratio: 8", profile)

    def test_paired_hole_profiles_follow_the_expected_manifests(self):
        expected = {
            "tag_sim_v2_phase1_noholes_fullstart_scratch": "no_holes",
            "tag_sim_v2_phase2_noholes_fullstart": "no_holes",
            "tag_sim_v2_phase3_branch_holes": "branch_holes",
            "tag_sim_v2_phase4_easy_dodge": "easy_dodge",
            "tag_sim_v2_phase5_mixed_holes": "mixed_holes",
        }
        for name, variant in expected.items():
            self.assertIn(
                f"paired_hole_curriculum/{variant}/maze_splits.json",
                profile_block(name),
            )

    def test_paired_phase1_always_starts_at_the_true_maze_entrance(self):
        profile = profile_block("tag_sim_v2_phase1_noholes_fullstart_scratch")
        self.assertIn("random_start: False", profile)
        self.assertIn("start_curriculum: False", profile)
        self.assertNotIn("start_curriculum_initial_min:", profile)
        self.assertNotIn("full_start_probability:", profile)

    def test_grouped_nohole_profiles_use_nested_uniform_full_start_training(self):
        expected = {
            "tag_sim_v2_noholes_group016": "016",
            "tag_sim_v2_noholes_group032": "032",
            "tag_sim_v2_noholes_group064": "064",
            "tag_sim_v2_noholes_group128": "128",
            "tag_sim_v2_noholes_group512": "512",
        }
        for name, size in expected.items():
            profile = profile_block(name)
            for setting in (
                "precision: float32",
                f"maze_splits_group_{size}.json",
                "maze_sampling: uniform",
                "random_start: False",
                "start_curriculum: False",
                "randomize_plant: False",
                "randomization_curriculum: False",
                "train_ratio: 8",
            ):
                self.assertIn(setting, profile)

    def test_grouped_launcher_guards_scratch_and_warm_start_transitions(self):
        launcher = (ROOT / "scripts" / "run_tag_v2_gpu2.sh").read_text(
            encoding="utf-8"
        )
        stage = (ROOT / "scripts" / "start_grouped_nohole_stage.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("The 16-map group must start from scratch.", launcher)
        self.assertIn(
            "Grouped no-hole stages after 16 require TAG_CHECKPOINT_MODE=agent_only.",
            launcher,
        )
        self.assertIn("TAG_SPLIT=dev", stage)
        self.assertIn("maze_splits_group_${code}.json", stage)


if __name__ == "__main__":
    unittest.main()
