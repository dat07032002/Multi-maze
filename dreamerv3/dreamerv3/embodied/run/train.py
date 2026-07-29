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
    replay, directory, limit_steps=0, sampling="chronological"
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
    for episode_index, filename in enumerate(filenames):
        with np.load(filename, allow_pickle=False) as episode:
            keys = tuple(episode.files)
            if not {"image", "states", "goal", "action", "reward"}.issubset(keys):
                raise ValueError(f"Incomplete demonstration episode: {filename}")
            lengths = {len(episode[key]) for key in keys}
            if len(lengths) != 1:
                raise ValueError(f"Mismatched demonstration arrays: {filename}")
            for index in range(lengths.pop()):
                replay.add(
                    {key: episode[key][index] for key in keys},
                    worker=1_000_000 + episode_index,
                )
                loaded += 1
                if limit_steps and loaded >= int(limit_steps):
                    print(f"Loaded {loaded} expert demonstration steps from {root}.")
                    return loaded
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

    _load_demonstrations(
        replay,
        args.demo_dir,
        args.demo_limit_steps,
        args.demo_sampling,
    )
    print("Prefill train dataset.")
    if loaded_agent:
        print("Prefill uses the loaded checkpoint policy.")
        prefill_policy = lambda *xs: agent.policy(*xs, mode="train")
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

    def train_step(ep, worker):
        for _ in range(should_train(step)):
            with timer.scope("dataset"):
                batch[0] = next(dataset)
            outs, state[0], mets = agent.train(batch[0], state[0])
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
    policy = lambda *args: agent.policy(
        *args, mode="explore" if should_expl(step) else "train"
    )
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
