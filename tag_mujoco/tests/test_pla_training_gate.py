import unittest

from tag_mujoco.pla_training_gate import evaluate_gate


def evaluation(completion, falls, hard_progress):
    return {
        "summary": {
            "completion_rate": completion,
            "fall_rate": falls,
        },
        "by_difficulty": {
            "hard": {"mean_max_route_completion": hard_progress}
        },
    }


class PlaTrainingGateTests(unittest.TestCase):
    def setUp(self):
        self.baseline_canonical = evaluation(0.60, 0.30, 0.55)
        self.baseline_robust = evaluation(0.30, 0.40, 0.45)

    def test_accepts_robust_completion_gain_without_nominal_regression(self):
        result = evaluate_gate(
            self.baseline_canonical,
            self.baseline_robust,
            evaluation(0.58, 0.31, 0.51),
            evaluation(0.36, 0.39, 0.50),
        )
        self.assertTrue(result["passed"])

    def test_accepts_fall_reduction_as_robust_improvement(self):
        result = evaluate_gate(
            self.baseline_canonical,
            self.baseline_robust,
            evaluation(0.60, 0.30, 0.55),
            evaluation(0.32, 0.34, 0.47),
        )
        self.assertTrue(result["passed"])

    def test_rejects_canonical_or_hard_band_regression(self):
        canonical_regression = evaluate_gate(
            self.baseline_canonical,
            self.baseline_robust,
            evaluation(0.56, 0.30, 0.55),
            evaluation(0.36, 0.34, 0.50),
        )
        hard_regression = evaluate_gate(
            self.baseline_canonical,
            self.baseline_robust,
            evaluation(0.60, 0.30, 0.49),
            evaluation(0.36, 0.34, 0.50),
        )
        self.assertFalse(canonical_regression["passed"])
        self.assertFalse(hard_regression["passed"])


if __name__ == "__main__":
    unittest.main()
