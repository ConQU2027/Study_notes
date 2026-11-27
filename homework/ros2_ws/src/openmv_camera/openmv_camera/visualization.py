"""ROS-independent geometry for the real-size square target display."""

import numpy as np


def validate_target_size(target_size_m: float) -> float:
    size = float(target_size_m)
    if not np.isfinite(size) or size <= 0:
        raise ValueError("target_size_m must be positive and finite")
    return size


def validate_visualization_settings(values: dict) -> None:
    for key in ("display_thickness_m", "line_width_m"):
        if not np.isfinite(values[key]) or values[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if not isinstance(values["base_frame"], str) or not values["base_frame"].strip():
        raise ValueError("base_frame must be a non-empty string")


def square_outline_points(target_size_m: float):
    """Return four LINE_LIST segments on z=0, centred in the target frame."""
    half = validate_target_size(target_size_m) / 2.0
    corners = [
        (-half, -half, 0.0),
        (half, -half, 0.0),
        (half, half, 0.0),
        (-half, half, 0.0),
    ]
    points = []
    for index, start in enumerate(corners):
        points.extend((start, corners[(index + 1) % 4]))
    return points
