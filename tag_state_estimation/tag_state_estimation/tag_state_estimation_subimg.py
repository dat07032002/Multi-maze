#!usr/bin/env python3

import time
import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np
from scipy.spatial.transform import Rotation
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import Float32, String
from ament_index_python.packages import get_package_share_directory
from tf2_ros import TransformBroadcaster
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
from tag_state_estimation.core.estimation_pipeline import EstimationPipeline
from tag_state_estimation.core.opencv_acceleration import (
    configure_opencv_acceleration,
)
from tag_state_estimation.core.pose_continuity import (
    PoseContinuityGate,
    apply_published_angle_zero,
)
from tag_interfaces.msg import StateEstimate, StateEstimateSub


class ImageSubscriber(Node):
    def __init__(self, skip=1):
        super().__init__("tag_state_estimation")
        self.declare_parameter("process_every_n", skip)
        self.declare_parameter("pipeline_fps", 55.0)
        self.declare_parameter("print_measurements", False)
        self.declare_parameter("show_image", False)
        self.declare_parameter("use_gpu", False)
        self.declare_parameter("gpu_backend", "auto")
        self.declare_parameter("gpu_device_id", 0)
        self.declare_parameter("require_gpu", False)
        self.declare_parameter("playable_width", 0.259)
        self.declare_parameter("playable_height", 0.229)
        # Tolerance ADDED beyond the nominal board edge. The marble legitimately
        # reaches the board edge (~half the playable size), and the board tilts
        # during play, which shifts the estimated position by a few mm. A small
        # negative/zero tolerance rejected valid edge marbles as "outside" and
        # published NaN, so the marble looked lost near the top/bottom. Expand
        # the accepted region instead of shrinking it.
        self.declare_parameter("playable_edge_tolerance", 0.015)
        self.declare_parameter("pose_max_abs_deg", 20.0)
        self.declare_parameter("pose_max_step_deg", 3.0)
        self.declare_parameter("pose_reject_hold_frames", 2)
        self.declare_parameter("pose_zero_alpha_deg", 0.0)
        self.declare_parameter("pose_zero_beta_deg", 0.0)
        self.declare_parameter("ai_mode", "off")
        self.declare_parameter("ai_model_path", "")
        self.declare_parameter("ai_backend", "cpu")
        self.declare_parameter("ai_confidence_threshold", 0.90)
        self.declare_parameter("ai_check_every_n_frames", 3)
        self.declare_parameter("ai_roi_x_min", 0.25)
        self.declare_parameter("ai_roi_y_min", 0.15)
        self.declare_parameter("ai_roi_x_max", 0.72)
        self.declare_parameter("ai_roi_y_max", 0.80)
        self.declare_parameter("ai_agreement_radius_px", 12.0)
        self.declare_parameter("ai_max_reacquire_jump_px", 25.0)
        self.declare_parameter("ai_occlusion_grace_frames", 90)
        self.declare_parameter("ai_reacquire_confirm_frames", 3)
        self.declare_parameter("ai_max_prediction_std_m", 0.03)

        self.skip = max(1, int(self.get_parameter("process_every_n").value))
        self.pipeline_fps = float(self.get_parameter("pipeline_fps").value)
        self.print_measurements = bool(self.get_parameter("print_measurements").value)
        self.show_image = bool(self.get_parameter("show_image").value)
        self.use_gpu = bool(self.get_parameter("use_gpu").value)
        self.gpu_backend = str(self.get_parameter("gpu_backend").value)
        self.gpu_device_id = int(self.get_parameter("gpu_device_id").value)
        self.require_gpu = bool(self.get_parameter("require_gpu").value)
        playable_width = float(self.get_parameter("playable_width").value)
        playable_height = float(self.get_parameter("playable_height").value)
        edge_tolerance = max(
            0.0, float(self.get_parameter("playable_edge_tolerance").value)
        )
        self.playable_half_x = playable_width / 2.0 + edge_tolerance
        self.playable_half_y = playable_height / 2.0 + edge_tolerance
        self.pose_gate = PoseContinuityGate(
            max_abs_deg=float(self.get_parameter("pose_max_abs_deg").value),
            max_step_deg=float(self.get_parameter("pose_max_step_deg").value),
            hold_frames=int(
                self.get_parameter("pose_reject_hold_frames").value
            ),
        )
        self.pose_zero_alpha_deg = float(
            self.get_parameter("pose_zero_alpha_deg").value
        )
        self.pose_zero_beta_deg = float(
            self.get_parameter("pose_zero_beta_deg").value
        )
        self.pose_rejection_active = False
        self.ai_mode = str(self.get_parameter("ai_mode").value).lower()
        self.ai_model_path = str(self.get_parameter("ai_model_path").value)
        if self.ai_mode != "off" and not self.ai_model_path:
            self.ai_model_path = os.path.join(
                get_package_share_directory("tag_state_estimation"),
                "models",
                "marble_detector.onnx",
            )

        self.acceleration_backend, acceleration_msg = configure_opencv_acceleration(
            self.use_gpu,
            self.gpu_backend,
            self.gpu_device_id,
            self.require_gpu,
        )
        self.get_logger().info(acceleration_msg)

        self.subscription = self.create_subscription(
            Image, "tag_camera/image", self.listener_callback, 1
        )
        self.publisher_ = self.create_publisher(
            StateEstimateSub, "tag_state_estimation/estimate_subimg", 1
        )
        self.state_publisher_ = self.create_publisher(
            StateEstimate, "tag_state_estimation/estimate", 1
        )
        self.ball_source_publisher = self.create_publisher(
            String, "tag_state_estimation/ball_source", 10
        )
        self.ai_confidence_publisher = self.create_publisher(
            Float32, "tag_state_estimation/ai_confidence", 10
        )
        self.ai_disagreement_publisher = self.create_publisher(
            Float32, "tag_state_estimation/detection_disagreement_px", 10
        )
        self.ai_inference_publisher = self.create_publisher(
            Float32, "tag_state_estimation/ai_inference_ms", 10
        )
        self.tf_static_broadcaster = StaticTransformBroadcaster(self)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.get_logger().info("Image subscriber has been initialized.")
        self.br = CvBridge()
        self.estimation_pipeline = EstimationPipeline(
            fps=self.pipeline_fps,
            estimator="KF",  #  "FiniteDiff",  "KF", "KFBias"
            print_measurements=self.print_measurements,
            show_image=self.show_image,
            do_anim_3d=False,
            viewpoint="top",  # 'top', 'side', 'topandside'
            show_subimages_detector=False,
            acceleration_backend=self.acceleration_backend,
            ai_mode=self.ai_mode,
            ai_model_path=self.ai_model_path,
            ai_backend=str(self.get_parameter("ai_backend").value),
            ai_confidence_threshold=float(
                self.get_parameter("ai_confidence_threshold").value
            ),
            ai_check_every_n_frames=int(
                self.get_parameter("ai_check_every_n_frames").value
            ),
            ai_valid_roi=(
                float(self.get_parameter("ai_roi_x_min").value),
                float(self.get_parameter("ai_roi_y_min").value),
                float(self.get_parameter("ai_roi_x_max").value),
                float(self.get_parameter("ai_roi_y_max").value),
            ),
            ai_agreement_radius_px=float(
                self.get_parameter("ai_agreement_radius_px").value
            ),
            ai_max_reacquire_jump_px=float(
                self.get_parameter("ai_max_reacquire_jump_px").value
            ),
            ai_occlusion_grace_frames=int(
                self.get_parameter("ai_occlusion_grace_frames").value
            ),
            ai_reacquire_confirm_frames=int(
                self.get_parameter("ai_reacquire_confirm_frames").value
            ),
            ai_max_prediction_std_m=float(
                self.get_parameter("ai_max_prediction_std_m").value
            ),
        )
        self.get_logger().info(
            f"Marble detector mode={self.ai_mode}; "
            f"model={self.ai_model_path or 'disabled'}"
        )
        self.last_valid_ball_pixel = None
        self.outside_candidate_active = False
        self.outside_candidate_count = 0
        self.outside_warning_frames = 5

        self.count = 0
        # self.prev_a = self.prev_b = 0.0
        self.a = np.zeros(15, dtype=float)
        self.b = np.zeros(15, dtype=float)

        # --- lightweight frame-rate profiler ---------------------------------
        # Separates the two possible bottlenecks: camera/USB delivery rate
        # (inter-arrival between callbacks) vs. estimate() compute cost.
        self.declare_parameter("profile_timing", True)
        self.profile_timing = bool(self.get_parameter("profile_timing").value)
        self.profile_window = 60          # frames per printed summary
        self._prof_last_recv = None
        self._prof_arrival = []           # s between consecutive frames
        self._prof_compute = []           # s spent inside estimate()

    def _profile_report(self):
        import statistics
        arr = self._prof_arrival
        cmp = self._prof_compute
        if not arr or not cmp:
            return
        arr_mean = statistics.mean(arr)
        cmp_mean = statistics.mean(cmp)
        cam_fps = 1.0 / arr_mean if arr_mean > 0 else 0.0
        cmp_fps = 1.0 / cmp_mean if cmp_mean > 0 else 0.0
        print(
            "[PROFILE] "
            f"camera_arrival: {arr_mean*1000:.1f} ms avg / {max(arr)*1000:.1f} ms max "
            f"(~{cam_fps:.1f} fps)  |  "
            f"estimate(): {cmp_mean*1000:.1f} ms avg / {max(cmp)*1000:.1f} ms max "
            f"(~{cmp_fps:.1f} fps cap)  ->  "
            f"bottleneck={'COMPUTE' if cmp_mean >= arr_mean * 0.9 else 'CAMERA/USB'}"
        )
        self._prof_arrival.clear()
        self._prof_compute.clear()

    def listener_callback(self, data):
        # self.get_logger().info('Receiving image frame')
        t_recv = time.perf_counter()
        if self.profile_timing:
            if self._prof_last_recv is not None:
                self._prof_arrival.append(t_recv - self._prof_last_recv)
            self._prof_last_recv = t_recv

        frame = self.br.imgmsg_to_cv2(data)

        # cv2.imshow("before", frame)
        b, g, r = np.mean(np.mean(frame, axis=0), axis=0)
        # print(b,g,r)
        if g > 100 and b < 40 and r < 40:
            print("SKIP THIS FRAME")
            # cv2.waitKey(1)
            return
        # cv2.imshow("before", frame)
        t_est0 = time.perf_counter()
        x_hat, P, angles, subimg, xb, yb = self.estimation_pipeline.estimate(
            frame, return_ball_subimg=True
        )
        angles = apply_published_angle_zero(
            angles,
            alpha_zero_deg=self.pose_zero_alpha_deg,
            beta_zero_deg=self.pose_zero_beta_deg,
        )
        pose_result = self.pose_gate.update(angles)
        ball_source = self.estimation_pipeline.ball_source
        if not pose_result.accepted:
            detector = self.estimation_pipeline.measurements.detector
            detector.corners = None
            detector.corners_missing = True
            xb = np.nan
            yb = np.nan
            x_hat[2] = np.nan
            x_hat[3] = np.nan
            subimg = np.zeros_like(subimg)
            ball_source = "lost_pose"
            if not self.pose_rejection_active:
                self.get_logger().warn(
                    "Rejecting discontinuous plate-pose solution and "
                    "resetting corner tracking."
                )
                self.pose_rejection_active = True
        elif self.pose_rejection_active:
            self.get_logger().info("Plate-pose tracking recovered.")
            self.pose_rejection_active = False
        angles = pose_result.angles
        if self.profile_timing:
            self._prof_compute.append(time.perf_counter() - t_est0)
            if len(self._prof_compute) >= self.profile_window:
                self._profile_report()
        if np.isfinite(xb) and np.isfinite(yb) and (
            abs(float(xb)) > self.playable_half_x
            or abs(float(yb)) > self.playable_half_y
        ):
            detector = self.estimation_pipeline.measurements.detector
            if self.last_valid_ball_pixel is not None:
                detector.ball_pos = self.last_valid_ball_pixel.copy()
                detector.is_ball_found = True
            else:
                detector.reset_ball_tracking()
            self.outside_candidate_count += 1
            if (
                not self.outside_candidate_active
                and self.outside_candidate_count >= self.outside_warning_frames
            ):
                self.get_logger().warn(
                    "Repeated marble candidates outside playable map; "
                    "retaining last valid tracking crop "
                    f"(x={float(xb):.4f}, y={float(yb):.4f})"
                )
                self.outside_candidate_active = True
            xb = np.nan
            yb = np.nan
            ball_source = "lost_outside"
        elif np.isfinite(xb) and np.isfinite(yb):
            detector = self.estimation_pipeline.measurements.detector
            if detector.ball_pos is not None:
                self.last_valid_ball_pixel = detector.ball_pos.copy()
            if self.outside_candidate_active:
                self.get_logger().info("Marble tracking recovered inside playable map.")
            self.outside_candidate_active = False
            self.outside_candidate_count = 0

        source_message = String()
        source_message.data = ball_source
        self.ball_source_publisher.publish(source_message)
        for publisher, value in (
            (
                self.ai_confidence_publisher,
                self.estimation_pipeline.measurements.ai_confidence,
            ),
            (
                self.ai_disagreement_publisher,
                self.estimation_pipeline.measurements.detection_disagreement_px,
            ),
            (
                self.ai_inference_publisher,
                self.estimation_pipeline.measurements.ai_inference_ms,
            ),
        ):
            diagnostic = Float32()
            diagnostic.data = float(value)
            publisher.publish(diagnostic)
        if self.count % self.skip == 0:
            msg = StateEstimateSub()
            msg.state.x_b = xb
            msg.state.y_b = yb
            msg.state.x_b_dot = x_hat[2]
            msg.state.y_b_dot = x_hat[3]
            msg.state.alpha = -angles[1]
            msg.state.beta = angles[0]
            msg.subimg = self.br.cv2_to_imgmsg(subimg)
            self.publisher_.publish(msg)

            state_msg = StateEstimate()
            state_msg.x_b = msg.state.x_b
            state_msg.y_b = msg.state.y_b
            state_msg.x_b_dot = msg.state.x_b_dot
            state_msg.y_b_dot = msg.state.y_b_dot
            state_msg.alpha = msg.state.alpha
            state_msg.beta = msg.state.beta
            self.state_publisher_.publish(state_msg)
            # self.get_logger().info(f"Publishing: {x_hat}")

        # Broadcast transforms
        if self.count == 0:
            t = self.get_tf_msg(
                self.estimation_pipeline.measurements.plate_pose.T__W_C,
                'camera',
                'world',
            )
            self.tf_static_broadcaster.sendTransform(t)
        t_maze = self.get_tf_msg(
            self.estimation_pipeline.measurements.plate_pose.T__W_M,
            'maze',
            'world',
        )
        T__B_M = np.eye(4)
        ball_position = (
            self.estimation_pipeline.measurements.get_ball_position_in_maze().copy()
        )
        ball_position[:2] = (xb, yb)
        T__B_M[:3, -1] = ball_position
        t_ball = self.get_tf_msg(
            T__B_M,
            'maze',
            'ball'
        )
        self.tf_broadcaster.sendTransform([t_maze, t_ball])

        # self.a[:-1] = self.a[1:]
        # self.a[-1] = msg.state.alpha
        # self.b[:-1] = self.b[1:]
        # self.b[-1] = msg.state.beta
        # print("a_dot: {:.4f}, b_dot: {:.4f}".format((self.a[-1] - self.a[0]) * 55.0 / 14.0, (self.b[-1] - self.b[0]) * 55.0 / 14.0))
        # #self.prev_a = msg.state.alpha
        # self.prev_b = msg.state.beta
        # cv2.imshow("sub", subimg)
        # cv2.waitKey(1)
        self.count += 1

    def get_tf_msg(self, se3, frame_id, child_frame_id):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = frame_id
        t.child_frame_id = child_frame_id
        t.transform.translation.x = se3[0, 3]
        t.transform.translation.y = se3[1, 3]
        t.transform.translation.z = se3[2, 3]
        q = Rotation.from_matrix(se3[:3, :3]).as_quat()
        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]
        return t


def main(args=None):
    rclpy.init(args=args)
    image_subscriber = ImageSubscriber()
    rclpy.spin(image_subscriber)
    rclpy.shutdown()
