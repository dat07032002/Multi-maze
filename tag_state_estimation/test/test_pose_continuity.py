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
        self.assertEqual(result.reason, "absolute_limit")
        self.assertTrue(all(math.isnan(value) for value in result.angles))

    def test_holds_only_a_bounded_number_of_bad_frames(self):
        gate = PoseContinuityGate(max_step_deg=3, hold_frames=2)
        valid = gate.update((math.radians(10), 0.0))
        bad_1 = gate.update((math.radians(34), 0.0))
        bad_2 = gate.update((math.radians(34), 0.0))
        bad_3 = gate.update((math.radians(34), 0.0))
        self.assertTrue(valid.accepted)
        self.assertEqual(bad_1.reason, "absolute_limit")
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
        self.assertEqual(recovered.reason, "accepted")
        self.assertEqual(recovered.consecutive_rejections, 0)

    def test_reports_non_finite_and_step_rejections(self):
        gate = PoseContinuityGate(max_step_deg=3)
        non_finite = gate.update((math.nan, 0.0))
        self.assertEqual(non_finite.reason, "non_finite")
        gate.update((0.0, 0.0))
        step = gate.update((math.radians(4), 0.0))
        self.assertEqual(step.reason, "step_limit")

    def test_reacquires_a_stable_pose_after_stale_reference(self):
        gate = PoseContinuityGate(max_step_deg=3, reacquire_frames=5)
        gate.update((0.0, 0.0))
        new_pose = (math.radians(5), math.radians(-1))
        results = [gate.update(new_pose) for _ in range(5)]
        self.assertTrue(all(not result.accepted for result in results[:4]))
        self.assertTrue(results[4].accepted)
        self.assertEqual(results[4].reason, "reacquired")
        self.assertEqual(results[4].angles, new_pose)

    def test_does_not_reacquire_inconsistent_candidates(self):
        gate = PoseContinuityGate(max_step_deg=3, reacquire_frames=3)
        gate.update((0.0, 0.0))
        candidates = [
            (math.radians(5), 0.0),
            (math.radians(10), 0.0),
            (math.radians(5), 0.0),
            (math.radians(10), 0.0),
        ]
        results = [gate.update(candidate) for candidate in candidates]
        self.assertTrue(all(not result.accepted for result in results))
        self.assertEqual(gate.last_valid, (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
