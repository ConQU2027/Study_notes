import time
import unittest

from openmv_camera.metrics import StreamMetrics
from openmv_camera.protocol import JpegFrame, ParserCounters


def synthetic_frame(sequence, host_ns, board_ms):
    return JpegFrame(
        sequence=sequence,
        capture_ms=board_ms,
        width=320,
        height=240,
        jpeg=b"\xFF\xD8x\xFF\xD9",
        header_monotonic_ns=host_ns - 5_000_000,
        complete_monotonic_ns=host_ns,
        complete_wall_ns=time.time_ns(),
    )


class StreamMetricsTest(unittest.TestCase):
    def test_rates_gaps_and_timing(self):
        metrics = StreamMetrics(window_sec=5.0)
        now = time.monotonic_ns()
        first = synthetic_frame(sequence=10, host_ns=now - 50_000_000, board_ms=1000)
        second = synthetic_frame(sequence=12, host_ns=now, board_ms=1050)
        metrics.record_received(first)
        metrics.record_received(second)
        metrics.record_queue_drop(2)
        metrics.record_published(second, decode_ms=2.5)
        report = metrics.snapshot(ParserCounters(), queue_size=2)

        self.assertAlmostEqual(report["capture_fps_board"], 20.0)
        self.assertAlmostEqual(report["received_fps_host"], 20.0)
        self.assertEqual(report["sequence_dropped_total"], 1)
        self.assertEqual(report["queue_dropped_total"], 2)
        self.assertEqual(report["rx_ms_mean"], 5.0)
        self.assertEqual(report["decode_ms_mean"], 2.5)
        self.assertEqual(report["published_total"], 1)

    def test_board_clock_wrap(self):
        metrics = StreamMetrics()
        now = time.monotonic_ns()
        near_wrap = (1 << 30) - 25
        metrics.record_received(synthetic_frame(1, now - 50_000_000, near_wrap))
        metrics.record_received(synthetic_frame(2, now, 25))
        report = metrics.snapshot(ParserCounters(), queue_size=2)
        self.assertAlmostEqual(report["capture_fps_board"], 20.0)


if __name__ == "__main__":
    unittest.main()
