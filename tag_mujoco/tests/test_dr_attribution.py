import unittest

from tag_mujoco.dr_attribution import build_report


class DrAttributionTests(unittest.TestCase):
    def test_worst_family_is_ranked_and_scalars_are_reported(self):
        def result(mode, group, completion, fall, progress):
            episodes = [
                {
                    "success": index >= 4,
                    "fall": index < 2,
                    "max_route_completion": index / 9,
                    "domain_randomization": {"dr_phys_mass": 0.010 + index / 10000},
                }
                for index in range(10)
            ]
            return {
                "mode": mode,
                "randomization_groups": group,
                "summary": {
                    "completion_rate": completion,
                    "fall_rate": fall,
                    "mean_max_route_completion": progress,
                },
                "episodes": episodes,
                "checkpoint": "/checkpoint.ckpt",
                "checkpoint_sha256": "abc",
                "trigger_step": 10,
                "split": "dev",
                "seed": 1,
                "randomization_strength": 0.25 if mode == "robust" else 0.0,
            }

        report = build_report(
            [
                result("canonical", "none", 0.9, 0.05, 0.95),
                result("robust", "all", 0.6, 0.3, 0.75),
                result("robust", "actuator", 0.8, 0.1, 0.90),
                result("robust", "physics", 0.5, 0.4, 0.70),
                result("robust", "camera", 0.85, 0.08, 0.92),
            ]
        )
        self.assertEqual(
            report["family_impacts_worst_first"][0]["group"], "physics"
        )
        self.assertEqual(
            report["scalar_associations_observational"][0]["parameter"],
            "dr_phys_mass",
        )


if __name__ == "__main__":
    unittest.main()
