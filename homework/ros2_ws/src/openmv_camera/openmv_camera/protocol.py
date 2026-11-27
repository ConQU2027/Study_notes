"""Incremental decoder for the OpenMV JPEG USB VCP protocol, version 1."""

from dataclasses import dataclass
import struct
import time
from typing import List
import zlib

MAGIC = b"OMVJ"
HEADER = struct.Struct("<4sIIHHII")


@dataclass(frozen=True)
class JpegFrame:
    sequence: int
    capture_ms: int
    width: int
    height: int
    jpeg: bytes
    header_monotonic_ns: int
    complete_monotonic_ns: int
    complete_wall_ns: int


@dataclass
class ParserCounters:
    valid_frames: int = 0
    invalid_headers: int = 0
    crc_errors: int = 0
    invalid_jpeg: int = 0
    resync_bytes: int = 0
    frame_timeouts: int = 0


class FrameParser:
    """Parse arbitrary serial chunks, resynchronizing after damaged data."""

    def __init__(self, max_jpeg_bytes: int = 1_000_000, frame_timeout_ms: int = 500) -> None:
        if max_jpeg_bytes <= 0:
            raise ValueError("max_jpeg_bytes must be positive")
        if frame_timeout_ms <= 0:
            raise ValueError("frame_timeout_ms must be positive")
        self.max_jpeg_bytes = max_jpeg_bytes
        self.frame_timeout_ns = frame_timeout_ms * 1_000_000
        self.counters = ParserCounters()
        self._buffer = bytearray()
        self._header_monotonic_ns = 0

    def reset(self) -> None:
        """Discard a partial frame after reconnecting; retain total counters."""
        self._buffer.clear()
        self._header_monotonic_ns = 0

    def _expire_partial_frame(self, now_ns: int) -> None:
        if (
            self._header_monotonic_ns
            and now_ns - self._header_monotonic_ns > self.frame_timeout_ns
        ):
            self.counters.frame_timeouts += 1
            self.counters.resync_bytes += len(self._buffer)
            self.reset()

    def feed(self, data: bytes) -> List[JpegFrame]:
        frames: List[JpegFrame] = []
        feed_ns = time.monotonic_ns()
        self._expire_partial_frame(feed_ns)
        if not data:
            return frames
        self._buffer.extend(data)

        while True:
            magic_at = self._buffer.find(MAGIC)
            if magic_at < 0:
                keep = min(len(self._buffer), len(MAGIC) - 1)
                discarded = len(self._buffer) - keep
                if discarded:
                    self.counters.resync_bytes += discarded
                    del self._buffer[:discarded]
                self._header_monotonic_ns = 0
                break
            if magic_at:
                self.counters.resync_bytes += magic_at
                del self._buffer[:magic_at]
                self._header_monotonic_ns = 0
            if len(self._buffer) < HEADER.size:
                break

            header_ns = feed_ns
            _, sequence, capture_ms, width, height, size, expected_crc = HEADER.unpack(
                self._buffer[:HEADER.size]
            )
            if not (0 < width <= 8192 and 0 < height <= 8192 and 0 < size <= self.max_jpeg_bytes):
                self.counters.invalid_headers += 1
                self._header_monotonic_ns = 0
                del self._buffer[0]
                continue

            total_size = HEADER.size + size
            if len(self._buffer) < total_size:
                if self._header_monotonic_ns == 0:
                    self._header_monotonic_ns = header_ns
                break

            payload = bytes(self._buffer[HEADER.size:total_size])
            del self._buffer[:total_size]
            complete_mono_ns = time.monotonic_ns()
            complete_wall_ns = time.time_ns()
            frame_header_ns = self._header_monotonic_ns or header_ns
            self._header_monotonic_ns = 0

            if (zlib.crc32(payload) & 0xFFFFFFFF) != expected_crc:
                self.counters.crc_errors += 1
                continue
            if not payload.startswith(b"\xFF\xD8") or not payload.endswith(b"\xFF\xD9"):
                self.counters.invalid_jpeg += 1
                continue

            self.counters.valid_frames += 1
            frames.append(
                JpegFrame(
                    sequence=sequence,
                    capture_ms=capture_ms,
                    width=width,
                    height=height,
                    jpeg=payload,
                    header_monotonic_ns=frame_header_ns,
                    complete_monotonic_ns=complete_mono_ns,
                    complete_wall_ns=complete_wall_ns,
                )
            )

        return frames
