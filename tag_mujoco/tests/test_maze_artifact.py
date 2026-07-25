from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cyberrunner_mujoco.maze_artifact import PrintConfig, export_maze_artifact


class MazeArtifactTest(unittest.TestCase):
    def setUp(self):
        self.layout = (
            Path(__file__).resolve().parents[1]
            / "generated_mazes"
            / "maze_seed_10000.json"
        )

    def test_export_is_versioned_and_prototype_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = export_maze_artifact(
                self.layout, Path(temporary), PrintConfig(floor_strip_height_m=0.004)
            )
            expected = {
                "layout.json", "route.json", "model.xml", "preview.png",
                "maze_prototype.stl", "metadata.json",
            }
            self.assertEqual({path.name for path in destination.iterdir()}, expected)
            metadata = json.loads((destination / "metadata.json").read_text())
            self.assertEqual(metadata["print_validation"]["print_status"], "prototype_only")
            self.assertFalse(metadata["print_validation"]["mounting_interface_confirmed"])
            self.assertTrue((destination / "maze_prototype.stl").read_text().startswith("solid "))

    def test_final_fit_is_blocked_without_mount_measurement(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(RuntimeError):
                export_maze_artifact(
                    self.layout,
                    Path(temporary),
                    request_final_fit=True,
                )


if __name__ == "__main__":
    unittest.main()
