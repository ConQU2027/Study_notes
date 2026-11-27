import unittest

import cv2
import numpy as np

from openmv_camera.pose import (
    compose_transform, estimate_square_pose, quaternion_to_rotation_matrix,
    rotation_matrix_to_quaternion, rpy_to_quaternion, square_object_points,
)


K = np.array([[271.0, 0.0, 160.0], [0.0, 270.0, 120.0], [0.0, 0.0, 1.0]])
D = np.zeros(5)


def projected_square(rvec, translation):
    points, _ = cv2.projectPoints(square_object_points(0.099), rvec, translation, K, D)
    return points.reshape(4, 2)


class PoseTest(unittest.TestCase):
    def test_object_points_use_metres_and_known_side_length(self):
        points = square_object_points(0.099)
        self.assertEqual(points.shape, (4, 3))
        self.assertAlmostEqual(np.linalg.norm(points[1] - points[0]), 0.099)
        self.assertTrue(np.all(points[:, 2] == 0))

    def test_assumed_mount_rpy_maps_optical_axes_to_base_axes(self):
        quaternion = rpy_to_quaternion(-np.pi / 2, 0, -np.pi / 2)
        rotation = quaternion_to_rotation_matrix(quaternion)
        expected = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]], dtype=float)
        np.testing.assert_allclose(rotation, expected, atol=1e-12)
        recovered = rotation_matrix_to_quaternion(rotation)
        self.assertAlmostEqual(abs(float(np.dot(recovered, quaternion))), 1.0, places=12)

    def test_compose_transform_places_forward_target_ahead_of_base(self):
        mount_rotation = quaternion_to_rotation_matrix(
            rpy_to_quaternion(-np.pi / 2, 0, -np.pi / 2)
        )
        rotation, translation = compose_transform(
            mount_rotation, np.array([0.2, 0.0, 0.1]),
            np.eye(3), np.array([0.0, 0.0, 0.5]),
        )
        np.testing.assert_allclose(rotation, mount_rotation, atol=1e-12)
        np.testing.assert_allclose(translation, [0.7, 0.0, 0.1], atol=1e-12)

    def test_frontoparallel_square_recovers_translation(self):
        translation = np.array([0.02, -0.01, 0.5])
        vertices = projected_square(np.zeros(3), translation)
        pose, info = estimate_square_pose(vertices, 0.099, K, D)
        self.assertIsNotNone(pose, info)
        np.testing.assert_allclose(pose["translation_m"], translation, atol=1e-4)
        self.assertLess(pose["reprojection_error_px"], 0.01)
        self.assertGreaterEqual(info["candidate_count"], 1)

    def test_tilted_square_has_positive_depth_and_low_reprojection(self):
        rvec = np.array([0.20, -0.10, 0.08])
        translation = np.array([-0.02, 0.015, 0.6])
        vertices = projected_square(rvec, translation)
        pose, info = estimate_square_pose(vertices, 0.099, K, D)
        self.assertIsNotNone(pose, info)
        np.testing.assert_allclose(pose["translation_m"], translation, atol=2e-4)
        self.assertLess(pose["reprojection_error_px"], 0.02)

    def test_previous_rotation_participates_in_candidate_selection(self):
        vertices = projected_square(np.zeros(3), np.array([0.0, 0.0, 0.5]))
        pose, info = estimate_square_pose(
            vertices, 0.099, K, D, previous_rvec=np.zeros(3)
        )
        self.assertIsNotNone(pose)
        self.assertTrue(info["previous_pose_used"])
        self.assertEqual(info["selection"], "previous_rotation_then_reprojection")

    def test_large_reprojection_error_is_rejected(self):
        vertices = projected_square(np.zeros(3), np.array([0.0, 0.0, 0.5]))
        vertices[0] += [25.0, -18.0]
        pose, info = estimate_square_pose(
            vertices, 0.099, K, D, max_reprojection_error_px=0.01
        )
        self.assertIsNone(pose)
        self.assertEqual(info["valid_candidate_count"], 0)

    def test_invalid_target_size_is_rejected(self):
        with self.assertRaises(ValueError):
            square_object_points(0.0)


if __name__ == "__main__":
    unittest.main()
