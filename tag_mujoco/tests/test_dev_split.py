import collections
import json
import unittest
from pathlib import Path

from tag_mujoco.maze_dataset import load_split, validate_manifest

HERE = Path(__file__).resolve().parent
MANIFEST_V2 = HERE.parent / "maze_splits_v2.json"


class DevSplitTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST_V2.read_text(encoding="utf-8"))

    def test_dev_split_is_a_subset_of_train(self):
        self.assertIn("dev", self.manifest)
        self.assertTrue(set(self.manifest["dev"]).issubset(set(self.manifest["train"])))

    def test_dev_split_never_touches_held_out_layouts(self):
        dev = set(self.manifest["dev"])
        self.assertEqual(dev & set(self.manifest["validation"]), set())
        self.assertEqual(dev & set(self.manifest["test"]), set())

    def test_dev_split_matches_validation_band_composition(self):
        metadata = self.manifest["metadata"]

        def bands(split):
            return collections.Counter(
                metadata[relative]["difficulty_band"] for relative in self.manifest[split]
            )

        self.assertEqual(bands("dev"), bands("validation"))

    def test_dev_split_loads(self):
        split = load_split("dev", MANIFEST_V2)
        self.assertEqual(len(split.paths), len(self.manifest["dev"]))
        self.assertTrue(all(path.is_file() for path in split.paths))

    def test_manifest_without_dev_split_still_validates(self):
        without_dev = dict(self.manifest)
        without_dev.pop("dev")
        validate_manifest(without_dev, MANIFEST_V2)

    def test_legacy_manifest_reports_a_missing_dev_split(self):
        # The optional split must stay backward compatible with the v1 manifest.
        legacy = MANIFEST_V2.parent / "maze_splits.json"
        self.assertNotIn("dev", json.loads(legacy.read_text(encoding="utf-8")))
        with self.assertRaises(KeyError):
            load_split("dev", legacy, verify_hashes=False)

    def test_dev_split_outside_train_is_rejected(self):
        leaked = dict(self.manifest)
        leaked["dev"] = [self.manifest["validation"][0]]
        with self.assertRaises(ValueError):
            validate_manifest(leaked, MANIFEST_V2)


if __name__ == "__main__":
    unittest.main()
