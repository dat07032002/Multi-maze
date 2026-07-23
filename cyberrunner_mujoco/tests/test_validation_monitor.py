import tempfile
import unittest
from pathlib import Path

from cyberrunner_mujoco.validation_monitor import latest_metric_step, milestones


class ValidationMonitorTests(unittest.TestCase):
    def test_latest_metric_step_skips_partial_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            path.write_text(
                '{"step": 100}\nnot-json\n{"step": 250}\n{"other": 1}\n',
                encoding="utf-8",
            )
            self.assertEqual(latest_metric_step(path), 250)

    def test_milestones_include_baseline_once(self):
        self.assertEqual(
            milestones(500_000, 500_000, 1_500_000, True),
            [0, 500_000, 1_000_000, 1_500_000],
        )


if __name__ == "__main__":
    unittest.main()
