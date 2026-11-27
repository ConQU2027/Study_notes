import unittest
from unittest.mock import patch
import zlib

from openmv_camera.metrics import StreamMetrics
from openmv_camera.protocol import FrameParser, HEADER, MAGIC, ParserCounters
from openmv_camera.stream_check import check_stream


def encoded_frame(sequence=0, payload=b"\xFF\xD8regression-test\xFF\xD9"):
    return HEADER.pack(
        MAGIC, sequence, 1000, 320, 240, len(payload), zlib.crc32(payload) & 0xFFFFFFFF
    ) + payload


class TimingRegressionTest(unittest.TestCase):
    @patch("openmv_camera.protocol.time.monotonic_ns")
    def test_header_time_survives_multiple_payload_reads(self, monotonic_ns):
        monotonic_ns.side_effect = [
            1_000_000_000, 1_100_000_000, 1_200_000_000, 1_250_000_000
        ]
        parser = FrameParser()
        data = encoded_frame()
        split = HEADER.size + 4
        self.assertEqual(parser.feed(data[:split]), [])
        self.assertEqual(parser.feed(data[split:split + 2]), [])
        frames = parser.feed(data[split + 2:])
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].header_monotonic_ns, 1_000_000_000)
        self.assertEqual(frames[0].complete_monotonic_ns, 1_250_000_000)

    @patch("openmv_camera.protocol.time.monotonic_ns")
    def test_crc_failure_clears_partial_header_time(self, monotonic_ns):
        monotonic_ns.side_effect = [
            1_000_000_000, 1_100_000_000, 1_150_000_000, 1_200_000_000, 1_250_000_000
        ]
        parser = FrameParser()
        damaged = bytearray(encoded_frame())
        damaged[-3] ^= 1
        split = HEADER.size + 2
        parser.feed(bytes(damaged[:split]))
        self.assertEqual(parser.feed(bytes(damaged[split:])), [])
        frames = parser.feed(encoded_frame(sequence=8))
        self.assertEqual(frames[0].header_monotonic_ns, 1_200_000_000)


class PartialFrameTimeoutTest(unittest.TestCase):
    @patch("openmv_camera.protocol.time.monotonic_ns")
    def test_incomplete_frame_expires_and_next_frame_recovers(self, monotonic_ns):
        monotonic_ns.side_effect = [
            1_000_000_000, 1_200_000_000, 1_300_000_000, 1_400_000_000
        ]
        parser = FrameParser(frame_timeout_ms=100)
        partial = encoded_frame()[: HEADER.size + 3]
        self.assertEqual(parser.feed(partial), [])
        self.assertEqual(parser.feed(b""), [])
        self.assertEqual(parser.counters.frame_timeouts, 1)
        self.assertEqual(parser.counters.resync_bytes, len(partial))
        self.assertEqual(parser._buffer, bytearray())
        frames = parser.feed(encoded_frame(sequence=11))
        self.assertEqual([frame.sequence for frame in frames], [11])


class BatchWindowTest(unittest.TestCase):
    @patch("openmv_camera.metrics.time.monotonic_ns")
    def test_batch_window_expires_but_lifetime_max_remains(self, monotonic_ns):
        monotonic_ns.side_effect = [1_000_000_000, 7_000_000_000, 7_000_000_000]
        metrics = StreamMetrics(window_sec=5.0)
        metrics.record_receive_batch(3)
        metrics.record_receive_batch(1)
        report = metrics.snapshot(ParserCounters(), queue_size=2)
        self.assertEqual(report["rx_batch_frames_max"], 1)
        self.assertEqual(report["rx_batch_frames_mean"], 1.0)
        self.assertEqual(report["rx_batch_frames_max_total"], 3)
        self.assertEqual(report["receive_batches_total"], 2)


class StreamCheckFailureTest(unittest.TestCase):
    @patch("openmv_camera.stream_check.serial.Serial", side_effect=OSError("mock open failed"))
    def test_open_failure_returns_partial_report(self, serial_class):
        report = check_stream("/dev/mock", frame_goal=100, timeout_sec=20.0)
        self.assertFalse(report["success"])
        self.assertEqual(report["frames_received"], 0)
        self.assertEqual(report["error"], "mock open failed")
        self.assertIn("wall_elapsed_sec", report)
        serial_class.assert_called_once()


class ConnectionMetricsTest(unittest.TestCase):
    def test_reconnect_counts_successful_reopen_not_failed_attempts(self):
        metrics = StreamMetrics()
        metrics.record_connection_attempt()
        metrics.record_connection_open()
        metrics.record_connection_error()
        metrics.record_connection_attempt()
        metrics.record_connection_open()
        metrics.record_receive_batch(3)
        report = metrics.snapshot(ParserCounters(), queue_size=2)
        self.assertEqual(report["connection_attempts_total"], 2)
        self.assertEqual(report["connections_total"], 2)
        self.assertEqual(report["connection_errors_total"], 1)
        self.assertEqual(report["reconnects_total"], 1)
        self.assertEqual(report["rx_batch_frames_max"], 3)
        self.assertEqual(report["rx_batch_frames_mean"], 3.0)


if __name__ == "__main__":
    unittest.main()
