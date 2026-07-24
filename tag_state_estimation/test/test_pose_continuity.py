import math
import unittest

from tag_state_estimation.core.pose_continuity import (
    PoseContinuityGate,
    apply_published_angle_zero,
)


class PoseContinuityGateTest(unittest.TestCase):
    def test_applies_zero_in_published_alpha_beta_convention(self):
        # Internal (x, y)=(beta, -alpha). Published state before zeroing is
        # therefore alpha=20 degrees and beta=-2 degrees.
        raw = (math.radians(-2), math.radians(-20))
        corrected = apply_published_angle_zero(
            raw, alpha_zero_deg=20, beta_zero_deg=-2
        )
        self.assertAlmostEqual(corrected[0], 0.0)
        self.assertAlmostEqual(corrected[1], 0.0)

    def test_accepts_small_continuous_motion(self):
        gate = PoseContinuityGate()
        first = gate.update((math.radians(10), math.radians(-1)))
        second = gate.update((math.radians(11), math.radians(-2)))
        self.assertTrue(first.accepted)
        self.assertTrue(second.accepted)

    def test_rejects_wrong_absolute_pose_at_startup(self):
        gate = PoseContinuityGate(max_abs_deg=20)
        result = gate.update((math.radians(45), 0.0))
        self.assertFalse(result.accepted)
        self.assertTrue(all(math.isnan(value) for value in result.angles))

    def test_holds_only_a_bounded_number_of_bad_frames(self):
        gate = PoseContinuityGate(max_step_deg=3, hold_frames=2)
        valid = gate.update((math.radians(10), 0.0))
        bad_1 = gate.update((math.radians(34), 0.0))
        bad_2 = gate.update((math.radians(34), 0.0))
        bad_3 = gate.update((math.radians(34), 0.0))
        self.assertTrue(valid.accepted)
        self.assertEqual(bad_1.angles, valid.angles)
        self.assertEqual(bad_2.angles, valid.angles)
        self.assertTrue(all(math.isnan(value) for value in bad_3.angles))

    def test_valid_pose_recovers_after_rejection(self):
        gate = PoseContinuityGate(max_step_deg=3)
        valid = gate.update((math.radians(10), 0.0))
        gate.update((math.radians(34), 0.0))
        recovered = gate.update((math.radians(10.5), 0.0))
        self.assertTrue(valid.accepted)
        self.assertTrue(recovered.accepted)
        self.assertEqual(recovered.consecutive_rejections, 0)


if __name__ == "__main__":
    unittest.main()
