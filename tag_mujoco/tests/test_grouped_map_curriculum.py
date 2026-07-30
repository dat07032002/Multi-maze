import json
import tempfile
import unittest
from pathlib import Path

from tag_mujoco.grouped_map_curriculum import build_group_manifests
from tag_mujoco.maze_dataset import load_manifest


class GroupedMapCurriculumTests(unittest.TestCase):
    def test_groups_are_nested_easy_first_and_direction_balanced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            train = []
            metadata = {}
            for index in range(20):
                name = f"maze_{index:03d}.json"
                direction = (1, 0) if index % 2 == 0 else (0, -1)
                layout = {
                    "solution_cells": [
                        [0, 5],
                        [direction[0], 5 + direction[1]],
                    ]
                }
                (root / name).write_text(json.dumps(layout), encoding="utf-8")
                metadata[name] = {
                    "seed": index,
                    "difficulty_score": index / 19,
                    "difficulty_band": "easy",
                }
                if index < 16:
                    train.append(name)
            source = {
                "schema_version": 2,
                "dataset_id": "source",
                "smoke": train[:2],
                "train": train,
                "dev": train[:4],
                "validation": ["maze_016.json", "maze_017.json"],
                "test": ["maze_018.json", "maze_019.json"],
                "metadata": metadata,
            }
            source_path = root / "maze_splits.json"
            source_path.write_text(json.dumps(source), encoding="utf-8")

            outputs = build_group_manifests(
                source_path, group_sizes=(4, 8, 16)
            )
            groups = {
                size: load_manifest(path)
                for size, path in outputs.items()
            }

            self.assertEqual(set(groups[4]["train"]), set(groups[8]["train"][:4]))
            self.assertEqual(set(groups[8]["train"]), set(groups[16]["train"][:8]))
            for size, manifest in groups.items():
                self.assertEqual(len(manifest["train"]), size)
                moves = []
                for relative in manifest["train"]:
                    layout = json.loads((root / relative).read_text())
                    first, second = layout["solution_cells"][:2]
                    moves.append((second[0] - first[0], second[1] - first[1]))
                self.assertEqual(moves.count((1, 0)), size // 2)
                self.assertEqual(moves.count((0, -1)), size // 2)


if __name__ == "__main__":
    unittest.main()
