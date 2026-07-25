"""Render one deterministic DreamerV3 validation rollout as a GIF."""

from __future__ import annotations

import argparse
import pathlib
import sys

from PIL import Image, ImageDraw
import ruamel.yaml as yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=pathlib.Path, required=True)
    parser.add_argument("--checkpoint", type=pathlib.Path, required=True)
    parser.add_argument("--config", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--layout", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--frame-skip", type=int, default=2)
    args = parser.parse_args()

    repo = args.repo.resolve()
    dreamer_package = repo / "dreamerv3" / "dreamerv3"
    sys.path[:0] = [str(repo), str(dreamer_package.parent), str(dreamer_package)]

    import embodied
    from dreamerv3 import agent as agt
    from dreamerv3 import train as trainlib
    from dreamerv3.embodied.envs.tag_maze import TagMaze
    from tag_mujoco.maze_dataset import load_split
    from tag_mujoco.validation_metrics import episode_record

    config_data = yaml.YAML(typ="safe").load(
        args.config.resolve().read_text(encoding="utf-8")
    )
    config = embodied.Config(config_data).update(
        {
            "jax.prealloc": False,
            "wrapper.length": 3000,
            "env.tagmaze.maze_sampling": "uniform",
        }
    )
    split = load_split("validation", args.manifest.resolve())
    matches = [
        (path, metadata)
        for path, metadata in zip(split.paths, split.metadata)
        if path.name == args.layout
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one layout named {args.layout!r}, got {len(matches)}")
    layout_path, metadata = matches[0]

    def make_env():
        kwargs = dict(config.env.tagmaze)
        kwargs.update(
            maze_manifest="",
            maze_split="",
            maze_sampling="uniform",
            random_start=False,
            randomize_plant=False,
            start_curriculum=False,
            randomization_curriculum=False,
        )
        base = TagMaze(
            "sim", layout_paths=[str(layout_path)], seed=args.seed, **kwargs
        )
        wrapped = trainlib.wrap_env(base, config)
        return embodied.BatchEnv([wrapped], parallel=False)

    prototype = make_env()
    counter = embodied.Counter()
    agent = agt.Agent(prototype.obs_space, prototype.act_space, counter, config)
    prototype.close()

    loader = embodied.Checkpoint(parallel=False)
    loader.agent = agent
    loader.step = counter
    loader.load(args.checkpoint.resolve(), keys=["agent", "step"])

    env = make_env()
    frames: list[Image.Image] = []
    episodes = []
    step_index = 0

    def capture(transition, _worker):
        nonlocal step_index
        should_capture = (
            step_index % args.frame_skip == 0
            or bool(transition["is_first"])
            or bool(transition["is_last"])
        )
        if should_capture:
            raw = env.render()[0]
            image = Image.fromarray(raw).resize((540, 480), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (540, 520), "white")
            canvas.paste(image, (0, 40))
            progress = float(transition.get("log_progress", [0.0])[0])
            status = "GOAL" if bool(transition["is_last"]) and float(
                transition.get("log_success", [0.0])[0]
            ) else "RUNNING"
            ImageDraw.Draw(canvas).text(
                (12, 12),
                f"1M policy | {args.layout} | step {step_index} | "
                f"route {100.0 * progress:5.1f}% | {status}",
                fill="black",
            )
            frames.append(canvas.convert("P", palette=Image.Palette.ADAPTIVE, colors=128))
        step_index += 1

    driver = embodied.Driver(env)
    driver.on_step(capture)
    driver.on_episode(lambda episode, _worker: episodes.append(episode))
    policy = lambda *values: agent.policy(*values, mode="eval")
    try:
        driver(policy, episodes=1)
    finally:
        env.close()

    if len(episodes) != 1 or not frames:
        raise RuntimeError("Rollout did not produce one episode and GIF frames")
    record = episode_record(
        episodes[0],
        layout=layout_path.name,
        layout_seed=int(metadata["seed"]),
        difficulty_score=float(metadata["difficulty_score"]),
        difficulty_band=str(metadata["difficulty_band"]),
        evaluation_seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.output,
        save_all=True,
        append_images=frames[1:],
        duration=max(20, round(1000 * args.frame_skip / 35)),
        loop=0,
        optimize=False,
        disposal=2,
    )
    print({"checkpoint_step": int(counter), "frames": len(frames), **record})
    print(args.output)


if __name__ == "__main__":
    main()
