import sys
import unittest
from pathlib import Path


DREAMER_PACKAGE = Path(__file__).resolve().parents[2] / "dreamerv3" / "dreamerv3"
sys.path.insert(0, str(DREAMER_PACKAGE))

from embodied.run.train import _checkpoint_load_keys  # noqa: E402


class CheckpointLoadingTests(unittest.TestCase):
    def test_full_resume_restores_every_checkpoint_entry(self):
        self.assertIsNone(_checkpoint_load_keys("full"))

    def test_agent_only_adaptation_excludes_step_and_replay(self):
        self.assertEqual(_checkpoint_load_keys("agent_only"), ["agent"])

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            _checkpoint_load_keys("replay_only")


if __name__ == "__main__":
    unittest.main()
