"""Morphology and single-frame square geometry checks, independent of ROS."""

from math import acos, degrees
from typing import Dict, List, Tuple

import cv2
import numpy as np


def validate_settings(values: Dict) -> None:
    kernel = values["morph_kernel_size"]
    if not isinstance(kernel, (int, np.integer)) or not 1 <= kernel <= 31 or kernel % 2 == 0:
        raise ValueError("morph_kernel_size must be an odd integer in [1, 31]")
    for key in ("morph_open_iterations", "morph_close_iterations"):
        value = values[key]
        if not isinstance(value, (int, np.integer)) or not 0 <= value <= 10:
            raise ValueError(f"{key} must be an integer in [0, 10]")
    if not 0 <= values["min_area_px"]:
        raise ValueError("min_area_px must be non-negative")
    if not 0 < values["max_area_ratio"] <= 1:
        raise ValueError("max_area_ratio must be in (0, 1]")
    if not 0 < values["approx_epsilon_ratio"] <= 0.2:
        raise ValueError("approx_epsilon_ratio must be in (0, 0.2]")
    if not 1 <= values["aspect_ratio_max"] <= 10:
        raise ValueError("aspect_ratio_max must be in [1, 10]")
    minimum = values["min_angle_deg"]
    maximum = values["max_angle_deg"]
    if not 0 < minimum < maximum < 180:
        raise ValueError("angle limits must satisfy 0 < min < max < 180")


def order_quad(points: np.ndarray) -> np.ndarray:
    """Return cyclic vertices without the sum/diff diamond-corner ambiguity."""
    quad = np.asarray(points, dtype=np.float32).reshape(4, 2)
    center = quad.mean(axis=0)
    angles = np.arctan2(quad[:, 1] - center[1], quad[:, 0] - center[0])
    return quad[np.argsort(angles)]


def quad_metrics(quad: np.ndarray) -> Dict[str, object]:
    ordered = order_quad(quad)
    sides = np.linalg.norm(np.roll(ordered, -1, axis=0) - ordered, axis=1)
    if float(sides.min()) <= 1e-6:
        raise ValueError("quadrilateral has a zero-length side")
    angles = []
    for index in range(4):
        point = ordered[index]
        first = ordered[index - 1] - point
        second = ordered[(index + 1) % 4] - point
        cosine = float(np.dot(first, second) / (np.linalg.norm(first) * np.linalg.norm(second)))
        angles.append(degrees(acos(float(np.clip(cosine, -1.0, 1.0)))))
    return {
        "ordered": ordered,
        "aspect_ratio": float(sides.max() / sides.min()),
        "angle_min_deg": float(min(angles)),
        "angle_max_deg": float(max(angles)),
    }


def detect_squares(mask: np.ndarray, values: Dict) -> Tuple[np.ndarray, List[Dict], Dict]:
    if mask.ndim != 2 or mask.dtype != np.uint8 or mask.size == 0:
        raise ValueError("mask must be a non-empty uint8 HxW image")
    validate_settings(values)

    kernel = np.ones((values["morph_kernel_size"], values["morph_kernel_size"]), dtype=np.uint8)
    cleaned = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, kernel, iterations=values["morph_open_iterations"]
    )
    cleaned = cv2.morphologyEx(
        cleaned, cv2.MORPH_CLOSE, kernel, iterations=values["morph_close_iterations"]
    )
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    maximum_area = mask.shape[0] * mask.shape[1] * values["max_area_ratio"]
    rejected = {key: 0 for key in ("area", "vertices", "convexity", "aspect_ratio", "angles")}
    targets = []
    filtered = np.zeros_like(mask)

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < values["min_area_px"] or area > maximum_area:
            rejected["area"] += 1
            continue
        perimeter = float(cv2.arcLength(contour, True))
        approximation = cv2.approxPolyDP(
            contour, values["approx_epsilon_ratio"] * perimeter, True
        )
        if len(approximation) != 4:
            rejected["vertices"] += 1
            continue
        if not cv2.isContourConvex(approximation):
            rejected["convexity"] += 1
            continue
        metrics = quad_metrics(approximation.reshape(4, 2))
        if metrics["aspect_ratio"] > values["aspect_ratio_max"]:
            rejected["aspect_ratio"] += 1
            continue
        if (
            metrics["angle_min_deg"] < values["min_angle_deg"]
            or metrics["angle_max_deg"] > values["max_angle_deg"]
        ):
            rejected["angles"] += 1
            continue

        ordered = metrics["ordered"]
        vertices = np.rint(ordered).astype(np.int32)
        center = ordered.mean(axis=0)
        targets.append({
            "area_px": area,
            "perimeter_px": perimeter,
            "center_px": [round(float(center[0]), 2), round(float(center[1]), 2)],
            "vertices": vertices.tolist(),
            "aspect_ratio": round(metrics["aspect_ratio"], 4),
            "angle_min_deg": round(metrics["angle_min_deg"], 2),
            "angle_max_deg": round(metrics["angle_max_deg"], 2),
        })
        cv2.fillPoly(filtered, [vertices], 255)

    targets.sort(key=lambda target: target["area_px"], reverse=True)
    info = {
        "contours_total": len(contours),
        "target_count": len(targets),
        "rejected": rejected,
    }
    return filtered, targets, info
