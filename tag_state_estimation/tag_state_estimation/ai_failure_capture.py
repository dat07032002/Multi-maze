"""Passively capture camera frames around marble-tracking failure events."""

from collections import deque
import csv
from pathlib import Path
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, String


NORMAL_SOURCES = {"fused", "ai_reacquired", "ai_disagreement"}
FIELDS = (
    "filename",
    "image_time_ns",
    "ball_source",
    "ai_confidence",
    "disagreement_px",
    "capture_reason",
    "label_status",
)


class AiFailureCapture(Node):
    """Save event windows without publishing application or control topics."""

    def __init__(self):
        super().__init__("tag_ai_failure_capture")
        self.declare_parameter("output_dir", "~/tag_ai_failure_capture")
        self.declare_parameter("duration_sec", 30.0)
        self.declare_parameter("pre_frames", 4)
        self.declare_parameter("post_frames", 4)
        self.declare_parameter("stable_interval_sec", 1.0)
        self.declare_parameter("jpeg_quality", 95)

        self.output_dir = Path(
            str(self.get_parameter("output_dir").value)
        ).expanduser()
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.output_dir / "capture_manifest.csv"
        self.manifest_file = self.manifest_path.open("w", newline="")
        self.writer = csv.DictWriter(self.manifest_file, fieldnames=FIELDS)
        self.writer.writeheader()

        self.bridge = CvBridge()
        self.pre_frames = max(0, int(self.get_parameter("pre_frames").value))
        self.post_frames = max(0, int(self.get_parameter("post_frames").value))
        self.jpeg_quality = int(self.get_parameter("jpeg_quality").value)
        self.stable_interval_sec = float(
            self.get_parameter("stable_interval_sec").value
        )
        self.recent = deque(maxlen=max(1, self.pre_frames))
        self.pending_post_frames = 0
        self.latest_source = "initializing"
        self.latest_confidence = float("nan")
        self.latest_disagreement = float("nan")
        self.last_stable_save = 0.0
        self.saved_stamps = set()
        self.saved_count = 0
        self.event_count = 0
        self.done = False

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=8,
        )
        self.create_subscription(Image, "/tag_camera/image", self._on_image, qos)
        self.create_subscription(
            String, "/tag_state_estimation/ball_source", self._on_source, 10
        )
        self.create_subscription(
            Float32,
            "/tag_state_estimation/ai_confidence",
            self._on_confidence,
            10,
        )
        self.create_subscription(
            Float32,
            "/tag_state_estimation/detection_disagreement_px",
            self._on_disagreement,
            10,
        )
        duration = float(self.get_parameter("duration_sec").value)
        self.create_timer(duration, self._stop)
        self.get_logger().info(
            f"Passive AI failure capture started for {duration:.1f}s: "
            f"{self.output_dir}"
        )

    @staticmethod
    def _stamp_ns(message):
        return int(message.header.stamp.sec) * 1_000_000_000 + int(
            message.header.stamp.nanosec
        )

    def _on_confidence(self, message):
        self.latest_confidence = float(message.data)

    def _on_disagreement(self, message):
        self.latest_disagreement = float(message.data)

    def _on_source(self, message):
        previous = self.latest_source
        self.latest_source = str(message.data)
        if (
            self.latest_source not in NORMAL_SOURCES
            and previous in NORMAL_SOURCES
        ):
            self.event_count += 1
            for item in tuple(self.recent):
                self._save(*item, reason="event_pre")
            self.pending_post_frames = self.post_frames
        elif (
            self.latest_source in NORMAL_SOURCES
            and previous not in NORMAL_SOURCES
        ):
            self.pending_post_frames = self.post_frames

    def _on_image(self, message):
        frame = self.bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
        item = (
            self._stamp_ns(message),
            frame.copy(),
            self.latest_source,
            self.latest_confidence,
            self.latest_disagreement,
        )
        self.recent.append(item)
        if self.pending_post_frames > 0:
            self._save(*item, reason="event_post")
            self.pending_post_frames -= 1
            return
        now = time.monotonic()
        if (
            self.latest_source in NORMAL_SOURCES
            and now - self.last_stable_save >= self.stable_interval_sec
        ):
            self._save(*item, reason="stable_control")
            self.last_stable_save = now

    def _save(
        self, stamp_ns, frame, source, confidence, disagreement, reason
    ):
        if stamp_ns in self.saved_stamps:
            return
        filename = f"frame_{self.saved_count:06d}_{stamp_ns}.jpg"
        path = self.images_dir / filename
        if not cv2.imwrite(
            str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
        ):
            raise RuntimeError(f"Failed to write {path}")
        self.writer.writerow(
            {
                "filename": filename,
                "image_time_ns": stamp_ns,
                "ball_source": source,
                "ai_confidence": confidence,
                "disagreement_px": disagreement,
                "capture_reason": reason,
                "label_status": "unlabeled",
            }
        )
        self.manifest_file.flush()
        self.saved_stamps.add(stamp_ns)
        self.saved_count += 1

    def _stop(self):
        self.get_logger().info(
            f"Capture complete: events={self.event_count}, "
            f"images={self.saved_count}"
        )
        self.done = True

    def close(self):
        if not self.manifest_file.closed:
            self.manifest_file.close()


def main(args=None):
    rclpy.init(args=args)
    node = AiFailureCapture()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
