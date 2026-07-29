import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


DREAMER_PACKAGE = Path(__file__).resolve().parents[2] / "dreamerv3" / "dreamerv3"
sys.path.insert(0, str(DREAMER_PACKAGE))

import embodied  # noqa: E402
from embodied.replay import saver as saverlib  # noqa: E402


class FiniteTrainingDataTests(unittest.TestCase):
    def test_reports_exact_nonfinite_field_and_index(self):
        values = {
            "states": np.asarray([[0.0, np.nan], [np.inf, 1.0]], np.float32),
            "is_first": np.asarray([True, False]),
        }
        failures = embodied.nonfinite_fields(values)
        self.assertEqual(failures["states"]["count"], 2)
        self.assertEqual(failures["states"]["first_index"], (0, 1))
        self.assertNotIn("is_first", failures)

    def test_rejects_nonfinite_transition_with_context(self):
        with self.assertRaisesRegex(
            embodied.NonFiniteDataError,
            r"worker 7.*action: count=1 first_index=\(1,\)",
        ):
            embodied.assert_finite(
                {"action": np.asarray([0.0, np.nan], np.float32)},
                "replay transition from worker 7",
            )

    def test_accepts_finite_numeric_and_non_numeric_values(self):
        embodied.assert_finite(
            {
                "reward": np.asarray(1.0, np.float32),
                "image": np.zeros((2, 2, 3), np.uint8),
                "label": "safe",
            },
            "finite fixture",
        )

    def test_saved_replay_loader_quarantines_whole_bad_chunk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = np.asarray([0.0, 1.0], np.float32)
            bad = np.asarray([0.0, np.nan], np.float32)
            suffix = "-0000000000000000000000-2.npz"
            np.savez_compressed(
                root / ("20260101T000000F000001-good" + suffix), reward=good
            )
            np.savez_compressed(
                root / ("20260101T000000F000002-bad0" + suffix), reward=bad
            )
            np.savez_compressed(
                root
                / "20260101T000000F000003-tail-0000000000000000000000-1.npz",
                reward=np.asarray([5.0, np.nan], np.float32),
            )
            replay_saver = saverlib.Saver(root)
            loaded = list(replay_saver.load(capacity=None, length=1))
            self.assertEqual(len(loaded), 3)
            self.assertTrue(
                all(
                    float(step["reward"]) in (0.0, 1.0, 5.0)
                    for step, _ in loaded
                )
            )
            self.assertEqual(replay_saver.load_report["accepted_chunks"], 2)
            self.assertEqual(replay_saver.load_report["rejected_chunks"], 1)
            self.assertTrue((root / "replay_load_report.json").is_file())


if __name__ == "__main__":
    unittest.main()
