import math
import unittest

from tag_adaptation.control import (
    AdaptationConfig,
    AdaptationController,
    SafetyState,
)


def safe_state(**updates):
    values = {
        "ball_visible": True,
        "state_age_seconds": 0.01,
        "board_angles_rad": (0.0, 0.0),
        "hole_clearance_m": 0.02,
        "predicted_fall_probability": 0.0,
        "weakness_score": 1.0,
    }
    values.update(updates)
    return SafetyState(**values)


class AdaptationControllerTests(unittest.TestCase):
    def test_shadow_mode_never_executes_the_residual(self):
        controller = AdaptationController()
        decision = controller.decide((0.2, -0.2), (1.0, 1.0), safe_state())
        self.assertEqual(decision.executed_action, (0.2, -0.2))
        self.assertEqual(decision.proposed_residual, (0.15, 0.15))
        self.assertFalse(decision.residual_executed)

    def test_bounded_mode_requires_two_approvals(self):
        controller = AdaptationController(
            AdaptationConfig(mode="bounded", execution_enabled=False)
        )
        with self.assertRaises(PermissionError):
            controller.decide(
                (0.0, 0.0), (0.1, 0.1), safe_state(), execution_approved=True
            )
        controller = AdaptationController(
            AdaptationConfig(mode="bounded", execution_enabled=True)
        )
        with self.assertRaises(PermissionError):
            controller.decide((0.0, 0.0), (0.1, 0.1), safe_state())

    def test_bounded_residual_is_scaled_and_clipped(self):
        controller = AdaptationController(
            AdaptationConfig(
                mode="bounded",
                execution_enabled=True,
                maximum_action_rate=1.0,
            )
        )
        decision = controller.decide(
            (0.2, -0.2),
            (1.0, -1.0),
            safe_state(weakness_score=0.5),
            execution_approved=True,
        )
        self.assertEqual(decision.proposed_residual, (0.15, -0.15))
        self.assertEqual(decision.executed_action, (0.35, -0.35))
        self.assertTrue(decision.residual_executed)

    def test_risk_disables_residual_before_stop_threshold(self):
        controller = AdaptationController(
            AdaptationConfig(
                mode="bounded",
                execution_enabled=True,
                maximum_action_rate=1.0,
            )
        )
        decision = controller.decide(
            (0.2, 0.1),
            (0.1, 0.1),
            safe_state(predicted_fall_probability=0.6),
            execution_approved=True,
        )
        self.assertEqual(decision.executed_action, (0.2, 0.1))
        self.assertIn("fall_risk_disabled_residual", decision.reasons)

    def test_stale_missing_or_unsafe_state_stops(self):
        for state in (
            safe_state(ball_visible=False),
            safe_state(state_age_seconds=0.2),
            safe_state(board_angles_rad=(math.radians(11.0), 0.0)),
            safe_state(hole_clearance_m=0.0),
            safe_state(predicted_fall_probability=0.9),
        ):
            controller = AdaptationController()
            decision = controller.decide((0.4, 0.4), (0.0, 0.0), state)
            self.assertTrue(decision.stopped)
            self.assertEqual(decision.executed_action, (0.0, 0.0))

    def test_action_rate_and_clearance_limits_apply(self):
        controller = AdaptationController(
            AdaptationConfig(maximum_action_rate=0.1)
        )
        first = controller.decide((0.0, 0.0), (0.0, 0.0), safe_state())
        second = controller.decide(
            (1.0, -1.0),
            (0.0, 0.0),
            safe_state(hole_clearance_m=0.004),
        )
        self.assertEqual(first.executed_action, (0.0, 0.0))
        self.assertEqual(second.executed_action, (0.1, -0.1))
        self.assertIn("hole_clearance_attenuation", second.reasons)
        self.assertIn("action_rate_limit", second.reasons)


if __name__ == "__main__":
    unittest.main()
