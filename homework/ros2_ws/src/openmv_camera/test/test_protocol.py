import struct
import unittest
import zlib

from openmv_camera.protocol import FrameParser, HEADER, MAGIC


def encoded_frame(sequence=0, capture_ms=1000, width=320, height=240, payload=None):
    if payload is None:
        payload = b"\xFF\xD8test-jpeg-payload\xFF\xD9"
    header = HEADER.pack(
        MAGIC,
        sequence,
        capture_ms,
        width,
        height,
        len(payload),
        zlib.crc32(payload) & 0xFFFFFFFF,
    )
    return header + payload


class FrameParserTest(unittest.TestCase):
    def test_single_frame(self):
        parser = FrameParser()
        frames = parser.feed(encoded_frame(sequence=7))
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].sequence, 7)
        self.assertEqual((frames[0].width, frames[0].height), (320, 240))
        self.assertTrue(frames[0].jpeg.startswith(b"\xFF\xD8"))

    def test_every_byte_fragmentation(self):
        parser = FrameParser()
        data = encoded_frame(sequence=9)
        frames = []
        for value in data:
            frames.extend(parser.feed(bytes([value])))
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].sequence, 9)

    def test_multiple_frames_and_garbage(self):
        parser = FrameParser()
        frames = parser.feed(b"noise" + encoded_frame(sequence=1) + encoded_frame(sequence=2))
        self.assertEqual([frame.sequence for frame in frames], [1, 2])
        self.assertEqual(parser.counters.resync_bytes, 5)

    def test_split_magic_and_reset(self):
        parser = FrameParser()
        data = encoded_frame()
        self.assertEqual(parser.feed(data[:2]), [])
        self.assertEqual(parser.feed(data[2:10]), [])
        parser.reset()
        self.assertEqual(parser.feed(encoded_frame(sequence=4))[0].sequence, 4)

    def test_crc_error_does_not_emit_frame(self):
        parser = FrameParser()
        damaged = bytearray(encoded_frame(sequence=1))
        damaged[-3] ^= 0x01
        self.assertEqual(parser.feed(bytes(damaged)), [])
        self.assertEqual(parser.counters.crc_errors, 1)
        self.assertEqual(parser.feed(encoded_frame(sequence=2))[0].sequence, 2)

    def test_invalid_jpeg_marker_is_rejected(self):
        parser = FrameParser()
        self.assertEqual(parser.feed(encoded_frame(payload=b"not-a-jpeg")), [])
        self.assertEqual(parser.counters.invalid_jpeg, 1)

    def test_oversized_payload_header_is_rejected_then_resynchronizes(self):
        parser = FrameParser(max_jpeg_bytes=32)
        bad_header = HEADER.pack(MAGIC, 1, 0, 320, 240, 1000, 0)
        frames = parser.feed(bad_header + encoded_frame(sequence=5))
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].sequence, 5)
        self.assertGreaterEqual(parser.counters.invalid_headers, 1)

    def test_garbage_buffer_stays_bounded(self):
        parser = FrameParser()
        self.assertEqual(parser.feed(b"x" * 10000), [])
        self.assertLessEqual(len(parser._buffer), len(MAGIC) - 1)


if __name__ == "__main__":
    unittest.main()
