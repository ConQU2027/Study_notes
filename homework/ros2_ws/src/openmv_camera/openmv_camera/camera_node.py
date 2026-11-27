"""ROS 2 Humble node: USB VCP JPEG reception, decoding, and publication."""

import copy
import json
from pathlib import Path
import queue
import threading
import time
from urllib.parse import unquote, urlparse

import cv2
import numpy as np
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
import serial
import yaml

from .metrics import StreamMetrics
from .protocol import FrameParser, JpegFrame
from .serial_io import read_available


class OpenMvCameraNode(Node):
    def __init__(self) -> None:
        super().__init__("openmv_camera")
        if self.get_parameter("use_sim_time").value:
            self.get_logger().fatal("The live camera node requires use_sim_time:=false")
            super().destroy_node()
            raise SystemExit(1)
        self._port = self.declare_parameter("serial_port", "/dev/ttyACM0").value
        self._read_timeout = self.declare_parameter("serial_read_timeout_sec", 0.2).value
        self._reconnect_delay = self.declare_parameter("reconnect_delay_sec", 1.0).value
        self._read_chunk = self.declare_parameter("read_chunk_size", 16384).value
        self._frame_id = self.declare_parameter("frame_id", "camera_optical_frame").value
        self._expected_width = self.declare_parameter("expected_width", 320).value
        self._expected_height = self.declare_parameter("expected_height", 240).value
        self._queue_size = self.declare_parameter("queue_size", 2).value
        stats_period = self.declare_parameter("stats_period_sec", 1.0).value
        max_jpeg_bytes = self.declare_parameter("max_jpeg_bytes", 1_000_000).value
        frame_timeout_ms = self.declare_parameter("frame_timeout_ms", 500).value
        opencv_threads = self.declare_parameter("opencv_num_threads", 1).value
        camera_info_url = self.declare_parameter("camera_info_url", "").value

        if self._queue_size < 1:
            raise ValueError("queue_size must be at least 1")
        if self._expected_width <= 0 or self._expected_height <= 0:
            raise ValueError("expected image dimensions must be positive")
        if self._read_chunk <= 0 or self._read_timeout <= 0:
            raise ValueError("read_chunk_size and serial_read_timeout_sec must be positive")
        cv2.setNumThreads(opencv_threads)

        self._image_pub = self.create_publisher(Image, "image_raw", qos_profile_sensor_data)
        # Match common camera-driver/image_transport usage and reduce tool QoS setup.
        self._info_pub = self.create_publisher(CameraInfo, "camera_info", QoSProfile(depth=10))
        self._stats_pub = self.create_publisher(String, "stats", 10)
        self._frames: queue.Queue = queue.Queue(maxsize=self._queue_size)
        self._parser = FrameParser(
            max_jpeg_bytes=max_jpeg_bytes,
            frame_timeout_ms=frame_timeout_ms,
        )
        self._metrics = StreamMetrics(window_sec=5.0)
        self._camera_info_template = self._load_camera_info(camera_info_url)
        self._stop = threading.Event()
        self._last_connect_log = 0.0
        self._last_error_log = 0.0

        self._reader = threading.Thread(target=self._reader_loop, name="openmv_rx", daemon=True)
        self._reader.start()
        # Live acquisition must keep running through host wall-clock/NTP steps.
        # Message stamps remain wall time; only timer scheduling uses steady time.
        self._steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self._process_timer = self.create_timer(
            0.005,
            self._process_latest_frame,
            clock=self._steady_clock,
        )
        self._stats_timer = self.create_timer(
            stats_period,
            self._publish_stats,
            clock=self._steady_clock,
        )
        self.get_logger().info(
            f"Waiting for {self._port}; nominal VCP baud is ignored by USB. "
            "Image stamps use host parse-completion time until clock alignment is implemented."
        )

    def _load_camera_info(self, url: str) -> CameraInfo:
        info = CameraInfo()
        info.header.frame_id = self._frame_id
        info.width = self._expected_width
        info.height = self._expected_height
        if not url:
            # ROS convention for an uncalibrated camera: zero camera matrix.
            info.k = [0.0] * 9
            info.d = []
            info.r = [0.0] * 9
            info.p = [0.0] * 12
            self.get_logger().warning("No calibration loaded; CameraInfo.K is intentionally zero.")
            return info

        path = unquote(urlparse(url).path) if url.startswith("file://") else url
        with Path(path).open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
        info.width = int(data["image_width"])
        info.height = int(data["image_height"])
        info.distortion_model = str(data["distortion_model"])
        info.d = [float(value) for value in data["distortion_coefficients"]["data"]]
        info.k = [float(value) for value in data["camera_matrix"]["data"]]
        info.r = [float(value) for value in data["rectification_matrix"]["data"]]
        info.p = [float(value) for value in data["projection_matrix"]["data"]]
        if len(info.k) != 9 or len(info.r) != 9 or len(info.p) != 12:
            raise ValueError("Calibration matrix dimensions are invalid")
        if (info.width, info.height) != (self._expected_width, self._expected_height):
            raise ValueError("Calibration resolution differs from expected_width/expected_height")
        self.get_logger().info(f"Loaded calibration from {path}")
        return info

    def _reader_loop(self) -> None:
        while not self._stop.is_set():
            connection = None
            try:
                self._metrics.record_connection_attempt()
                connection = serial.Serial(
                    port=self._port,
                    baudrate=115200,  # Nominal only; USB VCP does not use UART baud timing.
                    timeout=self._read_timeout,
                )
                connection.reset_input_buffer()
                self._parser.reset()
                self._metrics.record_connection_open()
                self.get_logger().info(f"Connected to {self._port}")
                while not self._stop.is_set():
                    data = read_available(connection, self._read_chunk)
                    frames = self._parser.feed(data)
                    self._metrics.record_receive_batch(len(frames))
                    for frame in frames:
                        self._metrics.record_received(frame)
                        self._enqueue(frame)
            except (serial.SerialException, OSError, ValueError) as error:
                now = time.monotonic()
                if now - self._last_connect_log >= 5.0:
                    self.get_logger().warning(f"OpenMV serial connection: {error}")
                    self._last_connect_log = now
                self._metrics.record_connection_error()
            finally:
                if connection is not None:
                    connection.close()
            self._stop.wait(self._reconnect_delay)

    def _enqueue(self, frame: JpegFrame) -> None:
        while not self._stop.is_set():
            try:
                self._frames.put_nowait(frame)
                return
            except queue.Full:
                try:
                    self._frames.get_nowait()
                    self._metrics.record_queue_drop()
                except queue.Empty:
                    pass

    def _process_latest_frame(self) -> None:
        latest = None
        while True:
            try:
                frame = self._frames.get_nowait()
                if latest is not None:
                    self._metrics.record_queue_drop()
                latest = frame
            except queue.Empty:
                break
        if latest is None:
            return

        decode_started = time.monotonic_ns()
        decoded = cv2.imdecode(np.frombuffer(latest.jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        decode_ms = (time.monotonic_ns() - decode_started) / 1e6
        if decoded is None:
            self._metrics.record_decode_error()
            self._log_error_throttled("JPEG decode failed")
            return
        height, width = decoded.shape[:2]
        if (width, height) != (latest.width, latest.height):
            self._metrics.record_decode_error()
            self._log_error_throttled("Decoded dimensions differ from the frame header")
            return
        if (width, height) != (self._expected_width, self._expected_height):
            self._metrics.record_decode_error()
            self._log_error_throttled(
                f"Unexpected resolution {width}x{height}; check board script and YAML"
            )
            return
        if self._camera_info_template.k[0] != 0.0 and (
            width != self._camera_info_template.width or height != self._camera_info_template.height
        ):
            self._metrics.record_decode_error()
            self._log_error_throttled("Image resolution differs from loaded calibration")
            return

        stamp = Time(nanoseconds=latest.complete_wall_ns).to_msg()
        image_msg = Image()
        image_msg.header.stamp = stamp
        image_msg.header.frame_id = self._frame_id
        image_msg.height = height
        image_msg.width = width
        image_msg.encoding = "bgr8"
        image_msg.is_bigendian = False
        image_msg.step = width * 3
        image_msg.data = np.ascontiguousarray(decoded).tobytes()

        info_msg = copy.deepcopy(self._camera_info_template)
        info_msg.header.stamp = stamp
        info_msg.header.frame_id = self._frame_id
        self._image_pub.publish(image_msg)
        self._info_pub.publish(info_msg)
        self._metrics.record_published(latest, decode_ms)

    def _log_error_throttled(self, message: str) -> None:
        now = time.monotonic()
        if now - self._last_error_log >= 2.0:
            self.get_logger().error(message)
            self._last_error_log = now

    def _publish_stats(self) -> None:
        report = self._metrics.snapshot(self._parser.counters, self._queue_size)
        message = String()
        message.data = json.dumps(report, ensure_ascii=False, sort_keys=True)
        self._stats_pub.publish(message)

    def destroy_node(self) -> bool:
        self._stop.set()
        self._reader.join(timeout=2.0)
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = OpenMvCameraNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
