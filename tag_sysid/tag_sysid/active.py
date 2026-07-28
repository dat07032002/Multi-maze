"""Approval-gated active TAG actuator measurements.

Without ``--execute`` this command only prints a dry-run plan. Execution also
requires an exact arm token, confirmation that an operator is present and the
marble is removed, a live estimator, the expected Hiwonder subscriber, and no
other publisher on the command topic.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any

import rclpy
from rclpy.node import Node

from .profiles import PROFILES, InterfaceProfile, get_profile, load_message_types
from .protocols import HARD_COMMAND_LIMIT, Phase, build_protocol, validate_protocol


ARM_TOKEN = "START_ACTIVE_SYSID"
STATE_FIELDS = (
    "monotonic_ns",
    "ros_time_ns",
    "source_time_ns",
    "source_age_ns",
    "elapsed_seconds",
    "phase_index",
    "phase_name",
    "repetition",
    "axis",
    "command_1",
    "command_2",
    "x_b_m",
    "y_b_m",
    "x_b_dot_mps",
    "y_b_dot_mps",
    "alpha_rad",
    "beta_rad",
    "ball_visible",
)

COMMAND_FIELDS = (
    "monotonic_ns",
    "ros_time_ns",
    "elapsed_seconds",
    "phase_index",
    "phase_name",
    "repetition",
    "axis",
    "command_1",
    "command_2",
)


def _plan_dict(phase: Phase) -> dict[str, object]:
    return {
        "name": phase.name,
        "repetition": phase.repetition,
        "axis": phase.axis,
        "command_1": phase.command_1,
        "command_2": phase.command_2,
        "duration_seconds": phase.duration_seconds,
    }


def _print_plan(
    test: str, phases: list[Phase], profile: InterfaceProfile
) -> None:
    total = sum(phase.duration_seconds for phase in phases)
    maximum = max(
        max(abs(phase.command_1), abs(phase.command_2)) for phase in phases
    )
    print(f"Test: {test}")
    print(f"Phases: {len(phases)}")
    print(f"Planned duration: {total:.1f} seconds")
    print(f"Maximum absolute command: {maximum:.1f}")
    print(f"Interface profile: {profile.name}")
    print(f"State topic: {profile.state_topic}")
    print(f"Command topic: {profile.command_topic}")
    print(f"Expected driver: {profile.expected_driver_node}")
    print("Dry run only: no ROS node was created and no command was published.")
    print(json.dumps([_plan_dict(phase) for phase in phases], indent=2))


class ActiveSysId(Node):
    """Run one exclusive, bounded actuator measurement protocol."""

    def __init__(
        self,
        args: argparse.Namespace,
        phases: list[Phase],
        profile: InterfaceProfile,
        state_type: type,
        command_type: type,
    ) -> None:
        super().__init__("tag_sysid_active")
        self.args = args
        self.phases = phases
        self.profile = profile
        self.state_type = state_type
        self.command_type = command_type
        self.started_ns = time.monotonic_ns()
        self.started_utc = datetime.now(timezone.utc).isoformat()
        self.latest_state: Any | None = None
        self.latest_state_ns: int | None = None
        self.angle_limit_exceeded: str | None = None
        self.baseline_alpha_rad: float | None = None
        self.baseline_beta_rad: float | None = None
        self.baseline_alpha_samples: list[float] = []
        self.baseline_beta_samples: list[float] = []
        self.state_count = 0
        self.command_count = 0
        self.current_phase_index = -1
        self.current_phase = Phase("preflight", 0, 0, 0.0, 0.0, 1.0)
        self.publisher = None
        self.exclusivity_lost = False

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.output_dir = (
            Path(args.output_root).expanduser().resolve()
            / f"{args.test}_{stamp}"
        )
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.state_file = (self.output_dir / "board_angles.csv").open(
            "w", newline="", encoding="utf-8"
        )
        self.command_file = (self.output_dir / "commands.csv").open(
            "w", newline="", encoding="utf-8"
        )
        self.state_writer = csv.DictWriter(
            self.state_file, fieldnames=STATE_FIELDS
        )
        self.command_writer = csv.DictWriter(
            self.command_file, fieldnames=COMMAND_FIELDS
        )
        self.state_writer.writeheader()
        self.command_writer.writeheader()
        self.state_subscription = self.create_subscription(
            self.state_type, self.profile.state_topic, self._on_state, 100
        )
        self._write_metadata("preflight")

    def _elapsed(self, now_ns: int) -> float:
        return (now_ns - self.started_ns) / 1e9

    def _on_state(self, message: Any) -> None:
        self.latest_state = message
        self.state_count += 1
        now_ns = time.monotonic_ns()
        ros_time_ns = int(self.get_clock().now().nanoseconds)
        header = getattr(message, "header", None)
        stamp = getattr(header, "stamp", None)
        source_time_ns = (
            int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)
            if stamp is not None
            else 0
        )
        self.latest_state_ns = now_ns
        self.baseline_alpha_samples.append(float(message.alpha))
        self.baseline_beta_samples.append(float(message.beta))
        limit_rad = math.radians(self.args.max_board_angle_deg)
        if not (
            math.isfinite(float(message.alpha))
            and math.isfinite(float(message.beta))
        ):
            self.angle_limit_exceeded = "non-finite board angle received"
        elif (
            self.args.baseline_relative_angle_safety
            and self.baseline_alpha_rad is None
        ):
            # During preflight, collect a finite neutral reference before
            # evaluating placement-dependent camera angle offsets.
            self.angle_limit_exceeded = None
        else:
            safety_alpha = float(message.alpha)
            safety_beta = float(message.beta)
            if self.args.baseline_relative_angle_safety:
                safety_alpha -= self.baseline_alpha_rad
                safety_beta -= self.baseline_beta_rad
            if abs(safety_alpha) > limit_rad:
                label = (
                    "alpha excursion"
                    if self.args.baseline_relative_angle_safety
                    else "alpha"
                )
                self.angle_limit_exceeded = (
                    f"{label} {math.degrees(safety_alpha):.2f} deg exceeds "
                    f"{self.args.max_board_angle_deg:.2f} deg"
                )
            elif abs(safety_beta) > limit_rad:
                label = (
                    "beta excursion"
                    if self.args.baseline_relative_angle_safety
                    else "beta"
                )
                self.angle_limit_exceeded = (
                    f"{label} {math.degrees(safety_beta):.2f} deg exceeds "
                    f"{self.args.max_board_angle_deg:.2f} deg"
                )
            else:
                self.angle_limit_exceeded = None
        if (
            self.angle_limit_exceeded is None
            and self.baseline_alpha_rad is not None
        ):
            excursion_limit = math.radians(
                self.args.max_angle_excursion_deg
            )
            alpha_excursion = float(message.alpha) - self.baseline_alpha_rad
            beta_excursion = float(message.beta) - self.baseline_beta_rad
            if abs(alpha_excursion) > excursion_limit:
                self.angle_limit_exceeded = (
                    f"alpha excursion {math.degrees(alpha_excursion):.2f} deg "
                    f"exceeds {self.args.max_angle_excursion_deg:.2f} deg"
                )
            elif abs(beta_excursion) > excursion_limit:
                self.angle_limit_exceeded = (
                    f"beta excursion {math.degrees(beta_excursion):.2f} deg "
                    f"exceeds {self.args.max_angle_excursion_deg:.2f} deg"
                )
        phase = self.current_phase
        visible = math.isfinite(message.x_b) and math.isfinite(message.y_b)
        self.state_writer.writerow(
            {
                "monotonic_ns": now_ns,
                "ros_time_ns": ros_time_ns,
                "source_time_ns": source_time_ns if source_time_ns else "",
                "source_age_ns": (
                    ros_time_ns - source_time_ns if source_time_ns else ""
                ),
                "elapsed_seconds": f"{self._elapsed(now_ns):.9f}",
                "phase_index": self.current_phase_index,
                "phase_name": phase.name,
                "repetition": phase.repetition,
                "axis": phase.axis,
                "command_1": phase.command_1,
                "command_2": phase.command_2,
                "x_b_m": message.x_b,
                "y_b_m": message.y_b,
                "x_b_dot_mps": message.x_b_dot,
                "y_b_dot_mps": message.y_b_dot,
                "alpha_rad": message.alpha,
                "beta_rad": message.beta,
                "ball_visible": int(visible),
            }
        )

    def _external_publishers(self) -> list[str]:
        result = []
        for endpoint in self.get_publishers_info_by_topic(
            self.profile.command_topic
        ):
            if endpoint.node_name != self.get_name():
                result.append(
                    f"{endpoint.node_namespace.rstrip('/')}/{endpoint.node_name}"
                )
        return sorted(set(result))

    def _driver_subscriber_present(self) -> bool:
        return any(
            endpoint.node_name == self.profile.expected_driver_node
            for endpoint in self.get_subscriptions_info_by_topic(
                self.profile.command_topic
            )
        )

    def validate_additional_preflight(self) -> None:
        """Allow specialized runners to add checks before arming output."""

    def validate_additional_runtime(self) -> None:
        """Allow specialized runners to stop between command publications."""

    def preflight(self) -> None:
        deadline = time.monotonic() + self.args.state_timeout
        while self.latest_state is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.latest_state is None:
            raise RuntimeError(f"no state received on {self.profile.state_topic}")
        baseline_deadline = time.monotonic() + self.args.baseline_seconds
        while time.monotonic() < baseline_deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
        if not (
            math.isfinite(self.latest_state.alpha)
            and math.isfinite(self.latest_state.beta)
        ):
            raise RuntimeError("board-angle estimator is not producing finite values")
        if self.angle_limit_exceeded:
            raise RuntimeError(
                "initial board angle is outside the safety bound: "
                + self.angle_limit_exceeded
            )
        self.baseline_alpha_rad = statistics.median(
            self.baseline_alpha_samples
        )
        self.baseline_beta_rad = statistics.median(
            self.baseline_beta_samples
        )
        self.get_logger().info(
            "baseline board angles: "
            f"alpha={math.degrees(self.baseline_alpha_rad):.2f} deg, "
            f"beta={math.degrees(self.baseline_beta_rad):.2f} deg; "
            f"maximum excursion={self.args.max_angle_excursion_deg:.2f} deg"
        )
        self.validate_additional_preflight()
        if not self._driver_subscriber_present():
            raise RuntimeError(
                "expected driver node "
                f"{self.profile.expected_driver_node!r} is not subscribed"
            )
        external = self._external_publishers()
        if external:
            raise RuntimeError(
                "refusing active sysid; other command publishers exist: "
                + ", ".join(external)
            )
        self.publisher = self.create_publisher(
            self.command_type, self.profile.command_topic, 10
        )
        # Recheck after our endpoint has entered the graph to close the startup
        # race with a policy or TCP bridge starting concurrently.
        end = time.monotonic() + 0.5
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        external = self._external_publishers()
        if external:
            self.exclusivity_lost = True
            raise RuntimeError(
                "command-topic exclusivity was lost during preflight: "
                + ", ".join(external)
            )

    def _publish(self, phase: Phase, enforce_state_safety: bool = True) -> None:
        external = self._external_publishers()
        if external:
            self.exclusivity_lost = True
            raise RuntimeError(
                "another command publisher appeared; stopping output: "
                + ", ".join(external)
            )
        if self.publisher is None:
            raise RuntimeError("publisher is not armed")
        if enforce_state_safety:
            if self.angle_limit_exceeded:
                raise RuntimeError(
                    "board-angle safety bound exceeded: "
                    + self.angle_limit_exceeded
                )
            if self.latest_state_ns is None:
                raise RuntimeError("state timestamp is unavailable")
            state_age = (time.monotonic_ns() - self.latest_state_ns) / 1e9
            if state_age > self.args.runtime_state_timeout:
                raise RuntimeError(
                    f"state stream is stale ({state_age:.3f}s); stopping output"
                )
        message = self.command_type()
        published_ros_ns = int(self.get_clock().now().nanoseconds)
        if hasattr(message, "header"):
            message.header.stamp = self.get_clock().now().to_msg()
        message.vel_1 = float(phase.command_1)
        message.vel_2 = float(phase.command_2)
        self.publisher.publish(message)
        now_ns = time.monotonic_ns()
        self.command_count += 1
        self.command_writer.writerow(
            {
                "monotonic_ns": now_ns,
                "ros_time_ns": published_ros_ns,
                "elapsed_seconds": f"{self._elapsed(now_ns):.9f}",
                "phase_index": self.current_phase_index,
                "phase_name": phase.name,
                "repetition": phase.repetition,
                "axis": phase.axis,
                "command_1": phase.command_1,
                "command_2": phase.command_2,
            }
        )

    def run_protocol(self) -> None:
        self._write_metadata("running")
        for index, phase in enumerate(self.phases):
            self.current_phase_index = index
            self.current_phase = phase
            self.get_logger().info(
                f"phase {index + 1}/{len(self.phases)} {phase.name}: "
                f"cmd=({phase.command_1:.0f}, {phase.command_2:.0f}) "
                f"for {phase.duration_seconds:.1f}s"
            )
            deadline = time.monotonic() + phase.duration_seconds
            next_publish = 0.0
            while time.monotonic() < deadline:
                now = time.monotonic()
                if now >= next_publish:
                    self._publish(phase)
                    next_publish = now + 0.1
                rclpy.spin_once(self, timeout_sec=0.01)
                self.validate_additional_runtime()
        self.return_home()
        self._write_metadata("complete")

    def return_home(self) -> None:
        if self.publisher is None or self.exclusivity_lost:
            return
        home = Phase("emergency_home", 0, 0, 0.0, 0.0, 1.0)
        self.current_phase = home
        self.current_phase_index = len(self.phases)
        for _ in range(10):
            self._publish(home, enforce_state_safety=False)
            rclpy.spin_once(self, timeout_sec=0.05)

    def _write_metadata(self, status: str) -> None:
        data = {
            "schema_version": 1,
            "test": self.args.test,
            "status": status,
            "started_utc": self.started_utc,
            "hard_command_limit": HARD_COMMAND_LIMIT,
            "command_scale": self.args.command_scale,
            "max_board_angle_deg": self.args.max_board_angle_deg,
            "baseline_relative_angle_safety": bool(
                self.args.baseline_relative_angle_safety
            ),
            "max_angle_excursion_deg": self.args.max_angle_excursion_deg,
            "baseline_seconds": self.args.baseline_seconds,
            "baseline_alpha_deg": (
                math.degrees(self.baseline_alpha_rad)
                if self.baseline_alpha_rad is not None
                else None
            ),
            "baseline_beta_deg": (
                math.degrees(self.baseline_beta_rad)
                if self.baseline_beta_rad is not None
                else None
            ),
            "runtime_state_timeout_s": self.args.runtime_state_timeout,
            "operator_present_confirmed": bool(self.args.operator_present),
            "ball_removed_confirmed": bool(self.args.ball_removed),
            "interface_profile": self.profile.name,
            "command_topic": self.profile.command_topic,
            "state_topic": self.profile.state_topic,
            "expected_driver_node": self.profile.expected_driver_node,
            "state_samples": self.state_count,
            "command_samples": self.command_count,
            "plan": [_plan_dict(phase) for phase in self.phases],
            "safety": {
                "requires_exact_arm_token": True,
                "refuses_external_command_publishers": True,
                "one_axis_at_a_time": True,
                "aborts_on_board_angle_limit": True,
                "aborts_on_angle_excursion_from_baseline": True,
                "aborts_on_stale_state": True,
                "returns_home_on_normal_completion_or_interrupt": True,
                "driver_timeout_is_final_fallback": True,
            },
        }
        temporary = self.output_dir / "metadata.json.tmp"
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.output_dir / "metadata.json")

    def close_files(self) -> None:
        self.state_file.flush()
        self.command_file.flush()
        self.state_file.close()
        self.command_file.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", required=True, choices=("home", "axis", "sweep", "step"))
    parser.add_argument("--output-root", default="~/tag_sysid_logs/active")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--hold-seconds", type=float)
    parser.add_argument(
        "--axis-only",
        type=int,
        choices=(1, 2),
        help="run only the selected motor axis; default runs both axes",
    )
    parser.add_argument(
        "--command-scale",
        type=float,
        default=1.0,
        help="scale every nonzero protocol command; must be in [0.1, 1.0]",
    )
    parser.add_argument("--max-command", type=float, default=40.0)
    parser.add_argument("--state-timeout", type=float, default=10.0)
    parser.add_argument(
        "--runtime-state-timeout",
        type=float,
        default=0.25,
        help="abort if the estimator is this stale while commands are active",
    )
    parser.add_argument(
        "--max-board-angle-deg",
        type=float,
        default=15.0,
        help="absolute alpha/beta safety bound during active excitation",
    )
    parser.add_argument(
        "--max-angle-excursion-deg",
        type=float,
        default=4.0,
        help="maximum alpha/beta change from the preflight median",
    )
    parser.add_argument(
        "--baseline-relative-angle-safety",
        action="store_true",
        help=(
            "evaluate board-angle safety after subtracting the measured "
            "neutral baseline; raw angles remain recorded"
        ),
    )
    parser.add_argument(
        "--baseline-seconds",
        type=float,
        default=1.0,
        help="preflight interval used to estimate the angle zero",
    )
    parser.add_argument(
        "--interface-profile",
        choices=tuple(sorted(PROFILES)),
        default="tag",
        help="ROS names and message package used by the running stack",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--arm", default="")
    parser.add_argument("--operator-present", action="store_true")
    parser.add_argument("--ball-removed", action="store_true")
    return parser


def main(argv=None) -> None:
    parser = _parser()
    args, ros_args = parser.parse_known_args(argv)
    profile = get_profile(args.interface_profile)
    phases = build_protocol(
        args.test,
        args.repetitions,
        args.hold_seconds,
        command_scale=args.command_scale,
        axes=(args.axis_only,) if args.axis_only else (1, 2),
    )
    validate_protocol(phases)
    planned_maximum = max(
        max(abs(phase.command_1), abs(phase.command_2)) for phase in phases
    )
    if not args.execute:
        _print_plan(args.test, phases, profile)
        return
    if args.arm != ARM_TOKEN:
        parser.error(f"execution requires --arm {ARM_TOKEN}")
    if not args.operator_present:
        parser.error("execution requires --operator-present")
    if not args.ball_removed:
        parser.error("execution requires --ball-removed")
    if not 0.0 < args.max_command <= HARD_COMMAND_LIMIT:
        parser.error(f"--max-command must be in (0, {HARD_COMMAND_LIMIT}]")
    if not 0.1 <= args.command_scale <= 1.0:
        parser.error("--command-scale must be in [0.1, 1.0]")
    if not 0.0 < args.max_board_angle_deg <= 20.0:
        parser.error("--max-board-angle-deg must be in (0, 20]")
    if not 0.25 <= args.max_angle_excursion_deg <= 5.0:
        parser.error("--max-angle-excursion-deg must be in [0.25, 5]")
    if not 0.5 <= args.baseline_seconds <= 3.0:
        parser.error("--baseline-seconds must be in [0.5, 3]")
    if not 0.05 <= args.runtime_state_timeout <= 1.0:
        parser.error("--runtime-state-timeout must be in [0.05, 1.0]")
    if planned_maximum > args.max_command:
        parser.error(
            f"plan reaches {planned_maximum}; explicitly allow it with "
            f"--max-command {planned_maximum:g}"
        )

    state_type, command_type = load_message_types(profile)
    rclpy.init(args=ros_args)
    node = ActiveSysId(args, phases, profile, state_type, command_type)
    failure = None
    try:
        node.preflight()
        node.run_protocol()
    except KeyboardInterrupt:
        node.get_logger().warning("operator interrupt; requesting home")
        failure = "operator_interrupt"
    except Exception as exc:  # safety handoff must retain the exact failure
        node.get_logger().error(str(exc))
        failure = str(exc)
    finally:
        try:
            node.return_home()
            node._write_metadata(failure or "complete")
        finally:
            node.close_files()
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
    if failure:
        raise SystemExit(failure)


if __name__ == "__main__":
    main()
