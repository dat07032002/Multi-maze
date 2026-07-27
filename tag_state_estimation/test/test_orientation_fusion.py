import math

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from tag_state_estimation.core.orientation_fusion import (
    CameraImuOrientationFusion,
    board_xy_angles,
)


def _rotation(x=0.0, y=0.0, z=0.0):
    return Rotation.from_euler("xyz", [x, y, z], degrees=True)


def test_camera_mode_preserves_existing_behavior():
    camera = _rotation(x=4, y=-3).as_matrix()
    result = CameraImuOrientationFusion(mode="camera").update(camera)
    assert result.source == "camera"
    assert np.allclose(result.rotation, camera)


def test_alignment_removes_arbitrary_imu_reference_frame():
    fusion = CameraImuOrientationFusion(mode="imu")
    camera_initial = _rotation(x=2, y=-1, z=5)
    reference_offset = _rotation(x=15, y=7, z=-30)
    imu_initial = reference_offset.inv() * camera_initial
    fusion.update(camera_initial.as_matrix(), imu_initial.as_quat(), 0.01)

    camera_moved = _rotation(x=6, y=-4, z=5)
    imu_moved = reference_offset.inv() * camera_moved
    result = fusion.update(None, imu_moved.as_quat(), 0.01)

    assert result.source == "imu_fallback"
    assert np.allclose(result.rotation, camera_moved.as_matrix(), atol=1e-8)


def test_alignment_accounts_for_nonparallel_sensor_mount():
    mount = _rotation(x=0, y=0, z=90)
    imu_world_in_camera_world = _rotation(x=12, y=-8, z=20)
    fusion = CameraImuOrientationFusion(
        mode="imu", imu_mount_rpy_deg=(0, 0, 90)
    )

    camera_initial = _rotation(x=2, y=-1, z=3)
    imu_initial = Rotation.from_matrix(
        imu_world_in_camera_world.as_matrix().T
        @ camera_initial.as_matrix()
        @ mount.as_matrix()
    )
    fusion.update(camera_initial.as_matrix(), imu_initial.as_quat(), 0.0)

    camera_moved = _rotation(x=7, y=-5, z=3)
    imu_moved = Rotation.from_matrix(
        imu_world_in_camera_world.as_matrix().T
        @ camera_moved.as_matrix()
        @ mount.as_matrix()
    )
    result = fusion.update(None, imu_moved.as_quat(), 0.0)
    assert np.allclose(result.rotation, camera_moved.as_matrix(), atol=1e-8)


def test_stale_imu_falls_back_to_camera():
    fusion = CameraImuOrientationFusion(mode="fused", imu_timeout_sec=0.1)
    camera = _rotation(x=2).as_matrix()
    result = fusion.update(camera, _rotation().as_quat(), 0.2)
    assert result.source == "camera_imu_stale"
    assert np.allclose(result.rotation, camera)


def test_large_disagreement_uses_camera_without_learning_bad_alignment():
    fusion = CameraImuOrientationFusion(mode="fused", max_disagreement_deg=5)
    initial = _rotation()
    fusion.update(initial.as_matrix(), initial.as_quat(), 0.0)
    camera = _rotation(x=1)
    bad_imu = _rotation(x=20)
    result = fusion.update(camera.as_matrix(), bad_imu.as_quat(), 0.0)
    assert result.source == "camera_imu_disagreement"
    assert result.disagreement_deg > 5
    assert np.allclose(result.rotation, camera.as_matrix())


def test_angle_extraction_matches_plate_pose_convention():
    rotation = _rotation(x=5, y=-4).as_matrix()
    alpha, beta = board_xy_angles(rotation)
    assert math.degrees(alpha) == pytest.approx(5, abs=0.05)
    assert math.degrees(beta) == pytest.approx(-4, abs=0.05)
