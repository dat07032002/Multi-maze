#!/usr/bin/env python3
"""Publish ESP32-forwarded BNO086 samples as standard ROS IMU messages."""

import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import UInt8

from tag_state_estimation.core.bno086_protocol import parse_bno086_line


class Bno086SerialNode(Node):
    """Read newline-delimited BNO086 reports from an ESP32 serial port."""

    def __init__(self):
        """Open the configured serial port and create ROS publishers."""
        super().__init__("tag_bno086_serial")
        self.declare_parameter("port", "/dev/ttyACM0")
        self.declare_parameter("baud", 115200)
        self.declare_parameter("frame_id", "tag_board_imu")
        self.declare_parameter("topic", "/tag_imu/data")
        self.declare_parameter("minimum_accuracy", 1)
        self.declare_parameter("orientation_std_deg", 2.0)
        self.declare_parameter("poll_rate_hz", 200.0)

        try:
            import serial
        except ImportError as exc:
            raise RuntimeError(
                "pyserial is required; install Ubuntu package python3-serial"
            ) from exc

        self.frame_id = str(self.get_parameter("frame_id").value)
        self.minimum_accuracy = int(
            self.get_parameter("minimum_accuracy").value
        )
        if self.minimum_accuracy not in {0, 1, 2, 3}:
            raise ValueError("minimum_accuracy must be in [0, 3]")
        orientation_std = math.radians(
            float(self.get_parameter("orientation_std_deg").value)
        )
        self.orientation_variance = orientation_std ** 2
        topic = str(self.get_parameter("topic").value)
        self.publisher = self.create_publisher(Imu, topic, 10)
        self.accuracy_publisher = self.create_publisher(
            UInt8, "/tag_imu/accuracy", 10
        )
        self.serial = serial.Serial(
            port=str(self.get_parameter("port").value),
            baudrate=int(self.get_parameter("baud").value),
            timeout=0,
        )
        rate = float(self.get_parameter("poll_rate_hz").value)
        if not 10.0 <= rate <= 1000.0:
            raise ValueError("poll_rate_hz must be in [10, 1000]")
        self.timer = self.create_timer(1.0 / rate, self.poll_serial)
        self.invalid_lines = 0
        self.receive_buffer = bytearray()
        self.get_logger().info(
            f"Reading BNO086 from {self.serial.port} at "
            f"{self.serial.baudrate} baud"
        )

    def poll_serial(self):
        """Drain complete lines and publish every accepted sample."""
        waiting = self.serial.in_waiting
        if waiting:
            self.receive_buffer.extend(self.serial.read(waiting))
        while b"\n" in self.receive_buffer:
            raw, remainder = self.receive_buffer.split(b"\n", 1)
            self.receive_buffer = bytearray(remainder)
            try:
                sample = parse_bno086_line(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                self.invalid_lines += 1
                if self.invalid_lines == 1 or self.invalid_lines % 100 == 0:
                    self.get_logger().warn(
                        "Rejected BNO086 serial line "
                        f"({self.invalid_lines}): {exc}"
                    )
                continue
            if (
                sample.accuracy >= 0
                and sample.accuracy < self.minimum_accuracy
            ):
                continue

            message = Imu()
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = self.frame_id
            qx, qy, qz, qw = sample.quaternion_xyzw
            message.orientation.x = float(qx)
            message.orientation.y = float(qy)
            message.orientation.z = float(qz)
            message.orientation.w = float(qw)
            message.orientation_covariance[0] = self.orientation_variance
            message.orientation_covariance[4] = self.orientation_variance
            message.orientation_covariance[8] = self.orientation_variance
            gx, gy, gz = sample.angular_velocity_xyz
            message.angular_velocity.x = float(gx)
            message.angular_velocity.y = float(gy)
            message.angular_velocity.z = float(gz)
            ax, ay, az = sample.linear_acceleration_xyz
            message.linear_acceleration.x = float(ax)
            message.linear_acceleration.y = float(ay)
            message.linear_acceleration.z = float(az)
            self.publisher.publish(message)

            accuracy = UInt8()
            accuracy.data = max(0, int(sample.accuracy))
            self.accuracy_publisher.publish(accuracy)

    def destroy_node(self):
        """Close the serial device before destroying the ROS node."""
        if hasattr(self, "serial") and self.serial.is_open:
            self.serial.close()
        return super().destroy_node()


def main(args=None):
    """Run the BNO086 serial adapter until ROS requests shutdown."""
    rclpy.init(args=args)
    node = Bno086SerialNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
