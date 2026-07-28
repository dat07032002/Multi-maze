"""Approval-gated, single-pulse marble-dynamics measurement."""

from __future__ import annotations

import argparse
import json
import math

import rclpy

from .active import ActiveSysId, _plan_dict
from .marble_protocols import (
    MARBLE_COMMAND_LIMIT,
    build_marble_breakaway,
    build_marble_gentle_high,
    build_marble_high_breakaway,
    build_marble_pulse,
)
from .marble_safety import ConfirmedDisplacementGuard
from .profiles import PROFILES, get_profile, load_message_types
from .protocols import Phase


STANDARD_ARM_TOKEN = "START_MARBLE_SYSID_20"
HIGH_ARM_TOKEN = "START_MARBLE_SYSID_100"


class MarbleSysId(ActiveSysId):
    """Add marble visibility, position, and speed aborts to active sysid."""

    def __init__(self, *args, **kwargs):
        self.marble_failure = "no marble state received"
        self.missing_frames = 0
        self.start_position = None
        self.displacement_guard = ConfirmedDisplacementGuard(
            args[0].max_displacement_m,
            args[0].displacement_window_frames,
            args[0].displacement_confirm_frames,
        )
        super().__init__(*args, **kwargs)

    def _on_state(self, message) -> None:
        super()._on_state(message)
        values = (
            float(message.x_b),
            float(message.y_b),
            float(message.x_b_dot),
            float(message.y_b_dot),
        )
        if not all(math.isfinite(value) for value in values):
            self.missing_frames += 1
            if self.missing_frames > self.args.max_missing_frames:
                self.marble_failure = (
                    f"marble lost for {self.missing_frames} frames"
                )
            return

        self.missing_frames = 0
        x_b, y_b, x_dot, y_dot = values
        speed = math.hypot(x_dot, y_dot)
        if abs(x_b) > self.args.max_abs_x_m:
            self.marble_failure = (
                f"marble x={x_b:.4f}m exceeds {self.args.max_abs_x_m:.4f}m"
            )
        elif abs(y_b) > self.args.max_abs_y_m:
            self.marble_failure = (
                f"marble y={y_b:.4f}m exceeds {self.args.max_abs_y_m:.4f}m"
            )
        elif speed > self.args.max_speed_mps:
            self.marble_failure = (
                f"marble speed={speed:.3f}m/s exceeds "
                f"{self.args.max_speed_mps:.3f}m/s"
            )
        elif self.displacement_guard.update(x_b, y_b):
            self.marble_failure = (
                "confirmed marble displacement exceeds "
                f"{1000.0 * self.args.max_displacement_m:.1f}mm "
                f"(filtered={1000.0 * self.displacement_guard.filtered_distance_m:.1f}mm)"
            )
        else:
            self.marble_failure = None

    def validate_additional_preflight(self) -> None:
        if self.marble_failure:
            raise RuntimeError("marble preflight failed: " + self.marble_failure)
        speed = math.hypot(
            float(self.latest_state.x_b_dot),
            float(self.latest_state.y_b_dot),
        )
        if speed > self.args.max_start_speed_mps:
            raise RuntimeError(
                f"marble is not stationary ({speed:.3f}m/s); refusing to arm"
            )
        self.start_position = (
            float(self.latest_state.x_b),
            float(self.latest_state.y_b),
        )
        self.displacement_guard.reset(*self.start_position)

    def validate_additional_runtime(self) -> None:
        if self.marble_failure:
            raise RuntimeError("marble safety abort: " + self.marble_failure)

    def _publish(self, phase: Phase, enforce_state_safety: bool = True) -> None:
        if enforce_state_safety and self.marble_failure:
            raise RuntimeError("marble safety abort: " + self.marble_failure)
        super()._publish(phase, enforce_state_safety=enforce_state_safety)

    def _write_metadata(self, status: str) -> None:
        super()._write_metadata(status)
        path = self.output_dir / "metadata.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["marble_installed_confirmed"] = bool(self.args.marble_installed)
        data["clear_start_confirmed"] = bool(self.args.start_clear)
        data["marble_safety"] = {
            "max_command": max(
                max(abs(phase.command_1), abs(phase.command_2))
                for phase in self.phases
            ),
            "max_abs_x_m": self.args.max_abs_x_m,
            "max_abs_y_m": self.args.max_abs_y_m,
            "max_speed_mps": self.args.max_speed_mps,
            "max_start_speed_mps": self.args.max_start_speed_mps,
            "max_missing_frames": self.args.max_missing_frames,
            "max_displacement_m": self.args.max_displacement_m,
            "displacement_window_frames": self.args.displacement_window_frames,
            "displacement_confirm_frames": self.args.displacement_confirm_frames,
        }
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axis", required=True, type=int, choices=(1, 2))
    parser.add_argument("--direction", required=True, type=int, choices=(-1, 1))
    parser.add_argument(
        "--mode",
        choices=("pulse", "breakaway", "high-breakaway", "gentle-high"),
        default="pulse",
    )
    parser.add_argument("--output-root", default="~/tag_sysid_logs/marble")
    parser.add_argument(
        "--interface-profile", choices=tuple(sorted(PROFILES)), default="tag"
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--arm", default="")
    parser.add_argument("--operator-present", action="store_true")
    parser.add_argument("--marble-installed", action="store_true")
    parser.add_argument("--start-clear", action="store_true")
    parser.add_argument("--max-abs-x-m", type=float, default=0.120)
    parser.add_argument("--max-abs-y-m", type=float, default=0.105)
    parser.add_argument("--max-speed-mps", type=float, default=0.25)
    parser.add_argument("--max-start-speed-mps", type=float, default=0.01)
    parser.add_argument("--max-missing-frames", type=int, default=3)
    parser.add_argument("--max-displacement-m", type=float, default=0.003)
    parser.add_argument("--displacement-window-frames", type=int, default=5)
    parser.add_argument("--displacement-confirm-frames", type=int, default=3)
    return parser


def _print_plan(args, phases, profile) -> None:
    print(
        f"Test: marble {args.mode}, axis {args.axis}, "
        f"direction {args.direction:+d}"
    )
    print(f"Phases: {len(phases)}")
    print(f"Planned duration: {sum(p.duration_seconds for p in phases):.1f} seconds")
    maximum = max(
        max(abs(phase.command_1), abs(phase.command_2)) for phase in phases
    )
    print(f"Maximum absolute command: {maximum:.1f}")
    print(f"State topic: {profile.state_topic}")
    print(f"Command topic: {profile.command_topic}")
    print("Dry run only: no ROS node was created and no command was published.")
    print(json.dumps([_plan_dict(phase) for phase in phases], indent=2))


def main(argv=None) -> None:
    parser = _parser()
    args, ros_args = parser.parse_known_args(argv)
    profile = get_profile(args.interface_profile)
    builders = {
        "pulse": build_marble_pulse,
        "breakaway": build_marble_breakaway,
        "high-breakaway": build_marble_high_breakaway,
        "gentle-high": build_marble_gentle_high,
    }
    phases = builders[args.mode](args.axis, args.direction)
    if not args.execute:
        _print_plan(args, phases, profile)
        return
    arm_token = (
        HIGH_ARM_TOKEN
        if args.mode in {"high-breakaway", "gentle-high"}
        else STANDARD_ARM_TOKEN
    )
    if args.arm != arm_token:
        parser.error(f"execution requires --arm {arm_token}")
    if not args.operator_present:
        parser.error("execution requires --operator-present")
    if not args.marble_installed:
        parser.error("execution requires --marble-installed")
    if not args.start_clear:
        parser.error("execution requires --start-clear")

    args.test = (
        f"marble_{args.mode}_axis{args.axis}_"
        f"{'pos' if args.direction > 0 else 'neg'}"
    )
    args.command_scale = 1.0
    args.max_board_angle_deg = 15.0
    args.max_angle_excursion_deg = 2.0
    args.baseline_relative_angle_safety = True
    args.baseline_seconds = 1.0
    args.state_timeout = 10.0
    args.runtime_state_timeout = 0.25
    args.ball_removed = False

    state_type, command_type = load_message_types(profile)
    rclpy.init(args=ros_args)
    node = MarbleSysId(args, phases, profile, state_type, command_type)
    failure = None
    try:
        node.preflight()
        node.run_protocol()
    except KeyboardInterrupt:
        node.get_logger().warning("operator interrupt; requesting home")
        failure = "operator_interrupt"
    except Exception as exc:
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
