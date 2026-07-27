"""Camera and IMU orientation alignment and guarded fusion."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.spatial.transform import Rotation


@dataclass(frozen=True)
class OrientationFusionResult:
    """Orientation selected for one camera frame."""

    rotation: np.ndarray | None
    source: str
    disagreement_deg: float
    imu_fresh: bool
    aligned: bool


def board_xy_angles(rotation: np.ndarray) -> tuple[float, float]:
    """Return the estimator's internal X and Y board angles in radians."""
    matrix = np.asarray(rotation, dtype=float)
    alpha = math.asin(float(np.clip(-matrix[1, 2], -1.0, 1.0)))
    beta = math.atan2(float(matrix[0, 2]), float(matrix[2, 2]))
    return alpha, beta


def _interpolate_rotation(
    first: np.ndarray, second: np.ndarray, weight: float
):
    """Move ``first`` toward ``second`` along the shortest rotation."""
    delta = Rotation.from_matrix(second @ first.T)
    correction = Rotation.from_rotvec(weight * delta.as_rotvec()).as_matrix()
    return correction @ first


class CameraImuOrientationFusion:
    """Map BNO086 orientation into camera world and fuse it safely.

    ROS ``sensor_msgs/Imu`` quaternions represent the sensor frame orientation
    in an external reference frame.  A simultaneous valid camera pose supplies
    the otherwise unknown fixed mapping between that reference and TAG world.
    """

    MODES = {"camera", "imu", "fused"}

    def __init__(
        self,
        mode: str = "camera",
        imu_timeout_sec: float = 0.10,
        camera_correction_gain: float = 0.05,
        max_disagreement_deg: float = 8.0,
        imu_mount_rpy_deg=(0.0, 0.0, 0.0),
    ) -> None:
        """Configure freshness, alignment and camera correction gates."""
        self.mode = str(mode).lower()
        if self.mode not in self.MODES:
            raise ValueError(f"mode must be one of {sorted(self.MODES)}")
        if not 0.0 < imu_timeout_sec <= 2.0:
            raise ValueError("imu_timeout_sec must be in (0, 2]")
        if not 0.0 <= camera_correction_gain <= 1.0:
            raise ValueError("camera_correction_gain must be in [0, 1]")
        if not 0.0 < max_disagreement_deg <= 45.0:
            raise ValueError("max_disagreement_deg must be in (0, 45]")

        self.imu_timeout_sec = float(imu_timeout_sec)
        self.camera_correction_gain = float(camera_correction_gain)
        self.max_disagreement_deg = float(max_disagreement_deg)
        mount_rpy = np.asarray(imu_mount_rpy_deg, dtype=float)
        if mount_rpy.shape != (3,) or not np.all(np.isfinite(mount_rpy)):
            raise ValueError(
                "imu_mount_rpy_deg must contain three finite values"
            )
        # R_M_S maps vectors from the physical sensor frame into the board
        # frame. Identity means the marked sensor axes are mounted parallel to
        # the board axes.
        self._board_from_sensor = Rotation.from_euler(
            "xyz", mount_rpy, degrees=True
        ).as_matrix()
        self._camera_world_from_imu_world = None

    @property
    def aligned(self) -> bool:
        """Return whether a simultaneous camera/IMU sample set alignment."""
        return self._camera_world_from_imu_world is not None

    def reset_alignment(self) -> None:
        """Require a new simultaneous camera/IMU alignment sample."""
        self._camera_world_from_imu_world = None

    @staticmethod
    def _imu_rotation(quaternion_xyzw):
        if quaternion_xyzw is None:
            return None
        quaternion = np.asarray(quaternion_xyzw, dtype=float)
        if quaternion.shape != (4,) or not np.all(np.isfinite(quaternion)):
            return None
        norm = float(np.linalg.norm(quaternion))
        if norm < 0.5:
            return None
        return Rotation.from_quat(quaternion / norm).as_matrix()

    def update(
        self,
        camera_rotation,
        imu_quaternion_xyzw=None,
        imu_age_sec=math.inf,
    ) -> OrientationFusionResult:
        """Select orientation using the configured mode and freshness gate."""
        camera_valid = camera_rotation is not None and np.all(
            np.isfinite(camera_rotation)
        )
        camera = (
            np.asarray(camera_rotation, dtype=float)
            if camera_valid
            else None
        )
        imu = self._imu_rotation(imu_quaternion_xyzw)
        imu_fresh = (
            imu is not None
            and math.isfinite(float(imu_age_sec))
            and 0.0 <= float(imu_age_sec) <= self.imu_timeout_sec
        )

        if self.mode == "camera":
            return OrientationFusionResult(
                camera, "camera" if camera_valid else "lost_camera",
                math.nan, imu_fresh, self.aligned
            )

        if camera_valid and imu_fresh and not self.aligned:
            self._camera_world_from_imu_world = (
                camera @ self._board_from_sensor @ imu.T
            )

        if not imu_fresh or not self.aligned:
            source = (
                "camera_imu_stale"
                if camera_valid
                else "lost_imu_unaligned"
            )
            return OrientationFusionResult(
                camera, source, math.nan, imu_fresh, self.aligned
            )

        mapped_imu = (
            self._camera_world_from_imu_world
            @ imu
            @ self._board_from_sensor.T
        )
        disagreement = math.nan
        if camera_valid:
            disagreement = math.degrees(
                Rotation.from_matrix(camera @ mapped_imu.T).magnitude()
            )
            if disagreement > self.max_disagreement_deg:
                return OrientationFusionResult(
                    camera,
                    "camera_imu_disagreement",
                    disagreement,
                    True,
                    True,
                )

            if self.mode == "fused":
                desired_mapping = camera @ self._board_from_sensor @ imu.T
                self._camera_world_from_imu_world = _interpolate_rotation(
                    self._camera_world_from_imu_world,
                    desired_mapping,
                    self.camera_correction_gain,
                )
                mapped_imu = (
                    self._camera_world_from_imu_world
                    @ imu
                    @ self._board_from_sensor.T
                )
                source = "fused"
            else:
                source = "imu"
        else:
            source = "imu_fallback"

        return OrientationFusionResult(
            mapped_imu, source, disagreement, True, True
        )
