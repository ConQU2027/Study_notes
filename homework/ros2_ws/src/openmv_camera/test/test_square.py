import unittest

import cv2
import numpy as np

from openmv_camera.square import detect_squares, quad_metrics, validate_settings


DEFAULTS = {
    "morph_kernel_size": 3,
    "morph_open_iterations": 1,
    "morph_close_iterations": 1,
    "min_area_px": 100.0,
    "max_area_ratio": 0.9,
    "approx_epsilon_ratio": 0.04,
    "aspect_ratio_max": 1.4,
    "min_angle_deg": 70.0,
    "max_angle_deg": 110.0,
}


def mask_with_polygon(points):
    mask = np.zeros((180, 220), dtype=np.uint8)
    cv2.fillPoly(mask, [np.asarray(points, dtype=np.int32)], 255)
    return mask


class SquareDetectionTest(unittest.TestCase):
    def test_axis_aligned_square_is_accepted(self):
        mask = mask_with_polygon([(30, 30), (110, 30), (110, 110), (30, 110)])
        filtered, targets, info = detect_squares(mask, DEFAULTS)
        self.assertEqual(info["target_count"], 1)
        self.assertEqual(len(targets[0]["vertices"]), 4)
        self.assertAlmostEqual(targets[0]["aspect_ratio"], 1.0, places=2)
        self.assertAlmostEqual(targets[0]["angle_min_deg"], 90.0, delta=1.0)
        self.assertGreater(cv2.countNonZero(filtered), 0)

    def test_diamond_has_unambiguous_cyclic_geometry(self):
        diamond = np.array([(100, 20), (180, 100), (100, 180), (20, 100)], dtype=np.float32)
        metrics = quad_metrics(diamond)
        self.assertAlmostEqual(metrics["aspect_ratio"], 1.0, places=3)
        self.assertAlmostEqual(metrics["angle_min_deg"], 90.0, places=3)
        self.assertAlmostEqual(metrics["angle_max_deg"], 90.0, places=3)

    def test_long_rectangle_is_rejected_by_aspect_ratio(self):
        mask = mask_with_polygon([(20, 40), (180, 40), (180, 80), (20, 80)])
        _, targets, info = detect_squares(mask, DEFAULTS)
        self.assertEqual(targets, [])
        self.assertEqual(info["rejected"]["aspect_ratio"], 1)

    def test_triangle_is_rejected_by_vertex_count(self):
        mask = mask_with_polygon([(30, 140), (100, 20), (170, 140)])
        _, targets, info = detect_squares(mask, DEFAULTS)
        self.assertEqual(targets, [])
        self.assertEqual(info["rejected"]["vertices"], 1)

    def test_opening_removes_isolated_noise(self):
        mask = mask_with_polygon([(30, 30), (110, 30), (110, 110), (30, 110)])
        mask[5, 5] = 255
        _, targets, info = detect_squares(mask, DEFAULTS)
        self.assertEqual(len(targets), 1)
        self.assertEqual(info["contours_total"], 1)

    def test_skewed_quadrilateral_is_rejected_by_angles(self):
        mask = mask_with_polygon([(20, 40), (120, 40), (170, 120), (70, 120)])
        _, targets, info = detect_squares(mask, DEFAULTS)
        self.assertEqual(targets, [])
        self.assertEqual(info["rejected"]["angles"], 1)

    def test_invalid_kernel_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_settings(dict(DEFAULTS, morph_kernel_size=4))


if __name__ == "__main__":
    unittest.main()
