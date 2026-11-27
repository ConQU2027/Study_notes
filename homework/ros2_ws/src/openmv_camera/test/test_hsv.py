import unittest

import numpy as np

from openmv_camera.hsv import hsv_mask_bgr, validate_thresholds


DEFAULTS = {
    "h_min": 0,
    "h_max": 179,
    "s_min": 0,
    "s_max": 70,
    "v_min": 180,
    "v_max": 255,
}


class HsvThresholdTest(unittest.TestCase):
    def test_white_is_selected_and_saturated_color_is_rejected(self):
        bgr = np.array([[[255, 255, 255], [0, 0, 255]]], dtype=np.uint8)
        mask = hsv_mask_bgr(bgr, DEFAULTS)
        self.assertEqual(mask.tolist(), [[255, 0]])

    def test_dark_white_is_rejected_by_value_threshold(self):
        bgr = np.full((2, 2, 3), 120, dtype=np.uint8)
        self.assertEqual(int(hsv_mask_bgr(bgr, DEFAULTS).sum()), 0)

    def test_invalid_range_is_rejected(self):
        values = dict(DEFAULTS, s_min=80, s_max=70)
        with self.assertRaises(ValueError):
            validate_thresholds(values)


if __name__ == "__main__":
    unittest.main()
