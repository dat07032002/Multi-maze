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
    run_name = os.environ.get(
        "CYBERRUNNER_THOMAS_RUN_NAME", f"thomas_dynamixel_parallel_{date_str}"
    )
    logdir = os.environ.get(
        "CYBERRUNNER_THOMAS_LOGDIR", os.path.join("~/cyberrunner_logs", run_name)
    )
    argv = [
        "--configs",
        "cyberrunner",
        "large",  # TODO add config file here!
        "--task",
        "gym_cyberrunner_dreamer_thomas:cyberrunner-thomas-ros-v0",
        "--logdir",
        logdir,
        "--replay_size",
        "1e6",
        "--run.script",
        "parallel",
        "--run.train_ratio",
        "-1",
        "--run.save_every",
        "20",
        "--run.log_every",
        "10",
        "--jax.policy_devices",
        "1",
        "--jax.train_devices",
        "0",
    ]

    # import os
    # os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    train(argv)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
