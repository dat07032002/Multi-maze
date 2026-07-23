#!usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np
from scipy.spatial.transform import Rotation
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
from cyberrunner_state_estimation.core.estimation_pipeline import EstimationPipeline
from cyberrunner_state_estimation.core.opencv_acceleration import (
    configure_opencv_acceleration,
)
from cyberrunner_interfaces.msg import StateEstimate, StateEstimateSub


class ImageSubscriber(Node):
    def __init__(self, skip=1):
        super().__init__("cyberrunner_state_estimation")
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
        self.declare_parameter("playable_edge_margin", 0.002)

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
        edge_margin = max(
            0.0, float(self.get_parameter("playable_edge_margin").value)
        )
        self.playable_half_x = max(0.0, playable_width / 2.0 - edge_margin)
        self.playable_half_y = max(0.0, playable_height / 2.0 - edge_margin)

        self.acceleration_backend, acceleration_msg = configure_opencv_acceleration(
            self.use_gpu,
            self.gpu_backend,
            self.gpu_device_id,
            self.require_gpu,
        )
        self.get_logger().info(acceleration_msg)

        self.subscription = self.create_subscription(
            Image, "cyberrunner_camera/image", self.listener_callback, 1
        )
        self.publisher_ = self.create_publisher(
            StateEstimateSub, "cyberrunner_state_estimation/estimate_subimg", 1
        )
        self.state_publisher_ = self.create_publisher(
            StateEstimate, "cyberrunner_state_estimation/estimate", 1
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
        )

        self.count = 0
        # self.prev_a = self.prev_b = 0.0
        self.a = np.zeros(15, dtype=float)
        self.b = np.zeros(15, dtype=float)

    def listener_callback(self, data):
        # self.get_logger().info('Receiving image frame')
        frame = self.br.imgmsg_to_cv2(data)

        # cv2.imshow("before", frame)
        b, g, r = np.mean(np.mean(frame, axis=0), axis=0)
        # print(b,g,r)
        if g > 100 and b < 40 and r < 40:
            print("SKIP THIS FRAME")
            # cv2.waitKey(1)
            return
        # cv2.imshow("before", frame)
        x_hat, P, angles, subimg, xb, yb = self.estimation_pipeline.estimate(
            frame, return_ball_subimg=True
        )
        if np.isfinite(xb) and np.isfinite(yb) and (
            abs(float(xb)) > self.playable_half_x
            or abs(float(yb)) > self.playable_half_y
        ):
            self.get_logger().warn(
                "Marble detected outside playable map; publishing NaN "
                f"(x={float(xb):.4f}, y={float(yb):.4f})",
                throttle_duration_sec=2.0,
            )
            self.estimation_pipeline.measurements.detector.reset_ball_tracking()
            xb = np.nan
            yb = np.nan
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
        T__B_M[:3, -1] = self.estimation_pipeline.measurements.get_ball_position_in_maze()
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
