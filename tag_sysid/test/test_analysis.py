import unittest

import numpy as np

from tag_sysid.analysis import fit_command_to_angle, timing_summary


class AnalysisTest(unittest.TestCase):
    def test_timing_summary(self):
        summary = timing_summary([0, 20_000_000, 40_000_000, 60_000_000])
        self.assertAlmostEqual(summary["rate_hz"], 50.0)
        self.assertAlmostEqual(summary["period_ms_median"], 20.0)

    def test_command_angle_fit_recovers_map_and_lag(self):
        command_times = np.arange(0, 4_000_000_000, 20_000_000, dtype=np.int64)
        phase = np.arange(command_times.size, dtype=np.float64)
        commands = np.column_stack((80.0 * np.sin(phase / 9), 60.0 * np.cos(phase / 13)))
        state_times = command_times.copy()
        lag_ns = 60_000_000
        indices = np.searchsorted(command_times, state_times - lag_ns, side="right") - 1
        indices = np.maximum(indices, 0)
        mapping = np.asarray(((0.0007, 0.0001), (-0.0002, 0.0008)))
        offset = np.asarray((0.01, -0.02))
        angles = offset + commands[indices] @ mapping.T
        fit = fit_command_to_angle(command_times, commands, state_times, angles)
        self.assertIsNotNone(fit)
        self.assertLessEqual(abs(fit["lag_seconds"] - 0.06), 0.02)
        self.assertAlmostEqual(fit["lag_resolution_seconds"], 0.02, places=3)
        np.testing.assert_allclose(fit["angle_rad_per_command"], mapping, atol=1e-8)


if __name__ == "__main__":
    unittest.main()
