import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


DREAMER_PACKAGE = Path(__file__).resolve().parents[2] / "dreamerv3" / "dreamerv3"
sys.path.insert(0, str(DREAMER_PACKAGE))

from embodied.run.train import (  # noqa: E402
    _AgentWeights,
    _checkpoint_load_keys,
    _load_demonstrations,
)
from checkpoint_loading import is_optimizer_variable  # noqa: E402


class _FakeAgent:
    def __init__(self):
        self.loaded = None

    def save(self):
        return {"agent/weight": 1}

    def load_weights(self, state):
        self.loaded = state


class _FakeReplay:
    def __init__(self):
        self.rewards = []

    def add(self, transition, worker):
        del worker
        self.rewards.append(float(transition["reward"]))


class CheckpointLoadingTests(unittest.TestCase):
    def test_full_resume_restores_every_checkpoint_entry(self):
        self.assertIsNone(_checkpoint_load_keys("full"))

    def test_agent_only_adaptation_excludes_step_and_replay(self):
        self.assertEqual(_checkpoint_load_keys("agent_only"), ["agent"])

    def test_agent_only_adapter_uses_true_weights_loader(self):
        agent = _FakeAgent()
        adapter = _AgentWeights(agent)
        state = {"agent/weight": 2, "agent/model_opt/state": 3}
        adapter.load(state)
        self.assertIs(agent.loaded, state)
        self.assertEqual(adapter.save(), {"agent/weight": 1})

    def test_optimizer_variables_are_excluded_by_module_name(self):
        self.assertTrue(
            is_optimizer_variable("agent/wm/model_opt/state/0/mu")
        )
        self.assertTrue(
            is_optimizer_variable("agent/task_behavior/actor_opt/step")
        )
        self.assertTrue(
            is_optimizer_variable("agent/task_behavior/critic_opt/grad_scale")
        )
        self.assertFalse(
            is_optimizer_variable("agent/wm/encoder/kernel")
        )

    def test_uniform_chunk_sampling_spreads_old_replay_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(5):
                values = np.full((1024, 1), index, dtype=np.float32)
                np.savez_compressed(
                    root / f"chunk_{index}.npz",
                    image=values,
                    states=values,
                    goal=values,
                    action=values,
                    reward=values[:, 0],
                )
            replay = _FakeReplay()
            loaded = _load_demonstrations(
                replay,
                root,
                limit_steps=2048,
                sampling="uniform_chunks",
            )
            self.assertEqual(loaded, 2048)
            self.assertEqual(set(replay.rewards), {0.0, 4.0})

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            _checkpoint_load_keys("replay_only")


if __name__ == "__main__":
    unittest.main()
