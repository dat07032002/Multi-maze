#!/usr/bin/env python3

import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class ImageViewer(Node):
    def __init__(self):
        super().__init__("cyberrunner_image_viewer")
        self.bridge = CvBridge()

        self.sub = self.create_subscription(
            Image,
            "/cyberrunner_camera/image",
            self.callback,
            1
        )

        self.get_logger().info("Viewing /cyberrunner_camera/image. Press q to quit.")

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        cv2.imshow("CyberRunner Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = ImageViewer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    cv2.destroyAllWindows()

    if rclpy.ok():
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

