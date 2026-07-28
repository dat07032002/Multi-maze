"""Passive ROS 2 recorder for TAG system-identification signals.

This node intentionally has no publishers, services, or action clients. It can
observe a live policy run without changing motor commands or reset behavior.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import re
import socket
import sys
import time
from typing import Any

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from .profiles import get_profile, load_message_types


CAMERA_FIELDS = (
    "ros_time_ns",
    "monotonic_ns",
    "header_time_ns",
    "header_age_ns",
    "height",
    "width",
    "step",
    "encoding",
)
STATE_FIELDS = (
    "ros_time_ns",
    "monotonic_ns",
    "source_time_ns",
    "source_age_ns",
    "x_b_m",
    "y_b_m",
    "x_b_dot_mps",
    "y_b_dot_mps",
    "alpha_rad",
    "beta_rad",
    "ball_visible",
)
COMMAND_FIELDS = (
    "ros_time_ns",
    "monotonic_ns",
    "vel_1",
    "vel_2",
    "target_pos_1",
    "target_pos_2",
)


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._") or datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )


class CsvSink:
    def __init__(self, path: Path, fields: tuple[str, ...], flush_every: int):
        self.path = path
        self.file = path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=fields)
        self.writer.writeheader()
        self.flush_every = max(1, int(flush_every))
        self.count = 0

    def write(self, row: dict[str, Any]) -> None:
        self.writer.writerow(row)
        self.count += 1
        if self.count % self.flush_every == 0:
            self.file.flush()

    def close(self) -> None:
        if not self.file.closed:
            self.file.flush()
            self.file.close()


class SysIdRecorder(Node):
    def __init__(self) -> None:
        super().__init__("tag_sysid_recorder")
        self.declare_parameter("output_root", "~/tag_sysid_logs")
        self.declare_parameter("session_name", "")
        self.declare_parameter("max_duration_sec", 0.0)
        self.declare_parameter("flush_every", 25)
        self.declare_parameter("record_camera_timing", True)
        self.declare_parameter("status_period_sec", 5.0)
        self.declare_parameter("home_pos_1", 500.0)
        self.declare_parameter("home_pos_2", 500.0)
        self.declare_parameter("command_scale_1", 1.5)
        self.declare_parameter("command_scale_2", 1.5)
        self.declare_parameter("servo_min_1", 100.0)
        self.declare_parameter("servo_max_1", 900.0)
        self.declare_parameter("servo_min_2", 100.0)
        self.declare_parameter("servo_max_2", 900.0)
        self.declare_parameter("interface_profile", "tag")

        self.profile = get_profile(
            str(self.get_parameter("interface_profile").value)
        )
        self.state_type, self.command_type = load_message_types(self.profile)

        output_root = Path(
            str(self.get_parameter("output_root").value)
        ).expanduser()
        requested_name = str(self.get_parameter("session_name").value)
        session_name = _safe_name(requested_name)
        self.session_dir = (output_root / session_name).resolve()
        self.session_dir.mkdir(parents=True, exist_ok=False)

        flush_every = int(self.get_parameter("flush_every").value)
        self.camera_sink = CsvSink(
            self.session_dir / "camera.csv", CAMERA_FIELDS, flush_every
        )
        self.state_sink = CsvSink(
            self.session_dir / "states.csv", STATE_FIELDS, flush_every
        )
        self.command_sink = CsvSink(
            self.session_dir / "commands.csv", COMMAND_FIELDS, flush_every
        )
        self.sinks = (self.camera_sink, self.state_sink, self.command_sink)

        self.started_utc = datetime.now(timezone.utc)
        self.started_monotonic_ns = time.monotonic_ns()
        self.finished = False
        self.camera_count = 0
        self.state_count = 0
        self.command_count = 0
        self.ball_missing_count = 0
        self.home = (
            float(self.get_parameter("home_pos_1").value),
            float(self.get_parameter("home_pos_2").value),
        )
        self.scale = (
            float(self.get_parameter("command_scale_1").value),
            float(self.get_parameter("command_scale_2").value),
        )
        self.servo_limits = (
            (
                float(self.get_parameter("servo_min_1").value),
                float(self.get_parameter("servo_max_1").value),
            ),
            (
                float(self.get_parameter("servo_min_2").value),
                float(self.get_parameter("servo_max_2").value),
            ),
        )
        self.record_camera = bool(
            self.get_parameter("record_camera_timing").value
        )

        if self.record_camera:
            self.camera_subscription = self.create_subscription(
                Image,
                self.profile.camera_topic,
                self.on_camera,
                qos_profile_sensor_data,
            )
        self.state_subscription = self.create_subscription(
            self.state_type,
            self.profile.state_topic,
            self.on_state,
            100,
        )
        self.command_subscription = self.create_subscription(
            self.command_type,
            self.profile.command_topic,
            self.on_command,
            100,
        )

        status_period = max(
            1.0, float(self.get_parameter("status_period_sec").value)
        )
        self.status_timer = self.create_timer(status_period, self.report_status)
        max_duration = float(self.get_parameter("max_duration_sec").value)
        if max_duration > 0.0:
            self.stop_timer = self.create_timer(max_duration, self.stop_after_limit)

        self._write_metadata(completed=False)
        self.get_logger().info(
            f"Passive sysid recording started: {self.session_dir}"
        )
        self.get_logger().info(
            "Safety: this node has no publishers and cannot command or reset the motors."
        )

    def _times(self) -> tuple[int, int]:
        return int(self.get_clock().now().nanoseconds), time.monotonic_ns()

    def on_camera(self, msg: Image) -> None:
        ros_ns, monotonic_ns = self._times()
        header_ns = int(msg.header.stamp.sec) * 1_000_000_000 + int(
            msg.header.stamp.nanosec
        )
        self.camera_sink.write(
            {
                "ros_time_ns": ros_ns,
                "monotonic_ns": monotonic_ns,
                "header_time_ns": header_ns,
                "header_age_ns": ros_ns - header_ns if header_ns else "",
                "height": int(msg.height),
                "width": int(msg.width),
                "step": int(msg.step),
                "encoding": str(msg.encoding),
            }
        )
        self.camera_count += 1

    def on_state(self, msg) -> None:
        ros_ns, monotonic_ns = self._times()
        header = getattr(msg, "header", None)
        stamp = getattr(header, "stamp", None)
        source_ns = (
            int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)
            if stamp is not None
            else 0
        )
        visible = math.isfinite(float(msg.x_b)) and math.isfinite(float(msg.y_b))
        self.state_sink.write(
            {
                "ros_time_ns": ros_ns,
                "monotonic_ns": monotonic_ns,
                "source_time_ns": source_ns if source_ns else "",
                "source_age_ns": ros_ns - source_ns if source_ns else "",
                "x_b_m": float(msg.x_b),
                "y_b_m": float(msg.y_b),
                "x_b_dot_mps": float(msg.x_b_dot),
                "y_b_dot_mps": float(msg.y_b_dot),
                "alpha_rad": float(msg.alpha),
                "beta_rad": float(msg.beta),
                "ball_visible": int(visible),
            }
        )
        self.state_count += 1
        self.ball_missing_count += int(not visible)

    def on_command(self, msg) -> None:
        ros_ns, monotonic_ns = self._times()
        vel_1, vel_2 = float(msg.vel_1), float(msg.vel_2)
        target_1 = round(self.home[0] + self.scale[0] * vel_1)
        target_2 = round(self.home[1] + self.scale[1] * vel_2)
        target_1 = min(
            max(target_1, self.servo_limits[0][0]), self.servo_limits[0][1]
        )
        target_2 = min(
            max(target_2, self.servo_limits[1][0]), self.servo_limits[1][1]
        )
        self.command_sink.write(
            {
                "ros_time_ns": ros_ns,
                "monotonic_ns": monotonic_ns,
                "vel_1": vel_1,
                "vel_2": vel_2,
                "target_pos_1": target_1,
                "target_pos_2": target_2,
            }
        )
        self.command_count += 1

    def elapsed_seconds(self) -> float:
        return (time.monotonic_ns() - self.started_monotonic_ns) / 1e9

    def report_status(self) -> None:
        elapsed = max(self.elapsed_seconds(), 1e-9)
        missing = self.ball_missing_count / max(self.state_count, 1)
        self.get_logger().info(
            f"sysid {elapsed:.1f}s | camera {self.camera_count / elapsed:.1f} Hz | "
            f"state {self.state_count / elapsed:.1f} Hz | "
            f"command {self.command_count / elapsed:.1f} Hz | "
            f"ball missing {100.0 * missing:.2f}%"
        )

    def stop_after_limit(self) -> None:
        self.get_logger().info("Configured recording duration reached; stopping.")
        self.finish()

    def _metadata(self, completed: bool) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "passive": True,
            "publishes_commands": False,
            "completed": bool(completed),
            "started_utc": self.started_utc.isoformat(),
            "finished_utc": (
                datetime.now(timezone.utc).isoformat() if completed else None
            ),
            "duration_seconds": self.elapsed_seconds(),
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": sys.version,
            "interface_profile": self.profile.name,
            "topics": {
                "camera": (
                    self.profile.camera_topic if self.record_camera else None
                ),
                "state": self.profile.state_topic,
                "command": self.profile.command_topic,
            },
            "counts": {
                "camera": self.camera_count,
                "state": self.state_count,
                "command": self.command_count,
                "ball_missing": self.ball_missing_count,
            },
            "command_conversion": {
                "home_positions": list(self.home),
                "servo_units_per_command": list(self.scale),
                "servo_limits": [list(pair) for pair in self.servo_limits],
            },
            "limitations": [
                (
                    "Legacy interface profiles may not provide state source "
                    "timestamps; blank source fields fall back to receipt time."
                ),
                (
                    "Commanded servo targets are derived from configuration "
                    "and are not measured servo positions."
                ),
                (
                    "Passive policy data cannot identify backlash or friction "
                    "as cleanly as a gated excitation test."
                ),
            ],
        }

    def _write_metadata(self, completed: bool) -> None:
        destination = self.session_dir / "metadata.json"
        temporary = self.session_dir / "metadata.json.tmp"
        temporary.write_text(
            json.dumps(self._metadata(completed), indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, destination)

    def finish(self) -> None:
        if self.finished:
            return
        self.finished = True
        for sink in self.sinks:
            sink.close()
        self._write_metadata(completed=True)
        self.get_logger().info(f"Sysid session complete: {self.session_dir}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SysIdRecorder()
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        node.finish()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
