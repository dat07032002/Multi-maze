import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


DREAMER_PACKAGE = Path(__file__).resolve().parents[2] / "dreamerv3" / "dreamerv3"
sys.path.insert(0, str(DREAMER_PACKAGE))

from embodied.run.train import (  # noqa: E402
    _AgentWeights,
    _aligned_driver_steps,
    _budget_alignment_warning,
    _checkpoint_load_keys,
    _load_demonstrations,
    _mixed_replay_dataset,
    _wait_at_validation_barrier,
)
from checkpoint_loading import (  # noqa: E402
    OptimizerHealthTracker,
    initialize_multihead_state,
    is_acting_variable,
    is_optimizer_variable,
    variable_sha256,
)


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

    def dataset(self):
        while True:
            yield {
                "reward": np.asarray([self.rewards[0]], np.float32),
                "is_first": np.asarray([False]),
            }


class CheckpointLoadingTests(unittest.TestCase):
    def test_driver_budget_is_small_aligned_and_exact_at_the_cap(self):
        self.assertEqual(_aligned_driver_steps(0, 50_000, 8), 96)
        self.assertEqual(_aligned_driver_steps(49_992, 50_000, 8), 8)
        self.assertEqual(_aligned_driver_steps(50_000, 50_000, 8), 0)

    def test_unaligned_vectorized_cap_warns_instead_of_refusing_to_train(self):
        """A sub-batch rounding error must not block a launch.

        Resuming under a different envs.amount is a documented workflow, and
        it routinely leaves a remainder. The run should say so and continue.
        """
        warning = _budget_alignment_warning(0, 7, 8)
        self.assertIsNotNone(warning)
        self.assertIn("remaining=7, env_count=8", warning)
        self.assertEqual(_aligned_driver_steps(0, 7, 8), 7)

    def test_training_is_polled_per_step_not_per_episode(self):
        """A step budget must buy optimizer updates, not just environment steps.

        should_train is a Ratio: the first call returns 1 and anchors its
        baseline, and later calls need batch_steps / train_ratio of step delta.
        Polling that on episode completion was fine while the loop ran
        driver(episodes=1). Once the loop collected fixed step chunks instead,
        a 50k run polled once, spent its single update inside the warmup
        schedule's zero learning rate, and exited 0 having learned nothing.
        """
        source = (DREAMER_PACKAGE / "embodied" / "run" / "train.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("driver.on_step(train_step)", source)
        self.assertNotIn("driver.on_episode(train_step)", source)

    def test_every_throttle_the_train_loop_defines_is_actually_used(self):
        """A defined-but-unconsulted throttle is the bug, not the safeguard.

        should_log and should_sync sat unused because train_step ran per
        episode, which throttled them implicitly. Moving it to per-step cadence
        made that latent: agent.report on every step cut throughput from about
        205 to 19 frames per second and wrote a 79 MB metrics.jsonl in half a
        50k run. Each throttle must be consulted, not merely constructed.
        """
        source = (DREAMER_PACKAGE / "embodied" / "run" / "train.py").read_text(
            encoding="utf-8"
        )
        for name in ("should_log", "should_sync", "should_save", "should_train"):
            self.assertIn(f"{name} = embodied.when.", source, f"{name} not defined")
            self.assertIn(f"{name}(", source.split(f"{name} = embodied.when.")[1],
                          f"{name} is defined but never called")

    def test_episode_counter_is_defined_before_the_callback_that_uses_it(self):
        """per_episode fires during prefill, before most of the loop is built."""
        source = (DREAMER_PACKAGE / "embodied" / "run" / "train.py").read_text(
            encoding="utf-8"
        )
        defined = source.index("episode = embodied.Counter()")
        used = source.index("episode.increment()")
        self.assertLess(defined, used)
        # And it must be the episode boundary that counts episodes, or the
        # checkpoint interval silently becomes a step interval.
        self.assertLess(used, source.index("driver.on_step(train_step)"))

    def test_ratio_yields_expected_updates_for_a_step_budget(self):
        """A 50k budget at train_ratio 8 must buy a few hundred updates.

        Two foundation runs finished this budget having made exactly one, which
        the warmup schedule spends at a zero learning rate. Coarse polling alone
        does not explain that -- polled once per 3000 step episode the same
        budget still yields 376 -- so this pins the expected magnitude rather
        than a mechanism, and a run that lands near one fails it.
        """
        from embodied.core.when import Ratio

        train_ratio, batch_steps, budget = 8, 1024, 50_000
        updates = sum(
            Ratio(train_ratio / batch_steps)(step) for step in [0]
        )  # first call always returns exactly 1 and anchors the baseline
        self.assertEqual(updates, 1)
        ratio = Ratio(train_ratio / batch_steps)
        self.assertGreater(sum(ratio(step) for step in range(budget)), 300)

    def test_ratio_returns_nothing_while_the_step_counter_is_static(self):
        """The failure mode that does explain a single update.

        Ratio measures step delta, so any polling that happens while the step
        counter is not advancing contributes nothing at all, however often it
        runs. Polling every step rather than once per episode is what keeps the
        poll and the counter in lockstep.
        """
        from embodied.core.when import Ratio

        ratio = Ratio(8 / 1024)
        self.assertEqual(ratio(47_984), 1)
        self.assertEqual([ratio(47_984) for _ in range(15)], [0] * 15)

    def test_aligned_budget_produces_no_warning(self):
        self.assertIsNone(_budget_alignment_warning(0, 50_000, 8))
        self.assertIsNone(_budget_alignment_warning(50_000, 50_000, 8))

    def test_driver_budget_never_exceeds_one_batch_of_overshoot(self):
        # The last chunk is the only unaligned one, so the cap can be passed
        # by at most env_count - 1 steps.
        step, target, env_count = 0, 1_003, 8
        while step < target:
            step += max(_aligned_driver_steps(step, target, env_count), env_count)
        self.assertLess(step - target, env_count)

    def test_legacy_actor_is_copied_into_every_multihead_actor(self):
        source = {
            "agent/wm/value": np.asarray([1.0], np.float32),
            "agent/task_behavior/ac/actor/h0/kernel": np.asarray([2.0], np.float32),
        }
        current = {
            "agent/wm/value": np.asarray([0.0], np.float32),
            "agent/task_behavior/ac/actor_stabilize/h0/kernel": np.asarray([0.0], np.float32),
            "agent/task_behavior/ac/actor_straight/h0/kernel": np.asarray([0.0], np.float32),
            "agent/task_behavior/ac/actor_opt/step": np.asarray(0, np.int32),
        }
        restored = initialize_multihead_state(
            current, source, ("stabilize", "straight")
        )
        self.assertEqual(float(restored["agent/wm/value"].item()), 1.0)
        self.assertEqual(
            float(restored["agent/task_behavior/ac/actor_stabilize/h0/kernel"].item()),
            2.0,
        )
        self.assertEqual(
            float(restored["agent/task_behavior/ac/actor_straight/h0/kernel"].item()),
            2.0,
        )
        self.assertEqual(
            int(restored["agent/task_behavior/ac/actor_opt/step"].item()), 0
        )

    def test_validation_barrier_saves_and_observes_preexisting_release(self):
        class _Checkpoint:
            saved = 0

            def save(self):
                self.saved += 1

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            barrier = root / "validation/barriers"
            barrier.mkdir(parents=True)
            (barrier / "step_000025000.release.json").write_text("{}\n")
            checkpoint = _Checkpoint()
            passed = _wait_at_validation_barrier(
                root, 25_000, checkpoint, root / "STOP_TRAINING", 0.001
            )
            self.assertTrue(passed)
            self.assertEqual(checkpoint.saved, 1)
            self.assertTrue(
                (barrier / "step_000025000.request.json").is_file()
            )

    def test_fixed_retention_replay_fraction_does_not_dilute(self):
        online = _FakeReplay()
        retention = _FakeReplay()
        online.rewards.append(0.0)
        retention.rewards.append(1.0)
        dataset = _mixed_replay_dataset(online, retention, 0.25, seed=7)
        samples = np.asarray(
            [next(dataset)["is_retention"].item() for _ in range(20_000)]
        )
        self.assertAlmostEqual(float(samples.mean()), 0.25, delta=0.01)

    def test_full_resume_restores_every_checkpoint_entry(self):
        self.assertIsNone(_checkpoint_load_keys("full"))

    def test_agent_only_adaptation_excludes_step_and_replay(self):
        self.assertEqual(_checkpoint_load_keys("agent_only"), ["agent"])

    def test_multihead_initialization_loads_only_agent_state(self):
        self.assertEqual(_checkpoint_load_keys("multihead_init"), ["agent"])

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

    def test_acting_digest_excludes_optimizer_and_critic_state(self):
        state = {
            "agent/wm/encoder/kernel": np.asarray([1.0], np.float32),
            "agent/task_behavior/ac/actor/kernel": np.asarray([2.0], np.float32),
            "agent/task_behavior/critic/slow/kernel": np.asarray([3.0], np.float32),
            "agent/wm/model_opt/step": np.asarray(4, np.int32),
        }
        digest, count = variable_sha256(state, is_acting_variable)
        changed = dict(state)
        changed["agent/task_behavior/critic/slow/kernel"] = np.asarray(
            [99.0], np.float32
        )
        changed_digest, changed_count = variable_sha256(
            changed, is_acting_variable
        )
        self.assertEqual(count, 2)
        self.assertEqual(changed_count, 2)
        self.assertEqual(digest, changed_digest)

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

    def test_nonfinite_demonstration_chunk_is_quarantined_and_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = np.ones((4, 1), dtype=np.float32)
            bad = good.copy()
            bad[2, 0] = np.nan
            for name, action in (("good.npz", good), ("bad.npz", bad)):
                np.savez_compressed(
                    root / name,
                    image=good,
                    states=good,
                    goal=good,
                    action=action,
                    reward=good[:, 0],
                )
            replay = _FakeReplay()
            report_path = root / "report.json"
            loaded = _load_demonstrations(
                replay,
                root,
                sampling="chronological",
                report_path=report_path,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, 4)
            self.assertEqual(replay.rewards, [1.0] * 4)
            self.assertEqual(report["accepted_files"], 1)
            self.assertEqual(report["rejected_files"], 1)
            self.assertIn("action", report["rejections"][0]["nonfinite_fields"])

    def test_partial_chunk_ignores_uninitialized_storage_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = np.ones((4, 1), dtype=np.float32)
            action = good.copy()
            action[2:, 0] = np.nan
            filename = (
                "20260101T000000F000001-part-"
                "0000000000000000000000-2.npz"
            )
            np.savez_compressed(
                root / filename,
                image=good,
                states=good,
                goal=good,
                action=action,
                reward=good[:, 0],
            )
            replay = _FakeReplay()
            loaded = _load_demonstrations(replay, root)
            self.assertEqual(loaded, 2)
            self.assertEqual(replay.rewards, [1.0, 1.0])

    def test_optimizer_health_rejects_nonfinite_and_stalled_updates(self):
        tracker = OptimizerHealthTracker(stall_limit=3)
        tracker.check({"model_opt_grad_steps": 1, "model_opt_loss": 2.0})
        tracker.check({"model_opt_grad_steps": 1, "model_opt_loss": 2.0})
        tracker.check({"model_opt_grad_steps": 1, "model_opt_loss": 2.0})
        with self.assertRaisesRegex(RuntimeError, "did not advance"):
            tracker.check({"model_opt_grad_steps": 1, "model_opt_loss": 2.0})
        with self.assertRaisesRegex(FloatingPointError, "non-finite"):
            OptimizerHealthTracker().check({"actor_opt_loss": np.nan})
        with self.assertRaisesRegex(FloatingPointError, "gradient overflow"):
            OptimizerHealthTracker().check({"actor_opt_grad_overflow": 1.0})


if __name__ == "__main__":
    unittest.main()
