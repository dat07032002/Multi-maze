from __future__ import annotations

import unittest

from tag_mujoco.apply_dynamics_fit import build_override


class DynamicsFitTest(unittest.TestCase):
    def test_quality_gated_override_converts_resistance_to_mu(self):
        fit = {
            "quality_gate": {
                "free_roll_usable": True,
                "restitution_usable": True,
                "warnings": [],
            },
            "free_roll": {
                "linear_damping_per_second": 0.8,
                "rolling_resistance_mps2": 0.03924,
                "tilt_acceleration_mps2_per_rad": [[0.0, 7.0], [-7.0, 0.0]],
            },
            "wall_impacts": {"median": 0.55, "p10": 0.45, "p90": 0.65},
        }
        result = build_override(fit, source="synthetic.json")
        self.assertAlmostEqual(
            result["rolling_friction_coefficient"]["value"], 0.004
        )
        self.assertAlmostEqual(
            result["linear_ball_damping_per_second"]["value"], 0.8
        )
        self.assertTrue(result["wall_restitution"]["applied"])

    def test_failed_free_roll_fit_is_not_activated_without_force(self):
        fit = {
            "quality_gate": {
                "free_roll_usable": False,
                "restitution_usable": False,
                "warnings": ["too few samples"],
            }
        }
        with self.assertRaisesRegex(ValueError, "too few samples"):
            build_override(fit)


if __name__ == "__main__":
    unittest.main()
