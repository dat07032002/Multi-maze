import unittest

from tag_mujoco.nominal_training_gate import evaluate_nominal_gate


def result(
    completion,
    falls,
    progress,
    hard_completion,
    hard_progress,
    episodes=192,
):
    return {
        "summary": {
            "episodes": episodes,
            "completion_rate": completion,
            "fall_rate": falls,
            "mean_max_route_completion": progress,
        },
        "by_difficulty": {
            "easy": {"completion_rate": completion},
            "medium": {"completion_rate": completion},
            "hard": {
                "completion_rate": hard_completion,
                "mean_max_route_completion": hard_progress,
            },
        },
    }


class NominalTrainingGateTests(unittest.TestCase):
    def setUp(self):
        self.baseline = result(0.67, 0.17, 0.82, 0.66, 0.74, episodes=64)

    def test_accepts_confirmed_nominal_mastery(self):
        candidate = result(0.92, 0.06, 0.96, 0.84, 0.95)
        decision = evaluate_nominal_gate(self.baseline, candidate)
        self.assertTrue(decision["continue_nominal"])
        self.assertTrue(decision["passed"])

    def test_single_seed_candidate_can_continue_but_not_claim_mastery(self):
        candidate = result(0.75, 0.12, 0.89, 0.71, 0.80, episodes=64)
        decision = evaluate_nominal_gate(self.baseline, candidate)
        self.assertTrue(decision["continue_nominal"])
        self.assertFalse(decision["passed"])
        self.assertFalse(
            decision["criteria"]["nominal_mastery"]["checks"][
                "confirmation_episodes"
            ]
        )

    def test_rejects_hard_band_regression(self):
        candidate = result(0.80, 0.10, 0.90, 0.50, 0.68, episodes=64)
        decision = evaluate_nominal_gate(self.baseline, candidate)
        self.assertFalse(decision["continue_nominal"])
        self.assertFalse(decision["passed"])


if __name__ == "__main__":
    unittest.main()
