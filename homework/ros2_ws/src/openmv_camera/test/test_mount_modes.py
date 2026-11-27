import unittest

import numpy as np

from openmv_camera.pose import (
    compose_transform, validate_mount_tf_mode,
)


class MountModeTest(unittest.TestCase):
    def test_supported_modes_are_accepted(self):
        self.assertEqual(validate_mount_tf_mode("assumed_static"), "assumed_static")
        self.assertEqual(validate_mount_tf_mode("external"), "external")

    def test_invalid_mode_is_rejected(self):
        for value in ("", "static", "dynamic", None, 1):
            with self.assertRaises(ValueError):
                validate_mount_tf_mode(value)

    def test_changing_external_mount_changes_base_pose(self):
        rotation = np.eye(3)
        camera_target_rotation = np.eye(3)
        camera_target_translation = np.array([0.0, 0.0, 0.5])
        _, first = compose_transform(
            rotation, np.array([0.20, 0.0, 0.10]),
            camera_target_rotation, camera_target_translation,
        )
        _, second = compose_transform(
            rotation, np.array([0.25, 0.02, 0.12]),
            camera_target_rotation, camera_target_translation,
        )
        np.testing.assert_allclose(first, [0.20, 0.0, 0.60])
        np.testing.assert_allclose(second, [0.25, 0.02, 0.62])


if __name__ == "__main__":
    unittest.main()
