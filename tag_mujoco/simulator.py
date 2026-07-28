"""Small simulation API used by verification and rendering scripts."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import mujoco
import numpy as np

try:
    from .maze_layout import load_layout
    from .model_builder import build_mjcf
except ImportError:
    from maze_layout import load_layout
    from model_builder import build_mjcf


class TagMazeSim:
    def __init__(
        self,
        layout: Dict[str, Any] | None = None,
        model_params: Dict[str, Any] | None = None,
    ):
        self.layout = layout or load_layout()
        self.model_params = model_params or {}
        self.xml = build_mjcf(self.layout, self.model_params)
        self.model = mujoco.MjModel.from_xml_string(self.xml)
        self.data = mujoco.MjData(self.model)
        self.board_body_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, "board"
        )
        self.ball_body_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, "ball"
        )
        self.ball_joint_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_JOINT, "ball_free"
        )
        self.tilt_x_joint_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_JOINT, "tilt_x"
        )
        self.tilt_y_joint_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_JOINT, "tilt_y"
        )
        self.ball_qpos_adr = int(self.model.jnt_qposadr[self.ball_joint_id])
        self.ball_qvel_adr = int(self.model.jnt_dofadr[self.ball_joint_id])
        self.linear_ball_damping_per_second = float(
            self.model_params.get("linear_ball_damping_per_second", 0.0)
        )
        self.tilt_x_qpos_adr = int(self.model.jnt_qposadr[self.tilt_x_joint_id])
        self.tilt_y_qpos_adr = int(self.model.jnt_qposadr[self.tilt_y_joint_id])
        self.reset()

    @property
    def board_size(self) -> Tuple[float, float]:
        return float(self.layout["board_width"]), float(self.layout["board_height"])

    @property
    def ball_radius(self) -> float:
        return float(self.layout["ball_radius"])

    def set_tilt(self, tilt_x: float, tilt_y: float) -> None:
        limit = math.radians(10.0)
        self.data.ctrl[:] = np.clip([tilt_x, tilt_y], -limit, limit)

    def board_to_world(self, xy: Iterable[float], z: float) -> np.ndarray:
        mujoco.mj_forward(self.model, self.data)
        xy = np.asarray(tuple(xy), dtype=np.float64)
        width, height = self.board_size
        local = np.array([xy[0] - width / 2.0, xy[1] - height / 2.0, z])
        rotation = self.data.xmat[self.board_body_id].reshape(3, 3)
        return self.data.xpos[self.board_body_id] + rotation @ local

    def reset(
        self,
        ball_xy: Iterable[float] | None = None,
        tilt: Tuple[float, float] = (0.0, 0.0),
        ball_velocity_xy: Iterable[float] = (0.0, 0.0),
        settle_steps: int = 30,
    ) -> None:
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[self.tilt_x_qpos_adr] = tilt[0]
        self.data.qpos[self.tilt_y_qpos_adr] = tilt[1]
        self.data.ctrl[:] = tilt
        mujoco.mj_forward(self.model, self.data)
        if ball_xy is None:
            ball_xy = self.layout["waypoints"][0]
        world = self.board_to_world(ball_xy, self.ball_radius + 0.0008)
        self.data.qpos[self.ball_qpos_adr : self.ball_qpos_adr + 3] = world
        self.data.qpos[self.ball_qpos_adr + 3 : self.ball_qpos_adr + 7] = [1, 0, 0, 0]
        self.data.qvel[self.ball_qvel_adr : self.ball_qvel_adr + 6] = 0
        velocity_board = np.asarray(tuple(ball_velocity_xy), dtype=np.float64)
        if velocity_board.shape != (2,):
            raise ValueError("ball_velocity_xy must contain exactly two values")
        rotation = self.data.xmat[self.board_body_id].reshape(3, 3)
        velocity_world = rotation @ np.array(
            [velocity_board[0], velocity_board[1], 0.0], dtype=np.float64
        )
        self.data.qvel[self.ball_qvel_adr : self.ball_qvel_adr + 3] = velocity_world
        mujoco.mj_forward(self.model, self.data)
        for _ in range(settle_steps):
            mujoco.mj_step(self.model, self.data)

    def step(self, steps: int = 1) -> None:
        for _ in range(steps):
            self.data.xfrc_applied[self.ball_body_id, :] = 0.0
            if self.linear_ball_damping_per_second > 0.0:
                rotation = self.data.xmat[self.board_body_id].reshape(3, 3)
                velocity_world = self.data.qvel[
                    self.ball_qvel_adr : self.ball_qvel_adr + 3
                ]
                velocity_board = rotation.T @ velocity_world
                velocity_board[2] = 0.0
                mass = float(self.model.body_mass[self.ball_body_id])
                damping_force = rotation @ (
                    -mass * self.linear_ball_damping_per_second * velocity_board
                )
                self.data.xfrc_applied[self.ball_body_id, :3] = damping_force
            mujoco.mj_step(self.model, self.data)

    def ball_world_position(self) -> np.ndarray:
        return self.data.xpos[self.ball_body_id].copy()

    def ball_board_position(self) -> np.ndarray:
        rotation = self.data.xmat[self.board_body_id].reshape(3, 3)
        local = rotation.T @ (
            self.data.xpos[self.ball_body_id] - self.data.xpos[self.board_body_id]
        )
        width, height = self.board_size
        return np.array([local[0] + width / 2.0, local[1] + height / 2.0, local[2]])

    def board_angles(self) -> np.ndarray:
        return np.array(
            [
                self.data.qpos[self.tilt_x_qpos_adr],
                self.data.qpos[self.tilt_y_qpos_adr],
            ],
            dtype=np.float64,
        )

    def render(self, width: int = 900, height: int = 800) -> np.ndarray:
        renderer = mujoco.Renderer(self.model, height=height, width=width)
        try:
            renderer.update_scene(self.data, camera="top")
            return renderer.render().copy()
        finally:
            renderer.close()

    def save_xml(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.xml, encoding="utf-8")
