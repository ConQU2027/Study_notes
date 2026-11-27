"""Thread-safe, bounded-window metrics for acquisition and ROS publication."""

from collections import deque
import threading
import time
from typing import Deque, Dict, Tuple

from .protocol import JpegFrame, ParserCounters


class StreamMetrics:
    def __init__(self, window_sec: float = 5.0) -> None:
        self.window_sec = window_sec
        self._lock = threading.Lock()
        self._received: Deque[int] = deque()
        self._published: Deque[int] = deque()
        self._board_samples: Deque[Tuple[int, int]] = deque()
        self._rx_ms: Deque[Tuple[int, float]] = deque()
        self._decode_ms: Deque[Tuple[int, float]] = deque()
        self._publish_latency_ms: Deque[Tuple[int, float]] = deque()
        self._batch_samples: Deque[Tuple[int, int]] = deque()
        self.received_total = 0
        self.published_total = 0
        self.decode_errors_total = 0
        self.sequence_dropped_total = 0
        self.queue_dropped_total = 0
        self.receive_batches_total = 0
        self.batch_frames_max_total = 0
        self.connection_attempts_total = 0
        self.connections_total = 0
        self.connection_errors_total = 0
        self.reconnects_total = 0
        self._last_sequence = None
        self._last_received_ns = 0
        self._last_jpeg_bytes = 0

    def _prune(self, values: Deque[int], now_ns: int) -> None:
        cutoff = now_ns - int(self.window_sec * 1e9)
        while values and values[0] < cutoff:
            values.popleft()

    def _prune_timed(self, values: Deque[Tuple[int, float]], now_ns: int) -> None:
        cutoff = now_ns - int(self.window_sec * 1e9)
        while values and values[0][0] < cutoff:
            values.popleft()

    def record_receive_batch(self, frame_count: int) -> None:
        if frame_count <= 0:
            return
        with self._lock:
            now = time.monotonic_ns()
            self.receive_batches_total += 1
            self._batch_samples.append((now, frame_count))
            self.batch_frames_max_total = max(self.batch_frames_max_total, frame_count)
            self._prune_timed(self._batch_samples, now)

    def record_received(self, frame: JpegFrame) -> None:
        with self._lock:
            now = frame.complete_monotonic_ns
            self.received_total += 1
            self._received.append(now)
            self._board_samples.append((now, frame.capture_ms))
            self._rx_ms.append((now, (now - frame.header_monotonic_ns) / 1e6))
            self._last_received_ns = now
            self._last_jpeg_bytes = len(frame.jpeg)
            if self._last_sequence is not None:
                delta = (frame.sequence - self._last_sequence) & 0xFFFFFFFF
                if 1 < delta < 0x80000000:
                    self.sequence_dropped_total += delta - 1
            self._last_sequence = frame.sequence
            self._prune(self._received, now)
            self._prune_timed(self._board_samples, now)
            self._prune_timed(self._rx_ms, now)

    def record_published(self, frame: JpegFrame, decode_ms: float) -> None:
        with self._lock:
            now = time.monotonic_ns()
            self.published_total += 1
            self._published.append(now)
            self._decode_ms.append((now, decode_ms))
            self._publish_latency_ms.append(
                (now, (now - frame.complete_monotonic_ns) / 1e6)
            )
            self._prune(self._published, now)
            self._prune_timed(self._decode_ms, now)
            self._prune_timed(self._publish_latency_ms, now)

    def record_decode_error(self) -> None:
        with self._lock:
            self.decode_errors_total += 1

    def record_queue_drop(self, count: int = 1) -> None:
        with self._lock:
            self.queue_dropped_total += count

    def record_connection_attempt(self) -> None:
        with self._lock:
            self.connection_attempts_total += 1

    def record_connection_open(self) -> None:
        with self._lock:
            if self.connections_total:
                self.reconnects_total += 1
            self.connections_total += 1
            self._last_sequence = None

    def record_connection_error(self) -> None:
        with self._lock:
            self.connection_errors_total += 1

    @staticmethod
    def _fps_ns(samples: Deque[int]) -> float:
        if len(samples) < 2:
            return 0.0
        elapsed = samples[-1] - samples[0]
        return (len(samples) - 1) * 1e9 / elapsed if elapsed > 0 else 0.0

    @staticmethod
    def _fps_board(samples: Deque[Tuple[int, int]]) -> float:
        if len(samples) < 2:
            return 0.0
        elapsed_ms = 0
        intervals = 0
        for (_, previous), (_, current) in zip(samples, list(samples)[1:]):
            delta = (current - previous) & 0x3FFFFFFF
            if 0 < delta <= 5000:
                elapsed_ms += delta
                intervals += 1
        return intervals * 1000.0 / elapsed_ms if elapsed_ms else 0.0

    @staticmethod
    def _mean(samples: Deque[Tuple[int, float]]) -> float:
        return sum(value for _, value in samples) / len(samples) if samples else 0.0

    def snapshot(self, parser: ParserCounters, queue_size: int) -> Dict:
        with self._lock:
            now = time.monotonic_ns()
            self._prune(self._received, now)
            self._prune(self._published, now)
            self._prune_timed(self._board_samples, now)
            self._prune_timed(self._rx_ms, now)
            self._prune_timed(self._decode_ms, now)
            self._prune_timed(self._publish_latency_ms, now)
            self._prune_timed(self._batch_samples, now)
            age_ms = (now - self._last_received_ns) / 1e6 if self._last_received_ns else None
            batch_values = [count for _, count in self._batch_samples]
            return {
                "status": "streaming" if age_ms is not None and age_ms < 3000 else "waiting",
                "stamp_source": "host_wall_time_when_parser_completes_frame",
                "capture_fps_board": round(self._fps_board(self._board_samples), 3),
                "received_fps_host": round(self._fps_ns(self._received), 3),
                "published_fps_ros": round(self._fps_ns(self._published), 3),
                "rx_ms_mean": round(self._mean(self._rx_ms), 3),
                "decode_ms_mean": round(self._mean(self._decode_ms), 3),
                "publish_latency_ms_mean": round(self._mean(self._publish_latency_ms), 3),
                "last_frame_age_ms": round(age_ms, 3) if age_ms is not None else None,
                "last_jpeg_bytes": self._last_jpeg_bytes,
                "received_total": self.received_total,
                "published_total": self.published_total,
                "decode_errors_total": self.decode_errors_total,
                "sequence_dropped_total": self.sequence_dropped_total,
                "queue_dropped_total": self.queue_dropped_total,
                "rx_batch_frames_max": max(batch_values, default=0),
                "rx_batch_frames_mean": round(
                    sum(batch_values) / len(batch_values), 3
                ) if batch_values else 0.0,
                "rx_batch_frames_max_total": self.batch_frames_max_total,
                "receive_batches_total": self.receive_batches_total,
                "connection_attempts_total": self.connection_attempts_total,
                "connections_total": self.connections_total,
                "connection_errors_total": self.connection_errors_total,
                "reconnects_total": self.reconnects_total,
                "queue_capacity": queue_size,
                "crc_errors_total": parser.crc_errors,
                "invalid_headers_total": parser.invalid_headers,
                "invalid_jpeg_total": parser.invalid_jpeg,
                "resync_bytes_total": parser.resync_bytes,
                "frame_timeouts_total": parser.frame_timeouts,
            }
