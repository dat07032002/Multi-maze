"""Line protocol shared by the ESP32 BNO086 bridge and ROS node."""

from __future__ import annotations

from dataclasses import dataclass
import json

import numpy as np


@dataclass(frozen=True)
class Bno086Sample:
    """One decoded BNO086 report in SI units."""

    quaternion_xyzw: np.ndarray
    angular_velocity_xyz: np.ndarray
    linear_acceleration_xyz: np.ndarray
    accuracy: int


def parse_bno086_line(line: str) -> Bno086Sample:
    """Parse explicit JSON or ``TAG_IMU`` CSV without guessing field order."""
    text = line.strip()
    if not text:
        raise ValueError("empty IMU line")

    if text.startswith("{"):
        payload = json.loads(text)
        values = [
            payload[name]
            for name in ("qx", "qy", "qz", "qw", "gx", "gy", "gz",
                         "ax", "ay", "az")
        ]
        accuracy = int(payload.get("accuracy", -1))
    else:
        fields = text.split(",")
        if len(fields) != 12 or fields[0] != "TAG_IMU":
            raise ValueError(
                "expected TAG_IMU,qx,qy,qz,qw,gx,gy,gz,"
                "ax,ay,az,accuracy"
            )
        values = [float(value) for value in fields[1:11]]
        accuracy = int(fields[11])

    numeric = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(numeric)):
        raise ValueError("IMU sample contains non-finite values")
    quaternion = numeric[:4]
    norm = float(np.linalg.norm(quaternion))
    if norm < 0.5:
        raise ValueError("IMU quaternion norm is invalid")
    if accuracy not in {-1, 0, 1, 2, 3}:
        raise ValueError("BNO086 accuracy must be -1 or 0..3")
    return Bno086Sample(
        quaternion_xyzw=quaternion / norm,
        angular_velocity_xyz=numeric[4:7],
        linear_acceleration_xyz=numeric[7:10],
        accuracy=accuracy,
    )
