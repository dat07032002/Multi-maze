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
import time

import rclpy
from rclpy.node import Node
from tag_interfaces.msg import HiwonderVel, StateEstimate

from .protocols import HARD_COMMAND_LIMIT, Phase, build_protocol, validate_protocol


ARM_TOKEN = "START_ACTIVE_SYSID"
COMMAND_TOPIC = "/tag_hiwonder/cmd"
STATE_TOPIC = "/tag_state_estimation/estimate"
EXPECTED_DRIVER_NODE = "tag_hiwonder_compat"

STATE_FIELDS = (
    "monotonic_ns",
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


def _print_plan(test: str, phases: list[Phase]) -> None:
    total = sum(phase.duration_seconds for phase in phases)
    maximum = max(
        max(abs(phase.command_1), abs(phase.command_2)) for phase in phases
    )
    print(f"Test: {test}")
    print(f"Phases: {len(phases)}")
    print(f"Planned duration: {total:.1f} seconds")
    print(f"Maximum absolute command: {maximum:.1f}")
    print("Dry run only: no ROS node was created and no command was published.")
    print(json.dumps([_plan_dict(phase) for phase in phases], indent=2))


class ActiveSysId(Node):
    """Run one exclusive, bounded actuator measurement protocol."""

    def __init__(self, args: argparse.Namespace, phases: list[Phase]) -> None:
        super().__init__("tag_sysid_active")
        self.args = args
        self.phases = phases
        self.started_ns = time.monotonic_ns()
        self.started_utc = datetime.now(timezone.utc).isoformat()
        self.latest_state: StateEstimate | None = None
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
            StateEstimate, STATE_TOPIC, self._on_state, 100
        )
        self._write_metadata("preflight")

    def _elapsed(self, now_ns: int) -> float:
        return (now_ns - self.started_ns) / 1e9

    def _on_state(self, message: StateEstimate) -> None:
        self.latest_state = message
        self.state_count += 1
        now_ns = time.monotonic_ns()
        phase = self.current_phase
        visible = math.isfinite(message.x_b) and math.isfinite(message.y_b)
        self.state_writer.writerow(
            {
                "monotonic_ns": now_ns,
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
        for endpoint in self.get_publishers_info_by_topic(COMMAND_TOPIC):
            if endpoint.node_name != self.get_name():
                result.append(
                    f"{endpoint.node_namespace.rstrip('/')}/{endpoint.node_name}"
                )
        return sorted(set(result))

    def _driver_subscriber_present(self) -> bool:
        return any(
            endpoint.node_name == EXPECTED_DRIVER_NODE
            for endpoint in self.get_subscriptions_info_by_topic(COMMAND_TOPIC)
        )

    def preflight(self) -> None:
        deadline = time.monotonic() + self.args.state_timeout
        while self.latest_state is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.latest_state is None:
            raise RuntimeError(f"no state received on {STATE_TOPIC}")
        if not (
            math.isfinite(self.latest_state.alpha)
            and math.isfinite(self.latest_state.beta)
        ):
            raise RuntimeError("board-angle estimator is not producing finite values")
        if not self._driver_subscriber_present():
            raise RuntimeError(
                f"expected driver node {EXPECTED_DRIVER_NODE!r} is not subscribed"
            )
        external = self._external_publishers()
        if external:
            raise RuntimeError(
                "refusing active sysid; other command publishers exist: "
                + ", ".join(external)
            )
        self.publisher = self.create_publisher(HiwonderVel, COMMAND_TOPIC, 10)
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

    def _publish(self, phase: Phase) -> None:
        external = self._external_publishers()
        if external:
            self.exclusivity_lost = True
            raise RuntimeError(
                "another command publisher appeared; stopping output: "
                + ", ".join(external)
            )
        if self.publisher is None:
            raise RuntimeError("publisher is not armed")
        message = HiwonderVel()
        message.vel_1 = float(phase.command_1)
        message.vel_2 = float(phase.command_2)
        self.publisher.publish(message)
        now_ns = time.monotonic_ns()
        self.command_count += 1
        self.command_writer.writerow(
            {
                "monotonic_ns": now_ns,
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
        self.return_home()
        self._write_metadata("complete")

    def return_home(self) -> None:
        if self.publisher is None or self.exclusivity_lost:
            return
        home = Phase("emergency_home", 0, 0, 0.0, 0.0, 1.0)
        self.current_phase = home
        self.current_phase_index = len(self.phases)
        for _ in range(10):
            self._publish(home)
            rclpy.spin_once(self, timeout_sec=0.05)

    def _write_metadata(self, status: str) -> None:
        data = {
            "schema_version": 1,
            "test": self.args.test,
            "status": status,
            "started_utc": self.started_utc,
            "hard_command_limit": HARD_COMMAND_LIMIT,
            "operator_present_confirmed": bool(self.args.operator_present),
            "ball_removed_confirmed": bool(self.args.ball_removed),
            "command_topic": COMMAND_TOPIC,
            "state_topic": STATE_TOPIC,
            "expected_driver_node": EXPECTED_DRIVER_NODE,
            "state_samples": self.state_count,
            "command_samples": self.command_count,
            "plan": [_plan_dict(phase) for phase in self.phases],
            "safety": {
                "requires_exact_arm_token": True,
                "refuses_external_command_publishers": True,
                "one_axis_at_a_time": True,
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
    parser.add_argument("--max-command", type=float, default=40.0)
    parser.add_argument("--state-timeout", type=float, default=10.0)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--arm", default="")
    parser.add_argument("--operator-present", action="store_true")
    parser.add_argument("--ball-removed", action="store_true")
    return parser


def main(argv=None) -> None:
    parser = _parser()
    args, ros_args = parser.parse_known_args(argv)
    phases = build_protocol(args.test, args.repetitions, args.hold_seconds)
    validate_protocol(phases)
    planned_maximum = max(
        max(abs(phase.command_1), abs(phase.command_2)) for phase in phases
    )
    if not args.execute:
        _print_plan(args.test, phases)
        return
    if args.arm != ARM_TOKEN:
        parser.error(f"execution requires --arm {ARM_TOKEN}")
    if not args.operator_present:
        parser.error("execution requires --operator-present")
    if not args.ball_removed:
        parser.error("execution requires --ball-removed")
    if not 0.0 < args.max_command <= HARD_COMMAND_LIMIT:
        parser.error(f"--max-command must be in (0, {HARD_COMMAND_LIMIT}]")
    if planned_maximum > args.max_command:
        parser.error(
            f"plan reaches {planned_maximum}; explicitly allow it with "
            f"--max-command {planned_maximum:g}"
        )

    rclpy.init(args=ros_args)
    node = ActiveSysId(args, phases)
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
