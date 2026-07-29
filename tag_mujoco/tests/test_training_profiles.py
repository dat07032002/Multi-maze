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


if __name__ == "__main__":
    unittest.main()
