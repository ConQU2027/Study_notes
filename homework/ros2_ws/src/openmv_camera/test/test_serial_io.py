import unittest

from openmv_camera.serial_io import read_available


class FakeConnection:
    def __init__(self, pending):
        self.in_waiting = pending
        self.requested = []

    def read(self, size):
        self.requested.append(size)
        return b"x" * size


class ReadAvailableTest(unittest.TestCase):
    def test_idle_port_waits_for_only_one_byte(self):
        connection = FakeConnection(pending=0)
        self.assertEqual(read_available(connection, 16384), b"x")
        self.assertEqual(connection.requested, [1])

    def test_pending_bytes_return_without_large_batch_wait(self):
        connection = FakeConnection(pending=37)
        self.assertEqual(len(read_available(connection, 16384)), 37)
        self.assertEqual(connection.requested, [37])

    def test_pending_bytes_are_capped(self):
        connection = FakeConnection(pending=20000)
        self.assertEqual(len(read_available(connection, 16384)), 16384)
        self.assertEqual(connection.requested, [16384])

    def test_invalid_chunk_size(self):
        with self.assertRaises(ValueError):
            read_available(FakeConnection(0), 0)


if __name__ == "__main__":
    unittest.main()
