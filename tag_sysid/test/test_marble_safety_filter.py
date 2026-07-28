import unittest

from tag_sysid.marble_safety import ConfirmedDisplacementGuard


class ConfirmedDisplacementGuardTest(unittest.TestCase):
    def test_one_frame_spike_does_not_trip(self):
        guard = ConfirmedDisplacementGuard(0.003, 5, 3)
        guard.reset(0.0, 0.0)
        results = [guard.update(x, 0.0) for x in (0.0, 0.0, 0.010, 0.0, 0.0)]
        self.assertFalse(any(results))
        self.assertEqual(guard.consecutive, 0)

    def test_sustained_displacement_trips_after_confirmation(self):
        guard = ConfirmedDisplacementGuard(0.003, 5, 3)
        guard.reset(0.0, 0.0)
        results = [guard.update(0.005, 0.0) for _ in range(7)]
        self.assertEqual(results[:6], [False, False, False, False, False, True])
        self.assertAlmostEqual(guard.filtered_distance_m, 0.005)

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            ConfirmedDisplacementGuard(0.003, 4, 3)
        with self.assertRaises(ValueError):
            ConfirmedDisplacementGuard(0.0, 5, 3)


if __name__ == "__main__":
    unittest.main()
