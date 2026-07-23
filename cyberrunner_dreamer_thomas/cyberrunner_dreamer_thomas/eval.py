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
    source_run = os.environ.get("CYBERRUNNER_THOMAS_EVAL_RUN", "thomas_dynamixel")
    checkpoint = os.environ.get(
        "CYBERRUNNER_THOMAS_CHECKPOINT",
        "~/cyberrunner_logs/{}/checkpoint.ckpt".format(source_run),
    )
    eval_logdir = os.environ.get(
        "CYBERRUNNER_THOMAS_EVAL_LOGDIR",
        "~/cyberrunner_logs/eval_thomas_dynamixel_" + date_str,
    )
    # date_str = '2023-08-23:04-17-46'
    argv = [
        "--configs",
        "cyberrunner",
        "large",  # TODO add config file here!
        "--task",
        "gym_cyberrunner_dreamer_thomas:cyberrunner-thomas-ros-v0",
        "--logdir",
        eval_logdir,
        "--run.from_checkpoint",
        checkpoint,
        "--run.steps",
        "10000",
        "--run.script",
        "eval_only",
        "--jax.policy_devices",
        "0",
        "--jax.train_devices",
        "0",
    ]
    train(argv)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
