import os
import sys
from datetime import datetime
import rclpy
from dreamerv3.train import main as train
from datetime import datetime


def main(args=None):
    rclpy.init(args=args)
    now = datetime.now()
    date_str = now.strftime("%Y%m%d-%H%M%S")
    run_name = os.environ.get("CYBERRUNNER_THOMAS_TCP_RUN_NAME", f"thomas_tcp_{date_str}")
    logdir = os.environ.get(
        "CYBERRUNNER_THOMAS_TCP_LOGDIR", os.path.join("~/cyberrunner_logs", run_name)
    )
    argv = [
        "--configs",
        "cyberrunner",
        "large",  # TODO add config file here!
        "--task",
        "gym_cyberrunner_dreamer_thomas:cyberrunner-thomas-tcp-v0",
        "--logdir",
        logdir,
        "--replay_size",
        "1e6",
        "--run.script",
        "train_top5",
        "--run.train_ratio",
        "128",
        "--run.save_every",
        "20",
        "--run.log_every",
        "10",
        "--jax.policy_devices",
        "0",
        "--jax.train_devices",
        "0",
    ]

    # import os
    # os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    train(argv)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
