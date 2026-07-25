from __future__ import annotations

import unittest
from pathlib import Path

from tag_mujoco.maze_layout import DEFAULT_LAYOUT_PATH, load_layout
from tag_mujoco.system_config import DEFAULT_CAMERA_CALIBRATION
from tag_dreamer.tag_dreamer.path import LinearPath


ROOT = Path(__file__).resolve().parents[2]


class UpdatedTagReferenceTest(unittest.TestCase):
    def test_simulator_defaults_use_updated_tag_packages(self):
        self.assertIn("tag_dreamer", DEFAULT_LAYOUT_PATH.parts)
        self.assertIn("tag_state_estimation", DEFAULT_CAMERA_CALIBRATION.parts)
        self.assertTrue(DEFAULT_LAYOUT_PATH.is_file())
        self.assertTrue(DEFAULT_CAMERA_CALIBRATION.is_file())
        layout = load_layout()
        self.assertEqual(layout["board_width"], 0.259)
        self.assertEqual(layout["board_height"], 0.229)

    def test_renamed_tag_package_loads_preserved_routes(self):
        for name in ("path_custom.pkl", "path_0002_hard.pkl"):
            route = LinearPath.load(ROOT / "tag_dreamer" / "data" / name)
            self.assertIsInstance(route, LinearPath)
            self.assertGreater(route.points.shape[0], 0)


if __name__ == "__main__":
    unittest.main()
