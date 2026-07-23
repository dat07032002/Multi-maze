import importlib
import os
from datetime import datetime

import rclpy


def _load_dreamer4_main():
    entry = os.environ.get("CYBERRUNNER_DREAMER4_ENTRY", "dreamer4.train:main")
    module_name, _, attr = entry.partition(":")
    if not module_name or not attr:
        raise RuntimeError(
            "CYBERRUNNER_DREAMER4_ENTRY must look like 'module:function', "
            f"got {entry!r}."
        )

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Dreamer4 is not installed on this Python path yet. Keep the old "
            "dreamerv3/ folder as-is, install or clone Dreamer4 separately, "
            "then set PYTHONPATH or CYBERRUNNER_DREAMER4_ENTRY. Default entry "
            "is 'dreamer4.train:main'."
        ) from exc

    try:
        return getattr(module, attr)
    except AttributeError as exc:
        raise RuntimeError(
            f"Dreamer4 entry {entry!r} was imported, but {attr!r} was not found."
        ) from exc


def main(args=None):
    rclpy.init(args=args)
    try:
        date_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_name = os.environ.get(
            "CYBERRUNNER_THOMAS_DREAMER4_RUN_NAME",
            f"thomas_dreamer4_tcp_{date_str}",
        )
        logdir = os.environ.get(
            "CYBERRUNNER_THOMAS_DREAMER4_LOGDIR",
            os.path.join("~/cyberrunner_logs", run_name),
        )
        argv = [
            "--configs",
            "cyberrunner",
            "large",
            "--task",
            "gym_cyberrunner_dreamer_thomas:cyberrunner-thomas-tcp-v0",
            "--logdir",
            logdir,
            "--replay_size",
            "1e6",
            "--run.script",
            os.environ.get("CYBERRUNNER_DREAMER4_SCRIPT", "train"),
            "--run.train_ratio",
            os.environ.get("CYBERRUNNER_DREAMER4_TRAIN_RATIO", "128"),
            "--run.save_every",
            os.environ.get("CYBERRUNNER_DREAMER4_SAVE_EVERY", "20"),
            "--run.log_every",
            os.environ.get("CYBERRUNNER_DREAMER4_LOG_EVERY", "10"),
            "--jax.policy_devices",
            os.environ.get("CYBERRUNNER_DREAMER4_POLICY_DEVICES", "0"),
            "--jax.train_devices",
            os.environ.get("CYBERRUNNER_DREAMER4_TRAIN_DEVICES", "0"),
        ]
        _load_dreamer4_main()(argv)
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
