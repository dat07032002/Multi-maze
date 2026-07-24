"""Instantiate the Dreamer adapter without creating an agent or training."""

from __future__ import annotations

import pathlib
import sys

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
DREAMER_PACKAGE = HERE.parent / "dreamerv3" / "dreamerv3"
sys.path.insert(0, str(DREAMER_PACKAGE))
sys.path.insert(0, str(HERE.parent))

from embodied.envs.cyberrunner import CyberRunner  # noqa: E402
from cyberrunner_mujoco.policy_contract import TagPolicyContract  # noqa: E402


def main() -> None:
    env = CyberRunner(
        maze_manifest=str(HERE / "maze_splits.json"),
        maze_split="train",
        maze_sampling="curriculum",
    )
    if len(env._env.layout_paths) != 40:
        raise RuntimeError("Dreamer adapter did not load the 40-maze training split")
    reset = env.step({"reset": True, "action": np.zeros(2, dtype=np.float32)})
    if not reset["is_first"] or reset["is_last"]:
        raise RuntimeError("Dreamer reset flags are invalid")
    step = env.step({"reset": False, "action": np.zeros(2, dtype=np.float32)})
    if step["image"].shape != (64, 64, 1) or step["goal"].shape != (10,):
        raise RuntimeError("Dreamer observation contract is invalid")
    if not np.isfinite(step["reward"]):
        raise RuntimeError("Dreamer adapter emitted a non-finite reward")
    if "ball_visible" in step:
        raise RuntimeError("Dreamer adapter exposes non-deployed ball_visible input")
    TagPolicyContract().validate_observation(step)
    if env.info["maze_split"] != "train":
        raise RuntimeError("Dreamer adapter selected a held-out split")
    print("Dreamer multi-maze adapter check passed; no agent or training was started.")


if __name__ == "__main__":
    main()
