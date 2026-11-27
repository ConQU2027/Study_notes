"""Planar square IPPE pose and rigid-transform helpers, independent of ROS."""

from math import acos, cos, sin, sqrt
from typing import Dict, Optional, Tuple

import cv2
import numpy as np


MOUNT_TF_MODES = ("assumed_static", "external")


def validate_mount_tf_mode(mode: str) -> str:
    if not isinstance(mode, str) or mode not in MOUNT_TF_MODES:
        raise ValueError(f"mount_tf_mode must be one of {MOUNT_TF_MODES}")
    return mode


def square_object_points(target_size_m: float) -> np.ndarray:
    """Centered square in meters; +z points away from the visible front face."""
    if not np.isfinite(target_size_m) or not 0.001 <= target_size_m <= 2.0:
        raise ValueError("target_size_m must be finite and in [0.001, 2.0]")
    half = target_size_m / 2.0
    return np.array([
        [-half, -half, 0.0],
        [half, -half, 0.0],
        [half, half, 0.0],
        [-half, half, 0.0],
    ], dtype=np.float64)


def quaternion_to_rotation_matrix(quaternion_xyzw) -> np.ndarray:
    quaternion = np.asarray(quaternion_xyzw, dtype=np.float64).reshape(4)
    norm = float(np.linalg.norm(quaternion))
    if norm <= 1e-12:
        raise ValueError("quaternion must be non-zero")
    x, y, z, w = quaternion / norm
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)


def rotation_matrix_to_quaternion(rotation: np.ndarray) -> np.ndarray:
    matrix = np.asarray(rotation, dtype=np.float64).reshape(3, 3)
    trace = float(np.trace(matrix))
    if trace > 0:
        scale = sqrt(trace + 1.0) * 2
        w = 0.25 * scale
        x = (matrix[2, 1] - matrix[1, 2]) / scale
        y = (matrix[0, 2] - matrix[2, 0]) / scale
        z = (matrix[1, 0] - matrix[0, 1]) / scale
    elif matrix[0, 0] > matrix[1, 1] and matrix[0, 0] > matrix[2, 2]:
        scale = sqrt(max(1e-15, 1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2])) * 2
        w = (matrix[2, 1] - matrix[1, 2]) / scale
        x = 0.25 * scale
        y = (matrix[0, 1] + matrix[1, 0]) / scale
        z = (matrix[0, 2] + matrix[2, 0]) / scale
    elif matrix[1, 1] > matrix[2, 2]:
        scale = sqrt(max(1e-15, 1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2])) * 2
        w = (matrix[0, 2] - matrix[2, 0]) / scale
        x = (matrix[0, 1] + matrix[1, 0]) / scale
        y = 0.25 * scale
        z = (matrix[1, 2] + matrix[2, 1]) / scale
    else:
        scale = sqrt(max(1e-15, 1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1])) * 2
        w = (matrix[1, 0] - matrix[0, 1]) / scale
        x = (matrix[0, 2] + matrix[2, 0]) / scale
        y = (matrix[1, 2] + matrix[2, 1]) / scale
        z = 0.25 * scale
    quaternion = np.array([x, y, z, w], dtype=np.float64)
    return quaternion / np.linalg.norm(quaternion)


def rpy_to_quaternion(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """ROS fixed-axis roll/pitch/yaw to xyzw quaternion."""
    cr, sr = cos(roll / 2), sin(roll / 2)
    cp, sp = cos(pitch / 2), sin(pitch / 2)
    cy, sy = cos(yaw / 2), sin(yaw / 2)
    return np.array([
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
        cr * cp * cy + sr * sp * sy,
    ], dtype=np.float64)


def compose_transform(
    rotation_ab: np.ndarray, translation_ab: np.ndarray,
    rotation_bc: np.ndarray, translation_bc: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    rotation_ac = rotation_ab @ rotation_bc
    translation_ac = translation_ab + rotation_ab @ translation_bc
    return rotation_ac, translation_ac


def _rotation_distance(first: np.ndarray, second: np.ndarray) -> float:
    relative = first.T @ second
    cosine = float(np.clip((np.trace(relative) - 1.0) / 2.0, -1.0, 1.0))
    return acos(cosine)


def estimate_square_pose(
    vertices, target_size_m: float, camera_matrix, distortion_coefficients,
    max_reprojection_error_px: float = 8.0, min_positive_depth_m: float = 0.02,
    previous_rvec: Optional[np.ndarray] = None,
) -> Tuple[Optional[Dict], Dict]:
    """Select an IPPE candidate by validity, reprojection and optional rotation continuity."""
    if not np.isfinite(max_reprojection_error_px) or max_reprojection_error_px <= 0:
        raise ValueError("max_reprojection_error_px must be positive and finite")
    if not np.isfinite(min_positive_depth_m) or min_positive_depth_m <= 0:
        raise ValueError("min_positive_depth_m must be positive and finite")
    image_points = np.asarray(vertices, dtype=np.float64).reshape(4, 2)
    camera_matrix = np.asarray(camera_matrix, dtype=np.float64).reshape(3, 3)
    if camera_matrix[0, 0] <= 0 or camera_matrix[1, 1] <= 0:
        raise ValueError("camera focal lengths must be positive")
    distortion = np.asarray(distortion_coefficients, dtype=np.float64).reshape(-1)
    distortion = None if distortion.size == 0 else distortion
    object_points = square_object_points(target_size_m)

    pnp_output = cv2.solvePnPGeneric(
        object_points, image_points, camera_matrix, distortion, flags=cv2.SOLVEPNP_IPPE
    )
    if len(pnp_output) == 4:
        _, rvecs, tvecs, _ = pnp_output
    elif len(pnp_output) == 3:
        rvecs, tvecs, _ = pnp_output
    elif len(pnp_output) == 2:
        rvecs, tvecs = pnp_output
    else:
        raise ValueError("Unexpected solvePnPGeneric return signature")
    rejected = {"positive_depth": 0, "visible_face": 0, "reprojection": 0}
    candidates = []
    for index, (rvec, tvec) in enumerate(zip(rvecs, tvecs)):
        rotation, _ = cv2.Rodrigues(rvec)
        translation = tvec.reshape(3).astype(np.float64)
        camera_points = (rotation @ object_points.T).T + translation
        if not np.all(camera_points[:, 2] > min_positive_depth_m):
            rejected["positive_depth"] += 1
            continue
        camera_center_in_target = -rotation.T @ translation
        if camera_center_in_target[2] >= 0:
            rejected["visible_face"] += 1
            continue
        projected, _ = cv2.projectPoints(
            object_points, rvec, tvec, camera_matrix, distortion
        )
        error = float(np.sqrt(np.mean(np.sum(
            (projected.reshape(4, 2) - image_points) ** 2, axis=1
        ))))
        if error > max_reprojection_error_px:
            rejected["reprojection"] += 1
            continue
        candidates.append({
            "source_index": index,
            "rvec": rvec.reshape(3).astype(np.float64),
            "tvec": translation,
            "rotation_matrix": rotation,
            "reprojection_error_px": error,
        })

    errors = sorted(candidate["reprojection_error_px"] for candidate in candidates)
    ambiguous = len(errors) >= 2 and errors[1] <= errors[0] * 1.2 + 0.1
    info = {
        "candidate_count": len(rvecs),
        "valid_candidate_count": len(candidates),
        "rejected_candidates": rejected,
        "reprojection_errors_px": [round(error, 5) for error in errors],
        "planar_ambiguous": ambiguous,
        "previous_pose_used": previous_rvec is not None,
    }
    if not candidates:
        return None, info

    if previous_rvec is not None:
        previous_rotation, _ = cv2.Rodrigues(np.asarray(previous_rvec).reshape(3, 1))
        selected = min(candidates, key=lambda candidate: (
            _rotation_distance(previous_rotation, candidate["rotation_matrix"]),
            candidate["reprojection_error_px"],
        ))
        info["selection"] = "previous_rotation_then_reprojection"
    else:
        selected = min(candidates, key=lambda candidate: candidate["reprojection_error_px"])
        info["selection"] = "minimum_reprojection"
    info["selected_source_index"] = selected["source_index"]

    result = dict(selected)
    result["translation_m"] = selected["tvec"].copy()
    result["quaternion_xyzw"] = rotation_matrix_to_quaternion(selected["rotation_matrix"])
    return result, info
