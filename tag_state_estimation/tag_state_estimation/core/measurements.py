# import sys
# sys.path.insert(0, 'G:/RA_IDSC_current/01_Source/tag')

import cv2
import numpy as np

from tag_state_estimation.ai_marble_common import OnnxMarbleDetector
from tag_state_estimation.core.detection import Detector, DetectorFixedPts
from tag_state_estimation.core.hybrid_ball import HybridBallTracker
from tag_state_estimation.core.plate_pose import PlatePoseEstimator
from tag_state_estimation.utils.anim_3d import Anim3d
from tag_state_estimation.utils.divers import init_win_subimages


class Measurements:
    def __init__(
        self,
        markers,
        do_anim_3d=True,
        viewpoint="side",
        show_subimages_detector=False,
        acceleration_backend="cpu",
        ai_mode="off",
        ai_model_path=None,
        ai_backend="cpu",
        ai_confidence_threshold=0.90,
        ai_check_every_n_frames=3,
        ai_valid_roi=(0.25, 0.15, 0.72, 0.80),
        ai_agreement_radius_px=12.0,
        ai_max_reacquire_jump_px=25.0,
        ai_occlusion_grace_frames=90,
        ai_reacquire_confirm_frames=3,
        ai_fusion_weight=0.5,
    ):
        self.acceleration_backend = acceleration_backend
        self.detector = Detector(
            markers[4:],
            show_subimages=show_subimages_detector,
            acceleration_backend=acceleration_backend,
        )
        self.detector_fixed_points = DetectorFixedPts(
            markers[:4],
            show_subimages=show_subimages_detector,
            acceleration_backend=acceleration_backend,
        )
        self.plate_pose = PlatePoseEstimator()

        self.ai_mode = str(ai_mode).lower()
        if self.ai_mode not in {"off", "shadow", "hybrid"}:
            raise ValueError(
                f"ai_mode must be off, shadow, or hybrid; got {self.ai_mode!r}"
            )
        self.ai_check_every_n_frames = max(1, int(ai_check_every_n_frames))
        self.ai_frame_count = 0
        self.ai_detector = None
        if self.ai_mode != "off":
            if not ai_model_path:
                raise ValueError("ai_model_path is required when ai_mode is not off")
            self.ai_detector = OnnxMarbleDetector(
                ai_model_path,
                confidence_threshold=float(ai_confidence_threshold),
                backend=str(ai_backend),
                valid_roi=tuple(ai_valid_roi),
            )
        self.hybrid_tracker = HybridBallTracker(
            agreement_radius_px=ai_agreement_radius_px,
            max_reacquire_jump_px=ai_max_reacquire_jump_px,
            occlusion_grace_frames=ai_occlusion_grace_frames,
            far_reacquire_confirm_frames=ai_reacquire_confirm_frames,
            ai_fusion_weight=ai_fusion_weight,
        )
        self.ball_source = "hsv" if self.ai_mode == "off" else "initializing"
        self.ai_confidence = np.nan
        self.detection_disagreement_px = np.nan
        self.ai_inference_ms = 0.0

        self.plate_angles = (None, None)
        self.ball_pos = None
        self.ball_img_coords = None
        self.ball_subimg = None

        if do_anim_3d:
            if viewpoint == "side":
                self.anim_3d_side = Anim3d(viewpoint="side")
                self.anim_3d_top = None
            if viewpoint == "top":
                self.anim_3d_top = Anim3d(viewpoint="top")
                self.anim_3d_side = None
            if viewpoint == "topandside":
                self.anim_3d_side = Anim3d(viewpoint="side")
                self.anim_3d_top = Anim3d(viewpoint="top")
        else:
            self.anim_3d_top = None
            self.anim_3d_side = None

        if show_subimages_detector:
            init_win_subimages()

    def process_frame(
        self,
        frame,
        get_ball_subimg=False,
    ):
        """
        Process the frame to compute the angles of the plate and the position of the ball in the maze frame {m}.

        Args :
            frame: np.ndarray, dim: (400, 640)
        """
        ai_frame = frame.copy() if self.ai_detector is not None else None
        if self.plate_pose.T__W_C is None:
            self.camera_localization(frame)
            if self.anim_3d_top is not None:
                self.anim_3d_top.init_3d_anim(self.plate_pose.T__W_C)
            if self.anim_3d_side is not None:
                self.anim_3d_side.init_3d_anim(self.plate_pose.T__W_C)

        if self.acceleration_backend == "opencl":
            frame_u = cv2.UMat(frame)
            frame = cv2.bitwise_and(frame_u, frame_u, mask=self.mask_u).get()
        else:
            frame = cv2.bitwise_and(frame, frame, mask=self.mask)
        if get_ball_subimg:
            frame_copy = frame.copy()

        run_ai = self.ai_detector is not None and (
            self.ai_mode == "hybrid"
            or self.ai_frame_count % self.ai_check_every_n_frames == 0
        )
        ai_position = None
        if run_ai:
            import time

            started = time.perf_counter()
            ai_detection = self.ai_detector.detect(ai_frame)
            self.ai_inference_ms = 1000.0 * (time.perf_counter() - started)
            self.ai_confidence = ai_detection.confidence
            if ai_detection.visible:
                # Classical coordinates are [row, column]; AI coordinates are [x, y].
                ai_position = np.array(
                    [ai_detection.y_px, ai_detection.x_px], dtype=np.float32
                )
        self.ai_frame_count += 1

        # A full-board HSV search can prefer a large, static blue maze feature
        # over the smaller marble.  During hybrid reacquisition, use the AI
        # result only to center the normal 80x80 HSV crop.  The proposal still
        # has to pass the independent HSV detector and the agreement/temporal
        # gates below before it can become a published measurement.
        if (
            self.ai_mode == "hybrid"
            and ai_position is not None
            and (
                not self.detector.is_ball_found
                or self.hybrid_tracker.missing_frames
                >= self.detector.BALL_MISS_THRESHOLD
            )
        ):
            self.detector.reset_ball_tracking()
            self.detector.ball_pos = ai_position.copy()
            self.detector.is_ball_found = True

        corners_img_coords, hsv_ball_img_coords = self.detector.process_frame(frame)
        hsv_measured = (
            hsv_ball_img_coords
            if self.detector.last_ball_detection_found
            else None
        )
        ball_img_coords = hsv_ball_img_coords
        self.detection_disagreement_px = np.nan

        if self.ai_mode == "hybrid":
            result = self.hybrid_tracker.update(hsv_measured, ai_position)
            ball_img_coords = result.measurement
            self.ball_source = result.source
            self.detection_disagreement_px = result.disagreement_px
            if np.all(np.isfinite(ball_img_coords)):
                # Let the HSV crop follow an AI-authoritative accepted position.
                self.detector.ball_pos = ball_img_coords.copy()
                self.detector.is_ball_found = True
        else:
            if np.all(np.isfinite(hsv_ball_img_coords)):
                self.ball_source = (
                    "hsv"
                    if self.detector.last_ball_detection_found
                    else "hsv_hold"
                )
            else:
                self.ball_source = "lost"
            if ai_position is not None and np.all(np.isfinite(hsv_ball_img_coords)):
                self.detection_disagreement_px = float(
                    np.linalg.norm(ai_position - hsv_ball_img_coords)
                )

        raw_pts = np.zeros((5, 2))
        raw_pts[:4, :] = corners_img_coords
        raw_pts[4, :] = ball_img_coords
        undist_pts = self.plate_pose.undistort_points(raw_pts)  # (x,y)
        corners_undist = undist_pts[:4, :]
        ball_undist = undist_pts[4, :]

        alpha, beta = self.plate_pose.estimate_anglesXY(corners_undist)
        self.plate_angles = (alpha, beta)
        self.ball_pos = self.ball_pos_backproject(
            ball_undist, self.plate_pose.K, self.plate_pose.T__C_M
        )
        self.ball_img_coords = ball_img_coords
        if get_ball_subimg:  # TODO: make function
            if np.isnan(self.ball_pos[0]):
                self.ball_subimg = np.zeros((64, 64, 3), dtype=np.uint8)
            else:  # TODO clean up and optimize
                points_board = np.zeros((64 * 64, 4))
                points_board[:, -1] = 1.0
                points_board[:, :2] = (
                    1.0e-3 * np.mgrid[-32:32, -32:32][::-1].reshape(2, -1).transpose()
                )
                points_board[:, 1] *= -1
                points_board[:, :3] += self.ball_pos
                points_cam = (self.plate_pose.T__C_M @ points_board.T).T[:, :3]
                points_cam[:, :2] = points_cam[:, [1, 0]]
                points_cam[:, 2] *= -1
                points_cam = self.plate_pose.o.world2cam(points_cam)
                points_cam = points_cam.reshape(64, 64, 2).astype(np.float32)
                self.ball_subimg = cv2.remap(
                    frame_copy, points_cam[..., 1], points_cam[..., 0], cv2.INTER_LINEAR
                )

        if self.anim_3d_top is not None:
            self.update_3d_anim_top()
        if self.anim_3d_side is not None:
            self.update_3d_anim_side()

    def get_ball_subimg(self):
        return self.ball_subimg

    def get_ball_coordinates(self):
        """
        Return the pixel coordinates of the ball in the image frame {m}.

        Returns:
            ball_pos: np.ndarray, dim: (2,)
                    2d position of the ball in the image frame.

        """
        return self.ball_img_coords

    def get_ball_position_in_maze(self):
        """
        Return the position of the ball in the maze frame {m}.

        Returns:
            ball_pos: np.ndarray, dim: (3,)
                    3d position of the ball in the maze frame {m}.
                    note: the z-coordinate of the ball in maze frame is fixed and known
                    by assumption of constant contact with the maze: z__m_b = ball_radius.

        """
        return self.ball_pos

    def get_plate_pose(self):
        """
        Return the angles (Euler YXZ) that describe the orientation of the maze frame {m} wrt the world frame {w}.

        Returns:
            ball_pos: Tuple(float, float)
                      (alpha, beta) around X and Y respectively
        """
        return self.plate_angles

    def camera_localization(self, frame):
        """
        Compute the pose of the camera {c} wrt to the world frame {w} : T__W_C.
        """
        fix_pts = self.detector_fixed_points.detect_corners(frame)
        self.detector.fixed_corners = fix_pts
        self.plate_pose.camera_localization(fix_pts)
        self.create_mask(frame)

    def create_mask(self, frame):
        h, w = frame.shape[:2]
        coords = np.mgrid[0:h, 0:w].transpose(1, 2, 0).reshape(-1, 2)
        camera_points = self.plate_pose.o.cam2world(coords)[:, [1, 0, 2]]
        camera_points[:, 2] *= -1
        world_vec = (self.plate_pose.T__W_C[:3, :3] @ camera_points.T).T
        world_vec = world_vec / world_vec[:, 2:]
        world_points = (
            world_vec * (-self.plate_pose.T__W_C[2, -1])
            + self.plate_pose.T__W_C[:3, -1]
        )
        mask = (
            (world_points[:, 0] >= -(2.0 * self.plate_pose.r))
            & (
                world_points[:, 0]
                <= self.plate_pose.L_EXT_INT_X + 2.0 * self.plate_pose.r
            )
            & (world_points[:, 1] >= -(2.0 * self.plate_pose.r))
            & (
                world_points[:, 1]
                <= self.plate_pose.L_EXT_INT_Y + 2.0 * self.plate_pose.r
            )
        )
        self.mask = 255 * mask.reshape(h, w, 1).astype(np.uint8)
        self.mask_u = (
            cv2.UMat(self.mask) if self.acceleration_backend == "opencl" else None
        )

    def ball_pos_backproject(self, ball_undist, K, T__C_M):
        """
        Compute the 3d position of the ball in the maze frame {m}.
        Returns:
            x_M: np.ndarray, dim: (3,)
                 3d position of the ball in the maze frame {m}.
                 note: the z-coordinate of the ball in maze frame is fixed and known
                 by assumption of constant contact with the maze: z__m_b = ball_radius.
        """
        if np.any(np.isnan(ball_undist)):
            return np.array([np.nan, np.nan, np.nan])
        d = PlatePoseEstimator.R_BALL
        v, u = ball_undist
        H = K @ T__C_M[:3, :]
        h_11, h_12, h_13, h_14 = H[0, :]
        h_21, h_22, h_23, h_24 = H[1, :]
        h_31, h_32, h_33, h_34 = H[2, :]
        A = np.array(
            [[u * h_31 - h_11, u * h_32 - h_12], [v * h_31 - h_21, v * h_32 - h_22]]
        )
        b = np.array(
            [
                d * h_13 + h_14 - d * u * h_33 - u * h_34,
                d * h_23 + h_24 - d * v * h_33 - v * h_34,
            ]
        )
        x = np.linalg.solve(A, b)
        x_M = np.array([x[0], x[1], PlatePoseEstimator.R_BALL])
        return x_M

    def update_3d_anim_top(self):
        self.anim_3d_top.B__W = (
            self.plate_pose.T__W_M @ np.hstack((self.ball_pos, np.array([1])))
        )[:-1]
        self.anim_3d_top.maze_corners__W = self.plate_pose.estimate_maze_corners__W()
        self.anim_3d_top.update_anim()

    def update_3d_anim_side(self):
        self.anim_3d_side.B__W = (
            self.plate_pose.T__W_M @ np.hstack((self.ball_pos, np.array([1])))
        )[:-1]
        self.anim_3d_side.maze_corners__W = self.plate_pose.estimate_maze_corners__W()
        self.anim_3d_side.update_anim()
