import math
import unittest

from openmv_camera.visualization import (
    square_outline_points, validate_visualization_settings,
)


class VisualizationGeometryTest(unittest.TestCase):
    def test_outline_has_four_segments_and_real_size_extent(self):
        points = square_outline_points(0.099)
        self.assertEqual(len(points), 8)
        self.assertAlmostEqual(max(p[0] for p in points) - min(p[0] for p in points), 0.099)
        self.assertAlmostEqual(max(p[1] for p in points) - min(p[1] for p in points), 0.099)
        self.assertTrue(all(p[2] == 0.0 for p in points))

    def test_each_line_segment_has_target_side_length(self):
        points = square_outline_points(0.050)
        for index in range(0, 8, 2):
            start, end = points[index:index + 2]
            length = math.dist(start, end)
            self.assertAlmostEqual(length, 0.050)

    def test_invalid_target_size_is_rejected(self):
        for value in (0.0, -0.1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                square_outline_points(value)

    def test_display_settings_are_validated(self):
        valid = {
            "display_thickness_m": 0.001,
            "line_width_m": 0.002,
            "base_frame": "base_link",
        }
        validate_visualization_settings(valid)
        for key in ("display_thickness_m", "line_width_m"):
            with self.assertRaises(ValueError):
                validate_visualization_settings(dict(valid, **{key: 0.0}))
        with self.assertRaises(ValueError):
            validate_visualization_settings(dict(valid, base_frame=""))


if __name__ == "__main__":
    unittest.main()
