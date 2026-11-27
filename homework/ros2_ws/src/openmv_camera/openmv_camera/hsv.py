"""Pure OpenCV HSV thresholding, kept independent of ROS for unit tests."""

from typing import Dict, Tuple

import cv2
import numpy as np

HSV_LIMITS = {
    "h_min": (0, 179),
    "h_max": (0, 179),
    "s_min": (0, 255),
    "s_max": (0, 255),
    "v_min": (0, 255),
    "v_max": (0, 255),
}


def validate_thresholds(values: Dict[str, int]) -> None:
    for key, (minimum, maximum) in HSV_LIMITS.items():
        value = values[key]
        if not minimum <= value <= maximum:
            raise ValueError(f"{key} must be in [{minimum}, {maximum}]")
    for channel in ("h", "s", "v"):
        if values[f"{channel}_min"] > values[f"{channel}_max"]:
            raise ValueError(f"{channel}_min must not exceed {channel}_max")


def threshold_bounds(values: Dict[str, int]) -> Tuple[np.ndarray, np.ndarray]:
    validate_thresholds(values)
    lower = np.array([values["h_min"], values["s_min"], values["v_min"]], dtype=np.uint8)
    upper = np.array([values["h_max"], values["s_max"], values["v_max"]], dtype=np.uint8)
    return lower, upper


def hsv_mask_bgr(bgr: np.ndarray, values: Dict[str, int]) -> np.ndarray:
    if bgr.ndim != 3 or bgr.shape[2] != 3 or bgr.dtype != np.uint8:
        raise ValueError("bgr must be a uint8 HxWx3 image")
    lower, upper = threshold_bounds(values)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, lower, upper)
