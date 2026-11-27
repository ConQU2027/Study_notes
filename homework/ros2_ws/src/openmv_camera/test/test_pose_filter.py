import unittest

import numpy as np

from openmv_camera.pose_filter import (
    FilterRejection, PoseFilter, quaternion_angle_deg, slerp_quaternion,
)


DEFAULTS = {
    "position_min_cutoff_hz": 1.0,
    "position_beta": 0.02,
    "position_derivative_cutoff_hz": 1.0,
    "orientation_tau_sec": 0.12,
    "max_position_jump_m": 0.30,
    "max_rotation_jump_deg": 80.0,
    "reacquire_timeout_sec": 0.5,
}


class PoseFilterTest(unittest.TestCase):
    def test_one_euro_reduces_small_stationary_position_noise(self):
        pose_filter = PoseFilter(DEFAULTS)
        raw = []
        filtered = []
        for index in range(100):
            position = np.array([0.2 + (0.005 if index % 2 else -0.005), 0.0, 0.5])
            result, _ = pose_filter.process(position, [0, 0, 0, 1], index * 0.05)
            if index >= 10:
                raw.append(position[0])
                filtered.append(result["translation_m"][0])
        self.assertLess(np.std(filtered), np.std(raw))

    def test_quaternion_sign_flip_preserves_continuous_orientation(self):
        pose_filter = PoseFilter(DEFAULTS)
        pose_filter.process([0.2, 0.0, 0.5], [0, 0, 0, 1], 0.0)
        result, info = pose_filter.process([0.2, 0.0, 0.5], [0, 0, 0, -1], 0.05)
        self.assertAlmostEqual(info["rotation_jump_deg"], 0.0, places=8)
        self.assertGreater(result["quaternion_xyzw"][3], 0.99)

    def test_slerp_halfway_between_identity_and_half_turn(self):
        result = slerp_quaternion([0, 0, 0, 1], [0, 0, 1, 0], 0.5)
        np.testing.assert_allclose(result, [0, 0, np.sqrt(0.5), np.sqrt(0.5)], atol=1e-12)

    def test_large_position_jump_is_rejected_without_output(self):
        pose_filter = PoseFilter(DEFAULTS)
        pose_filter.process([0.2, 0.0, 0.5], [0, 0, 0, 1], 0.0)
        with self.assertRaises(FilterRejection) as raised:
            pose_filter.process([1.0, 0.0, 0.5], [0, 0, 0, 1], 0.05)
        self.assertEqual(raised.exception.reason, "position_outlier")

    def test_large_rotation_jump_is_rejected(self):
        pose_filter = PoseFilter(DEFAULTS)
        pose_filter.process([0.2, 0.0, 0.5], [0, 0, 0, 1], 0.0)
        with self.assertRaises(FilterRejection) as raised:
            pose_filter.process([0.2, 0.0, 0.5], [0, 0, 1, 0], 0.05)
        self.assertEqual(raised.exception.reason, "orientation_outlier")

    def test_long_gap_reacquires_instead_of_rejecting_forever(self):
        pose_filter = PoseFilter(DEFAULTS)
        pose_filter.process([0.2, 0.0, 0.5], [0, 0, 0, 1], 0.0)
        result, info = pose_filter.process([1.0, 0.0, 0.5], [0, 0, 1, 0], 1.0)
        self.assertTrue(info["reacquired"])
        np.testing.assert_allclose(result["translation_m"], [1.0, 0.0, 0.5])

    def test_non_monotonic_timestamp_is_rejected(self):
        pose_filter = PoseFilter(DEFAULTS)
        pose_filter.process([0.2, 0.0, 0.5], [0, 0, 0, 1], 1.0)
        with self.assertRaises(FilterRejection) as raised:
            pose_filter.process([0.2, 0.0, 0.5], [0, 0, 0, 1], 0.9)
        self.assertEqual(raised.exception.reason, "non_monotonic_timestamp")

    def test_quaternion_angle_ignores_double_cover_sign(self):
        self.assertAlmostEqual(
            quaternion_angle_deg([0, 0, 0, 1], [0, 0, 0, -1]), 0.0, places=8
        )


if __name__ == "__main__":
    unittest.main()
