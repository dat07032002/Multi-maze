import json
from pathlib import Path
import tempfile
import unittest

from tag_adaptation.recording import AdaptationSession


class AdaptationSessionTests(unittest.TestCase):
    def test_finalized_session_has_hashes_and_never_publishes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / "champion.ckpt"
            checkpoint.write_bytes(b"champion")
            output = root / "session"
            with AdaptationSession(
                output,
                champion_checkpoint=checkpoint,
                mode="shadow",
            ) as session:
                session.write_step(
                    {
                        "episode_id": "one",
                        "base_action": [0.1, 0.2],
                        "executed_action": [0.1, 0.2],
                    }
                )
                session.write_episode(
                    {
                        "episode_id": "one",
                        "success": True,
                        "fall": False,
                    }
                )
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertTrue(manifest["completed"])
            self.assertFalse(manifest["publishes_commands"])
            self.assertEqual(manifest["counts"], {"steps": 1, "episodes": 1})
            self.assertTrue((output / "steps.jsonl").is_file())
            self.assertFalse((output / "steps.jsonl.partial").exists())

    def test_session_refuses_missing_checkpoint_and_existing_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(FileNotFoundError):
                AdaptationSession(
                    root / "session",
                    champion_checkpoint=root / "missing.ckpt",
                )
            checkpoint = root / "champion.ckpt"
            checkpoint.write_bytes(b"x")
            (root / "session").mkdir()
            with self.assertRaises(FileExistsError):
                AdaptationSession(
                    root / "session",
                    champion_checkpoint=checkpoint,
                )


if __name__ == "__main__":
    unittest.main()
