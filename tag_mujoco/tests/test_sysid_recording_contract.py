"""Guard the recorder/fitter contract before a bench session depends on it.

`tag_sysid/test/test_fit_dynamics.py` already proves the fit *mathematics*
recovers synthetic damping, rolling resistance and restitution. It calls
`fit_free_roll` and `detect_impacts` with arrays and never touches a file, so it
cannot catch the failure that actually costs a session: the recorder writing a
CSV the fitter cannot read. That is only discovered after the marble has been
rolled, and it is unrecoverable without re-recording.

These tests exercise the file path end to end. They matter locally because the
`tag_sysid` suite cannot run on Windows at all -- `recorder.py` imports `rclpy`
and pytest is not installed -- so the contract is otherwise unverified until
someone is standing at the bench.

`STATE_FIELDS` is read out of the recorder source with `ast` rather than
imported, which keeps the coupling real without dragging in ROS.
"""

from __future__ import annotations

import ast
import csv
import importlib.util
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORDER = REPO_ROOT / "tag_sysid" / "tag_sysid" / "recorder.py"
FIT_DYNAMICS = REPO_ROOT / "tag_sysid" / "tag_sysid" / "fit_dynamics.py"

# Columns `fit_dynamics._read_states` requires. `source_time_ns` is optional in
# the sense that it falls back to `ros_time_ns`, but both names must exist.
REQUIRED_STATE_COLUMNS = (
    "ball_visible",
    "ros_time_ns",
    "source_time_ns",
    "x_b_m",
    "y_b_m",
    "alpha_rad",
    "beta_rad",
)


def _recorder_state_fields():
    """Read STATE_FIELDS from the recorder source without importing rclpy."""

    tree = ast.parse(RECORDER.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "STATE_FIELDS":
                return tuple(ast.literal_eval(node.value))
    raise AssertionError("STATE_FIELDS not found in recorder.py")


def _load_fit_dynamics():
    """Import fit_dynamics by path; it needs only numpy, not ROS."""

    spec = importlib.util.spec_from_file_location("_tag_fit_dynamics", FIT_DYNAMICS)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _synthetic_session(
    directory: Path,
    duration_seconds: float = 16.0,
    rate_hz: float = 45.0,
    damping: float = 0.6,
    resistance: float = 0.03,
    restitution: float = 0.5,
    source_time_mode: str = "always",
    source_age_seconds: float = 0.030,
    half_extent: float | None = None,
    fields=None,
):
    """Write a states.csv describing a damped free roll, optionally bouncing.

    Uses the recorder's own field list so a schema change on either side of the
    contract fails these tests rather than the session.

    `half_extent` of None means the ball never reaches a wall. That is the
    default deliberately: `local_kinematics` fits a centred quadratic over a
    0.18 s window, and a bounce inside that window is a velocity discontinuity
    it cannot represent, so contaminated samples enter the free-roll regression
    as large spurious accelerations. Identifying damping and rolling resistance
    therefore needs unobstructed rolling, while restitution needs the opposite.
    They are separate recordings, not one.
    """

    fields = tuple(fields or _recorder_state_fields())
    dt = 1.0 / rate_hz
    steps = int(duration_seconds * rate_hz)
    tilt_map = np.asarray([[0.4, 6.2], [-6.0, 0.3]])

    times = np.arange(steps, dtype=np.float64) * dt
    angles = np.column_stack(
        (
            0.022 + 0.010 * np.sin(0.7 * times),
            -0.016 + 0.011 * np.cos(times),
        )
    )
    velocity = np.zeros((steps, 2))
    position = np.zeros((steps, 2))
    velocity[0] = (0.030, -0.020)
    for index in range(1, steps):
        prior = velocity[index - 1]
        speed = max(float(np.linalg.norm(prior)), 1.0e-9)
        acceleration = (
            tilt_map @ angles[index - 1] - damping * prior - resistance * prior / speed
        )
        current = prior + acceleration * dt
        candidate = position[index - 1] + current * dt
        if half_extent is not None:
            for axis in range(2):
                if abs(candidate[axis]) > half_extent:
                    candidate[axis] = math.copysign(half_extent, candidate[axis])
                    current[axis] = -restitution * current[axis]
        velocity[index] = current
        position[index] = candidate

    base_ns = 1_700_000_000_000_000_000
    rows = []
    for index in range(steps):
        ros_ns = base_ns + int(times[index] * 1e9)
        source_ns = ros_ns - int(source_age_seconds * 1e9)
        if source_time_mode == "always":
            source_value = source_ns
        elif source_time_mode == "never":
            source_value = ""
        elif source_time_mode == "alternating":
            source_value = source_ns if index % 2 == 0 else ""
        else:  # pragma: no cover - guard against typos in a test parameter
            raise ValueError(f"unknown source_time_mode {source_time_mode!r}")
        row = {name: "" for name in fields}
        row.update(
            {
                "ros_time_ns": ros_ns,
                "monotonic_ns": ros_ns,
                "source_time_ns": source_value,
                "source_age_ns": int(source_age_seconds * 1e9) if source_value else "",
                "x_b_m": float(position[index, 0]),
                "y_b_m": float(position[index, 1]),
                "x_b_dot_mps": float(velocity[index, 0]),
                "y_b_dot_mps": float(velocity[index, 1]),
                "alpha_rad": float(angles[index, 0]),
                "beta_rad": float(angles[index, 1]),
                "ball_visible": 1,
            }
        )
        rows.append(row)

    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "states.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)
    return directory


class RecordingSchemaTests(unittest.TestCase):
    def test_recorder_writes_every_column_the_fitter_reads(self):
        """The contract itself, checked directly rather than inferred."""

        fields = _recorder_state_fields()
        for column in REQUIRED_STATE_COLUMNS:
            self.assertIn(
                column,
                fields,
                f"recorder STATE_FIELDS is missing {column!r}, which "
                "fit_dynamics._read_states requires",
            )

    def test_fitter_reads_a_recorder_shaped_session(self):
        module = _load_fit_dynamics()
        with tempfile.TemporaryDirectory() as workspace:
            session = _synthetic_session(Path(workspace) / "session")
            result = module.fit_session(session)
        self.assertGreaterEqual(result["visible_samples"], 200)
        self.assertGreater(result["free_roll"]["samples"], 200)
        self.assertGreater(result["free_roll"]["r2"], 0.25)
        self.assertTrue(result["quality_gate"]["free_roll_usable"])

    def test_invisible_samples_are_excluded(self):
        """`ball_visible` gating must drop rows rather than fit through them."""

        module = _load_fit_dynamics()
        fields = _recorder_state_fields()
        with tempfile.TemporaryDirectory() as workspace:
            session = _synthetic_session(Path(workspace) / "session")
            path = session / "states.csv"
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            for row in rows[:50]:
                row["ball_visible"] = 0
                row["x_b_m"] = "nan"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(fields))
                writer.writeheader()
                writer.writerows(rows)
            result = module.fit_session(session)
        self.assertEqual(result["visible_samples"], len(rows) - 50)


class TimestampBasisTests(unittest.TestCase):
    """`fit_session` reports `state_source_time_when_available`.

    "When available" is load-bearing. The recorder writes an empty
    `source_time_ns` whenever the estimator supplies no source stamp, and
    `_read_states` then silently falls back to `ros_time_ns`. Those two clocks
    differ by `source_age_ns`, so a recording where availability flickers has a
    time axis that jumps back and forth by that age -- and every velocity and
    acceleration in the fit is a numerical derivative of that axis.
    """

    def test_absent_source_time_falls_back_to_ros_time(self):
        module = _load_fit_dynamics()
        with tempfile.TemporaryDirectory() as workspace:
            session = _synthetic_session(
                Path(workspace) / "session", source_time_mode="never"
            )
            result = module.fit_session(session)
        self.assertTrue(result["quality_gate"]["free_roll_usable"])

    def test_flickering_source_time_degrades_the_fit(self):
        """Record the hazard quantitatively so the bench can avoid it.

        If this ever stops degrading the fit, the fallback has become
        harmless and the recording guidance can relax. Until then,
        `source_time_ns` must be populated on every row of a session used for
        dynamics identification.
        """

        module = _load_fit_dynamics()
        with tempfile.TemporaryDirectory() as workspace:
            consistent = module.fit_session(
                _synthetic_session(
                    Path(workspace) / "consistent", source_time_mode="always"
                )
            )
            mixed = module.fit_session(
                _synthetic_session(
                    Path(workspace) / "mixed", source_time_mode="alternating"
                )
            )
        self.assertGreater(consistent["free_roll"]["r2"], mixed["free_roll"]["r2"])
        self.assertGreater(
            mixed["free_roll"]["residual_rmse_mps2"],
            consistent["free_roll"]["residual_rmse_mps2"],
        )


class SessionLengthTests(unittest.TestCase):
    def test_short_session_fails_the_quality_gate(self):
        """How much data Block C actually needs, expressed as a test.

        The gate wants 200 moving samples. A 2 s recording still *produces*
        numbers -- it clears the 20-sample read floor and the 40-sample fit
        floor -- it simply fails the gate. That is the trap worth naming: a
        marginal session yields a plausible-looking damping and rolling
        resistance that must not be quoted, and only `quality_gate` says so.
        """

        module = _load_fit_dynamics()
        with tempfile.TemporaryDirectory() as workspace:
            result = module.fit_session(
                _synthetic_session(Path(workspace) / "short", duration_seconds=2.0)
            )
        self.assertFalse(result["quality_gate"]["free_roll_usable"])
        self.assertIn(
            "fewer than 200 moving samples", result["quality_gate"]["warnings"]
        )
        # The numbers exist regardless, which is exactly why the gate matters.
        self.assertIn("linear_damping_per_second", result["free_roll"])

    def test_free_roll_recovers_known_damping_and_resistance(self):
        """End to end through the file path, not just the array API."""

        module = _load_fit_dynamics()
        with tempfile.TemporaryDirectory() as workspace:
            result = module.fit_session(
                _synthetic_session(
                    Path(workspace) / "roll", damping=0.6, resistance=0.03
                )
            )
        self.assertAlmostEqual(
            result["free_roll"]["linear_damping_per_second"], 0.6, delta=0.25
        )
        self.assertAlmostEqual(
            result["free_roll"]["rolling_resistance_mps2"], 0.03, delta=0.02
        )

    def test_bouncing_session_yields_impacts_but_a_worse_roll_fit(self):
        """Why Block C needs two recordings rather than one.

        Wall contact is required for restitution and destructive for the
        free-roll regression, because a velocity discontinuity inside the
        0.18 s kinematics window enters the fit as a large false acceleration.
        """

        module = _load_fit_dynamics()
        with tempfile.TemporaryDirectory() as workspace:
            clean = module.fit_session(
                _synthetic_session(Path(workspace) / "clean", half_extent=None)
            )
            bouncing = module.fit_session(
                _synthetic_session(Path(workspace) / "bounce", half_extent=0.05)
            )
        self.assertGreater(bouncing["wall_impacts"]["count"], clean["wall_impacts"]["count"])
        self.assertGreater(clean["free_roll"]["r2"], bouncing["free_roll"]["r2"])


if __name__ == "__main__":
    unittest.main()
