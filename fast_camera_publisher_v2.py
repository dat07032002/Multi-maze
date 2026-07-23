#!/usr/bin/env python3

import time
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy


class FastCameraPublisher(Node):
    def __init__(self):
        super().__init__("cyberrunner_camera")

        self.declare_parameter("device", "/dev/v4l/by-id/usb-e-con_systems_See3CAM_24CUG_0F2D140416020900-video-index0")
        self.declare_parameter("fps", 60.0)
        self.declare_parameter("width", 1280)
        self.declare_parameter("height", 720)
        self.declare_parameter("output_width", 640)
        self.declare_parameter("output_height", 360)
        self.declare_parameter("border_y", 20)
        self.declare_parameter("fourcc", "MJPG")
        self.declare_parameter("exposure", -1)  # -1 = auto, >0 = manual (100µs units, e.g. 150 = 15ms)

        self.device = self.get_parameter("device").value
        self.fps = float(self.get_parameter("fps").value)
        self.width = int(self.get_parameter("width").value)
        self.height = int(self.get_parameter("height").value)
        self.output_width = int(self.get_parameter("output_width").value)
        self.output_height = int(self.get_parameter("output_height").value)
        self.border_y = int(self.get_parameter("border_y").value)
        self.fourcc = str(self.get_parameter("fourcc").value)
        self.exposure = int(self.get_parameter("exposure").value)

        self.bridge = CvBridge()

        # Best QoS for camera streaming:
        # Keep only newest frame, do not block waiting for old frames.
        image_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.pub = self.create_publisher(
            Image,
            "/cyberrunner_camera/image",
            image_qos
        )

        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera device: {self.device}")

        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self.exposure > 0:
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 = manual in V4L2
            self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure)
            self.get_logger().info(f"Exposure: manual ({self.exposure})")
        else:
            self.get_logger().info("Exposure: auto")

        self.get_logger().info(f"Camera opened: {self.device}")
        self.get_logger().info(f"Requested FOURCC: {self.fourcc}")
        self.get_logger().info(f"Actual width: {self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
        self.get_logger().info(f"Actual height: {self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
        self.get_logger().info(f"Actual FPS setting: {self.cap.get(cv2.CAP_PROP_FPS)}")
        self.get_logger().info(
            f"Publishing output: {self.output_width}x{self.output_height + 2 * self.border_y}"
        )

        self.frame_count = 0
        self.last_report_time = time.time()

    def run(self):
        while rclpy.ok():
            ok, frame = self.cap.read()

            if not ok or frame is None:
                self.get_logger().warn("Failed to read camera frame")
                continue

            # Resize 1280x720 -> 640x360
            frame = cv2.resize(
                frame,
                (self.output_width, self.output_height),
                interpolation=cv2.INTER_AREA
            )

            # Add top/bottom border: 640x360 -> 640x400
            if self.border_y > 0:
                frame = cv2.copyMakeBorder(
                    frame,
                    self.border_y,
                    self.border_y,
                    0,
                    0,
                    cv2.BORDER_CONSTANT,
                    value=(0, 0, 0)
                )

            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "camera"

            self.pub.publish(msg)

            self.frame_count += 1
            now = time.time()

            if now - self.last_report_time >= 2.0:
                fps_now = self.frame_count / (now - self.last_report_time)
                self.get_logger().info(f"Publish FPS: {fps_now:.1f}")
                self.frame_count = 0
                self.last_report_time = now

        self.cleanup()

    def cleanup(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None


def main(args=None):
    rclpy.init(args=args)
    node = None

    try:
        node = FastCameraPublisher()
        node.run()

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        if node is not None:
            node.cleanup()
            node.destroy_node()

        # Prevent "rcl_shutdown already called" crash
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()