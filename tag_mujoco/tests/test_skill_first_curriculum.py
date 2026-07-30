from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from tag_mujoco.maze_dataset import load_manifest, load_split
from tag_mujoco.rehearsal_pack import build_rehearsal_pack
from tag_mujoco.sequential_map_curriculum import build_sequential_manifests
from tag_mujoco.sequential_map_gate import evaluate_map_gate
from tag_mujoco.skill_course_generator import (
    SKILL_FAMILIES,
    build_skill_dataset,
)
from tag_mujoco.skill_curriculum_gate import evaluate_skill_gate
from tag_mujoco.tag_env import TagMazeTask, TaskConfig


def _evaluation(completion=0.95, falls=0.02, progress=0.97, episodes=20):
    return {
        "summary": {
            "episodes": episodes,
            "completion_rate": completion,
            "fall_rate": falls,
            "mean_max_route_completion": progress,
        }
    }


def _replay_file(path: Path, length: int, value: float = 0.0) -> None:
    np.savez_compressed(
        path,
        image=np.zeros((length, 64, 64, 1), dtype=np.uint8),
        states=np.full((length, 4), value, dtype=np.float32),
        goal=np.zeros((length, 10), dtype=np.float32),
        action=np.zeros((length, 2), dtype=np.float32),
        reward=np.zeros(length, dtype=np.float32),
        is_first=np.zeros(length, dtype=bool),
        is_last=np.zeros(length, dtype=bool),
        is_terminal=np.zeros(length, dtype=bool),
    )


class SkillFirstCurriculumTests(unittest.TestCase):
    def test_skill_datasets_are_disjoint_safe_and_label_free_at_policy_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_skill_dataset(
                Path(temporary), train_count=2, validation_count=1, test_count=1
            )
            self.assertEqual(set(outputs), set(SKILL_FAMILIES))
            for family, path in outputs.items():
                manifest = load_manifest(path)
                self.assertEqual(manifest["skill_family"], family)
                self.assertEqual(len(manifest["train"]), 2)
                self.assertFalse(set(manifest["train"]) & set(manifest["validation"]))
                for metadata in manifest["metadata"].values():
                    self.assertEqual(metadata["skill_family"], family)
                    self.assertFalse(metadata["policy_observation_contains_labels"])
                    self.assertIn("reset_conditions", metadata)

    def test_conditioned_reset_uses_manifest_metadata_without_new_observation_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_skill_dataset(
                Path(temporary), train_count=1, validation_count=1, test_count=1
            )
            task = TagMazeTask(
                task_config=TaskConfig(
                    maze_manifest=str(outputs["recovery"]),
                    maze_split="train",
                    conditioned_resets=True,
                )
            )
            observation, info = task.reset(options={"layout_index": 0})
            self.assertAlmostEqual(info["start_progress_fraction"], 0.20)
            self.assertEqual(
                set(task.policy_contract.observation_keys),
                {"image", "states", "goal"},
            )
            self.assertNotIn("skill_family", observation)
            self.assertNotIn("condition_id", observation)

    def test_explicit_evaluation_layout_preserves_condition_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            outputs = build_skill_dataset(
                Path(temporary), train_count=1, validation_count=1, test_count=1
            )
            manifest = load_manifest(outputs["recovery"])
            relative = manifest["validation"][0]
            metadata = manifest["metadata"][relative]
            task = TagMazeTask(
                layout_paths=[str(outputs["recovery"].parent / relative)],
                layout_metadata=[metadata],
                task_config=TaskConfig(conditioned_resets=True),
            )
            _, info = task.reset(options={"layout_index": 0})
            self.assertEqual(info["reset_conditions"], metadata["reset_conditions"])

    def test_sequential_manifests_have_exactly_one_online_map(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = build_skill_dataset(
                root / "skills", train_count=3, validation_count=1, test_count=1
            )["straight"]
            outputs = build_sequential_manifests(skill, root / "maps")
            self.assertEqual(len(outputs), 3)
            previous_seen = set()
            for index, path in enumerate(outputs, start=1):
                manifest = load_manifest(path)
                self.assertEqual(manifest["online_map_count"], 1)
                self.assertEqual(len(manifest["train"]), 1)
                self.assertEqual(manifest["train"], manifest["dev"])
                self.assertEqual(set(manifest.get("rehearsal", ())), previous_seen)
                previous_seen.add(manifest["train"][0])
                self.assertEqual(set(manifest["seen"]), previous_seen)
                self.assertEqual(manifest["sequential_stage"], index)
            self.assertEqual(len(load_split("seen", outputs[-1]).paths), 3)
            self.assertEqual(len(load_split("rehearsal", outputs[-1]).paths), 2)

    def test_rehearsal_pack_balances_labeled_finite_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = {}
            for label, value in (("skills", 1.0), ("maps", 2.0)):
                source = root / label
                source.mkdir()
                _replay_file(source / "episode_000.npz", 7, value)
                _replay_file(source / "episode_001.npz", 7, value)
                sources[label] = source
            report = build_rehearsal_pack(
                sources, root / "pack", steps_per_source=10, seed=9
            )
            self.assertGreaterEqual(report["sources"]["skills"]["selected_steps"], 10)
            self.assertGreaterEqual(report["sources"]["maps"]["selected_steps"], 10)
            self.assertTrue((root / "pack" / "rehearsal_manifest.json").is_file())

    def test_rehearsal_pack_can_exclude_files_after_checkpoint_cutoff(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            old = source / "old-4.npz"
            new = source / "new-4.npz"
            _replay_file(old, 4)
            _replay_file(new, 4)
            old.touch()
            cutoff = old.stat().st_mtime
            new.touch()
            new_mtime = cutoff + 10.0
            import os
            os.utime(new, (new_mtime, new_mtime))
            report = build_rehearsal_pack(
                {"accepted": source},
                root / "pack",
                steps_per_source=4,
                before_mtimes={"accepted": cutoff},
            )
            selected = report["sources"]["accepted"]["selected_files"]
            self.assertEqual([Path(item["source"]).name for item in selected], [old.name])

    def test_skill_and_map_gates_require_mastery_and_retention(self):
        reports = {family: _evaluation() for family in SKILL_FAMILIES}
        skill_gate = evaluate_skill_gate(reports)
        self.assertTrue(skill_gate["passed"])
        failed = dict(reports)
        failed["hazard"] = _evaluation(completion=0.85)
        self.assertFalse(evaluate_skill_gate(failed)["passed"])

        map_gate = evaluate_map_gate(
            _evaluation(completion=0.90, falls=0.10, progress=0.95),
            skill_gate=skill_gate,
            retention_baseline=_evaluation(completion=0.95, progress=0.97),
            retention_candidate=_evaluation(completion=0.91, progress=0.95),
        )
        self.assertTrue(map_gate["passed"])
        regressed = evaluate_map_gate(
            _evaluation(),
            skill_gate=skill_gate,
            retention_baseline=_evaluation(completion=0.95, progress=0.97),
            retention_candidate=_evaluation(completion=0.89, progress=0.94),
        )
        self.assertFalse(regressed["passed"])


if __name__ == "__main__":
    unittest.main()
