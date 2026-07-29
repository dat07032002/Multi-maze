import json
import re
from pathlib import Path

import embodied
import numpy as np


class _AgentWeights:
    """Checkpoint adapter that deliberately excludes optimizer state."""

    def __init__(self, agent):
        self.agent = agent

    def save(self):
        return self.agent.save()

    def load(self, state):
        self.agent.load_weights(state)


def _load_demonstrations(
    replay,
    directory,
    limit_steps=0,
    sampling="chronological",
    report_path=None,
):
    """Load complete expert episodes without joining streams across files."""

    if not directory:
        return 0
    root = Path(str(directory)).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Demonstration directory does not exist: {root}")
    filenames = sorted(root.rglob("*.npz"))
    if sampling == "uniform_chunks" and limit_steps and filenames:
        # Replay chunks contain 1024 contiguous transitions by default. Spread
        # the retained subset across the source run instead of taking only its
        # earliest experience.
        chunk_count = min(
            len(filenames), max(1, int(np.ceil(int(limit_steps) / 1024)))
        )
        indices = np.linspace(0, len(filenames) - 1, chunk_count, dtype=int)
        filenames = [filenames[index] for index in np.unique(indices)]
    elif sampling != "chronological":
        raise ValueError(
            f"Unknown demonstration sampling mode: {sampling!r}"
        )

    loaded = 0
    accepted_files = 0
    rejected = []
    for episode_index, filename in enumerate(filenames):
        with np.load(filename, allow_pickle=False) as episode:
            keys = tuple(episode.files)
            if not {"image", "states", "goal", "action", "reward"}.issubset(keys):
                raise ValueError(f"Incomplete demonstration episode: {filename}")
            lengths = {len(episode[key]) for key in keys}
            if len(lengths) != 1:
                raise ValueError(f"Mismatched demonstration arrays: {filename}")
            arrays = {key: episode[key] for key in keys}
            failures = embodied.nonfinite_fields(arrays)
            if failures:
                rejected.append(
                    {
                        "filename": str(filename),
                        "nonfinite_fields": failures,
                    }
                )
                print(
                    f"Skipping non-finite demonstration chunk {filename}: "
                    f"{failures}"
                )
                continue
            accepted_files += 1
            for index in range(lengths.pop()):
                replay.add(
                    {key: arrays[key][index] for key in keys},
                    worker=1_000_000 + episode_index,
                )
                loaded += 1
                if limit_steps and loaded >= int(limit_steps):
                    break
        if limit_steps and loaded >= int(limit_steps):
            break
    report = {
        "source": str(root),
        "sampling": sampling,
        "limit_steps": int(limit_steps),
        "selected_files": len(filenames),
        "accepted_files": accepted_files,
        "rejected_files": len(rejected),
        "loaded_steps": loaded,
        "rejections": rejected,
    }
    if report_path:
        destination = Path(str(report_path))
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
    if rejected:
        print(
            f"Quarantined {len(rejected)} of {len(filenames)} selected "
            "demonstration chunks."
        )
    print(f"Loaded {loaded} expert demonstration steps from {root}.")
    return loaded


def _checkpoint_load_keys(mode):
    """Select state restored from an external checkpoint."""

    if mode == "full":
        return None
    if mode == "agent_only":
        return ["agent"]
    raise ValueError(
        f"Unknown checkpoint load mode {mode!r}; expected 'full' or 'agent_only'."
    )


def _write_training_health(path, report):
    destination = Path(str(path))
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def train(agent, env, replay, logger, args):

    logdir = embodied.Path(args.logdir)
    logdir.mkdirs()
    print("Logdir", logdir)
    should_expl = embodied.when.Until(args.expl_until)
    should_train = embodied.when.Ratio(args.train_ratio / args.batch_steps)
    should_log = embodied.when.Clock(args.log_every)
    should_save = embodied.when.Every(args.save_every, initial=False)
    should_sync = embodied.when.Every(args.sync_every)
    step = logger.step
    updates = embodied.Counter()
    metrics = embodied.Metrics()
    print("Observation space:", embodied.format(env.obs_space), sep="\n")
    print("Action space:", embodied.format(env.act_space), sep="\n")

    timer = embodied.Timer()
    timer.wrap("agent", agent, ["policy", "train", "report", "save"])
    timer.wrap("env", env, ["step"])
    timer.wrap("replay", replay, ["add", "save"])
    timer.wrap("logger", logger, ["write"])

    nonzeros = set()

    def per_episode(ep):
        length = len(ep["reward"]) - 1
        score = float(ep["reward"].astype(np.float64).sum())
        sum_abs_reward = float(np.abs(ep["reward"]).astype(np.float64).sum())
        logger.add(
            {
                "length": length,
                "score": score,
                "sum_abs_reward": sum_abs_reward,
                "reward_rate": (np.abs(ep["reward"]) >= 0.5).mean(),
            },
            prefix="episode",
        )
        print(f"Episode has {length} steps and return {score:.1f}.")
        stats = {}
        for key in args.log_keys_video:
            if key in ep:
                stats[f"policy_{key}"] = ep[key]
        for key, value in ep.items():
            if not args.log_zeros and key not in nonzeros and (value == 0).all():
                continue
            nonzeros.add(key)
            if re.match(args.log_keys_sum, key):
                stats[f"sum_{key}"] = ep[key].sum()
            if re.match(args.log_keys_mean, key):
                stats[f"mean_{key}"] = ep[key].mean()
            if re.match(args.log_keys_max, key):
                stats[f"max_{key}"] = ep[key].max(0).mean()
        metrics.add(stats, prefix="stats")

    driver = embodied.Driver(env)
    driver.on_episode(lambda ep, worker: per_episode(ep))
    driver.on_step(
        lambda transition, worker: embodied.assert_finite(
            transition, f"environment transition from worker {worker}"
        )
    )

    def add_replay(ep, worker):
        for i in range(len(ep["reward"])):
            trn = {k: v[i] for k, v in ep.items() if not k.startswith("log_")}
            replay.add(trn, worker)

    driver.on_episode(add_replay)

    checkpoint = embodied.Checkpoint(logdir / "checkpoint.ckpt")
    timer.wrap("checkpoint", checkpoint, ["save", "load"])
    checkpoint.step = step
    checkpoint.agent = agent
    checkpoint.replay = replay
    loaded_agent = False
    if args.from_checkpoint:
        load_keys = _checkpoint_load_keys(args.from_checkpoint_mode)
        if load_keys == ["agent"]:
            external = embodied.Checkpoint()
            external.agent = _AgentWeights(agent)
            external.load(args.from_checkpoint, keys=["agent"])
            loaded_agent = True
            print(
                "Loaded learned agent variables only; optimizer state, step "
                "counter, and replay remain fresh."
            )
        else:
            checkpoint.load(args.from_checkpoint)
            loaded_agent = True
    checkpoint.load_or_save()
    health_path = Path(str(logdir)) / "training_health.json"
    health_report = {
        "schema_version": 1,
        "status": "awaiting_first_update",
    }
    if hasattr(agent, "acting_weights_digest"):
        digest, count = agent.acting_weights_digest()
        health_report.update(
            {
                "initial_acting_weights_sha256": digest,
                "acting_variable_count": count,
            }
        )
    _write_training_health(health_path, health_report)

    def record_failure(error, phase):
        health_report.update(
            {
                "status": "failed",
                "failure_phase": phase,
                "failure_type": type(error).__name__,
                "failure": str(error),
            }
        )
        _write_training_health(health_path, health_report)

    def checked_policy(mode):
        def policy(*policy_args):
            try:
                return agent.policy(*policy_args, mode=mode)
            except Exception as error:
                record_failure(error, f"policy_{mode}")
                raise

        return policy

    _load_demonstrations(
        replay,
        args.demo_dir,
        args.demo_limit_steps,
        args.demo_sampling,
        report_path=Path(str(logdir)) / "replay_import_report.json",
    )
    print("Prefill train dataset.")
    if loaded_agent:
        print("Prefill uses the loaded checkpoint policy.")
        prefill_policy = checked_policy("train")
    else:
        print("Prefill uses a random policy because no checkpoint was loaded.")
        prefill_policy = embodied.RandomAgent(env.act_space).policy
    if args.count_prefill_steps:
        driver.on_step(lambda tran, _: step.increment())
    while len(replay) < max(args.batch_steps, args.train_fill):
        driver(prefill_policy, steps=100)
    if not args.count_prefill_steps:
        driver.on_step(lambda tran, _: step.increment())
    logger.add(metrics.result())
    logger.write()

    dataset = agent.dataset(replay.dataset)
    state = [None]  # To be writable from train step function below.
    batch = [None]
    episode = embodied.Counter()
    first_update_verified = [False]

    def train_step(ep, worker):
        for _ in range(should_train(step)):
            try:
                with timer.scope("dataset"):
                    batch[0] = next(dataset)
                outs, state[0], mets = agent.train(batch[0], state[0])
            except Exception as error:
                record_failure(error, "training_update")
                raise
            grad_steps = [
                int(np.asarray(value))
                for key, value in mets.items()
                if key.endswith("_grad_steps")
            ]
            # Warmup schedules intentionally apply a zero learning rate on the
            # first optimizer call. Verify mutation once every optimizer has
            # reached step 2, where the schedule must be nonzero.
            ready_for_hash_check = grad_steps and min(grad_steps) >= 2
            if (
                not first_update_verified[0]
                and ready_for_hash_check
                and hasattr(agent, "acting_weights_digest")
            ):
                digest, count = agent.acting_weights_digest()
                initial = health_report.get("initial_acting_weights_sha256")
                if digest == initial:
                    health_report.update(
                        {
                            "status": "failed",
                            "failure": "acting weights unchanged after optimizer step 2",
                            "first_update_acting_weights_sha256": digest,
                        }
                    )
                    _write_training_health(health_path, health_report)
                    raise RuntimeError(
                        "Actor/world-model variables did not change after all "
                        "optimizers reached step 2."
                    )
                health_report.update(
                    {
                        "status": "first_update_verified",
                        "first_update_acting_weights_sha256": digest,
                        "acting_variable_count": count,
                    }
                )
                _write_training_health(health_path, health_report)
                first_update_verified[0] = True
            metrics.add(mets, prefix="train")
            if "priority" in outs:
                replay.prioritize(outs["key"], outs["priority"])
            updates.increment()
        agent.sync()
        agg = metrics.result()
        report = agent.report(batch[0])
        report = {k: v for k, v in report.items() if "train/" + k not in agg}
        logger.add(agg)
        logger.add(report, prefix="report")
        logger.add(replay.stats, prefix="replay")
        logger.add(timer.stats(), prefix="timer")
        logger.write(fps=True)
        episode.increment()

    driver.on_episode(train_step)

    print("Start training loop.")
    def policy(*policy_args):
        mode = "explore" if should_expl(step) else "train"
        try:
            return agent.policy(*policy_args, mode=mode)
        except Exception as error:
            record_failure(error, f"policy_{mode}")
            raise
    stop_file = Path(str(logdir)) / "STOP_TRAINING"
    while step < args.steps:
        if stop_file.exists():
            print(f"Stopping at validation request: {stop_file}")
            break
        driver(policy, episodes=1)
        if should_save(episode):
            checkpoint.save()
    replay.save(wait=True)
    checkpoint.save()
    logger.write()
