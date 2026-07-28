import argparse
import tempfile
import unittest
from pathlib import Path

from tag_mujoco.validation_monitor import (
    evaluator_command,
    latest_metric_step,
    milestones,
    requires_new_checkpoint,
)


def _args(**overrides):
    values = dict(
        python=Path("/python"),
        repo_root=Path("/repo"),
        run_dir=Path("/run"),
        manifest=Path("/manifest.json"),
        split="validation",
        policy_mode="sample",
        canonical_episodes_per_maze=1,
        robust_episodes_per_maze=3,
        max_steps=3000,
        seed=20260723,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


def _flag(command, name):
    return command[command.index(name) + 1]


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

    def test_default_canonical_command_keeps_the_historical_protocol(self):
        command = evaluator_command(
            _args(), Path("/snap.ckpt"), Path("/milestone"), 500_000, "canonical"
        )
        self.assertEqual(_flag(command, "--split"), "validation")
        self.assertEqual(_flag(command, "--policy-mode"), "sample")
        self.assertEqual(_flag(command, "--episodes-per-maze"), "1")

    def test_dev_split_and_mode_policy_reach_the_evaluator(self):
        command = evaluator_command(
            _args(split="dev", policy_mode="mode", canonical_episodes_per_maze=3),
            Path("/snap.ckpt"),
            Path("/milestone"),
            500_000,
            "canonical",
        )
        self.assertEqual(_flag(command, "--split"), "dev")
        self.assertEqual(_flag(command, "--policy-mode"), "mode")
        self.assertEqual(_flag(command, "--episodes-per-maze"), "3")

    def test_robust_mode_uses_its_own_episode_count(self):
        command = evaluator_command(
            _args(canonical_episodes_per_maze=1, robust_episodes_per_maze=3),
            Path("/snap.ckpt"),
            Path("/milestone"),
            500_000,
            "robust",
        )
        self.assertEqual(_flag(command, "--episodes-per-maze"), "3")


if __name__ == "__main__":
    unittest.main()
