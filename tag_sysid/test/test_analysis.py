import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from tag_sysid.analysis import fit_command_to_angle, timing_summary
from tag_sysid.analyze import analyze_session


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

    def test_analyzes_active_csv_schema(self):
        with TemporaryDirectory() as directory:
            session = Path(directory)
            (session / "commands.csv").write_text(
                "monotonic_ns,command_1,command_2\n"
                "0,0,0\n20000000,0,5\n40000000,0,10\n",
                encoding="utf-8",
            )
            (session / "board_angles.csv").write_text(
                "monotonic_ns,x_b_m,y_b_m,x_b_dot_mps,y_b_dot_mps,"
                "alpha_rad,beta_rad,ball_visible\n"
                "0,nan,nan,nan,nan,0.01,0.00,0\n"
                "20000000,nan,nan,nan,nan,0.01,-0.01,0\n"
                "40000000,nan,nan,nan,nan,0.01,-0.02,0\n",
                encoding="utf-8",
            )
            result = analyze_session(session)

        self.assertEqual(result["session_kind"], "active")
        self.assertIn("command_2", result["observed_command_ranges"])
        self.assertIn("active_command_angle_fit", result)


if __name__ == "__main__":
    unittest.main()
