import tempfile
import unittest
from pathlib import Path

from tag_mujoco.validation_monitor import (
    latest_metric_step,
    milestones,
    requires_new_checkpoint,
)


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

    def test_only_intermediate_milestones_require_a_new_checkpoint(self):
        self.assertFalse(requires_new_checkpoint(0, 1_500_000))
        self.assertTrue(requires_new_checkpoint(500_000, 1_500_000))
        self.assertFalse(requires_new_checkpoint(1_500_000, 1_500_000))


if __name__ == "__main__":
    unittest.main()
