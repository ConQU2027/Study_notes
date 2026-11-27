"""Timestamp-driven One Euro position filtering and quaternion SLERP."""

from math import acos, exp, pi, sin
from typing import Dict, Optional, Tuple

import numpy as np


class FilterRejection(ValueError):
    def __init__(self, reason: str, metrics: Dict):
        super().__init__(reason)
        self.reason = reason
        self.metrics = metrics


def normalize_quaternion(quaternion_xyzw) -> np.ndarray:
    quaternion = np.asarray(quaternion_xyzw, dtype=np.float64).reshape(4)
    norm = float(np.linalg.norm(quaternion))
    if not np.isfinite(norm) or norm <= 1e-12:
        raise ValueError("quaternion must be finite and non-zero")
    return quaternion / norm


def quaternion_angle_deg(first, second) -> float:
    dot = abs(float(np.dot(normalize_quaternion(first), normalize_quaternion(second))))
    return 2.0 * acos(float(np.clip(dot, -1.0, 1.0))) * 180.0 / pi


def slerp_quaternion(first, second, alpha: float) -> np.ndarray:
    first = normalize_quaternion(first)
    second = normalize_quaternion(second)
    dot = float(np.dot(first, second))
    if dot < 0:
        second = -second
        dot = -dot
    alpha = float(np.clip(alpha, 0.0, 1.0))
    if dot > 0.9995:
        return normalize_quaternion(first + alpha * (second - first))
    theta = acos(float(np.clip(dot, -1.0, 1.0)))
    sine = sin(theta)
    return normalize_quaternion(
        sin((1.0 - alpha) * theta) / sine * first
        + sin(alpha * theta) / sine * second
    )


def validate_filter_settings(values: Dict) -> None:
    for key in (
        "position_min_cutoff_hz", "position_derivative_cutoff_hz",
        "orientation_tau_sec", "max_position_jump_m",
        "max_rotation_jump_deg", "reacquire_timeout_sec",
    ):
        if not np.isfinite(values[key]) or values[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if not np.isfinite(values["position_beta"]) or values["position_beta"] < 0:
        raise ValueError("position_beta must be non-negative and finite")
    if values["max_rotation_jump_deg"] > 180:
        raise ValueError("max_rotation_jump_deg must not exceed 180")


class OneEuroPosition:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._previous_raw: Optional[np.ndarray] = None
        self._previous_filtered: Optional[np.ndarray] = None
        self._previous_derivative = np.zeros(3, dtype=np.float64)
        self._previous_stamp: Optional[float] = None

    @staticmethod
    def _alpha(cutoff_hz: float, dt: float) -> float:
        time_constant = 1.0 / (2.0 * pi * cutoff_hz)
        return 1.0 / (1.0 + time_constant / dt)

    def filter(self, value, stamp_sec: float, settings: Dict) -> np.ndarray:
        value = np.asarray(value, dtype=np.float64).reshape(3)
        if not np.all(np.isfinite(value)):
            raise ValueError("position must be finite")
        if self._previous_raw is None:
            self._previous_raw = value.copy()
            self._previous_filtered = value.copy()
            self._previous_stamp = stamp_sec
            return value.copy()
        dt = stamp_sec - self._previous_stamp
        if not np.isfinite(dt) or dt <= 0:
            raise FilterRejection("non_monotonic_timestamp", {"dt_sec": dt})
        raw_derivative = (value - self._previous_raw) / dt
        derivative_alpha = self._alpha(settings["position_derivative_cutoff_hz"], dt)
        derivative = derivative_alpha * raw_derivative + (
            1.0 - derivative_alpha
        ) * self._previous_derivative
        cutoff = settings["position_min_cutoff_hz"] + settings["position_beta"] * float(
            np.linalg.norm(derivative)
        )
        alpha = self._alpha(cutoff, dt)
        filtered = alpha * value + (1.0 - alpha) * self._previous_filtered
        self._previous_raw = value.copy()
        self._previous_derivative = derivative
        self._previous_filtered = filtered.copy()
        self._previous_stamp = stamp_sec
        return filtered


class PoseFilter:
    def __init__(self, settings: Dict):
        self.settings = dict(settings)
        self._position = OneEuroPosition()
        self._quaternion: Optional[np.ndarray] = None
        self._last_accepted_stamp: Optional[float] = None

    def reset(self) -> None:
        self._position.reset()
        self._quaternion = None
        self._last_accepted_stamp = None

    @property
    def initialized(self) -> bool:
        return self._quaternion is not None

    def process(self, translation, quaternion_xyzw, stamp_sec: float) -> Tuple[Dict, Dict]:
        validate_filter_settings(self.settings)
        translation = np.asarray(translation, dtype=np.float64).reshape(3)
        quaternion = normalize_quaternion(quaternion_xyzw)
        if not np.all(np.isfinite(translation)) or not np.isfinite(stamp_sec):
            raise ValueError("pose and timestamp must be finite")

        reacquired = False
        if self._last_accepted_stamp is not None:
            gap = stamp_sec - self._last_accepted_stamp
            if gap <= 0:
                raise FilterRejection("non_monotonic_timestamp", {"dt_sec": gap})
            if gap > self.settings["reacquire_timeout_sec"]:
                self.reset()
                reacquired = True

        if not self.initialized:
            self._position.filter(translation, stamp_sec, self.settings)
            self._quaternion = quaternion.copy()
            self._last_accepted_stamp = stamp_sec
            result = {"translation_m": translation.copy(), "quaternion_xyzw": quaternion.copy()}
            return result, {
                "initialized": True, "reacquired": reacquired,
                "dt_sec": 0.0, "position_jump_m": 0.0,
                "rotation_jump_deg": 0.0, "orientation_alpha": 1.0,
            }

        dt = stamp_sec - self._last_accepted_stamp
        position_jump = float(np.linalg.norm(translation - self._position._previous_filtered))
        rotation_jump = quaternion_angle_deg(self._quaternion, quaternion)
        metrics = {
            "dt_sec": dt, "position_jump_m": position_jump,
            "rotation_jump_deg": rotation_jump,
        }
        if position_jump > self.settings["max_position_jump_m"]:
            raise FilterRejection("position_outlier", metrics)
        if rotation_jump > self.settings["max_rotation_jump_deg"]:
            raise FilterRejection("orientation_outlier", metrics)

        filtered_translation = self._position.filter(translation, stamp_sec, self.settings)
        orientation_alpha = 1.0 - exp(-dt / self.settings["orientation_tau_sec"])
        filtered_quaternion = slerp_quaternion(self._quaternion, quaternion, orientation_alpha)
        self._quaternion = filtered_quaternion
        self._last_accepted_stamp = stamp_sec
        result = {
            "translation_m": filtered_translation,
            "quaternion_xyzw": filtered_quaternion,
        }
        return result, {
            "initialized": False, "reacquired": False,
            "orientation_alpha": orientation_alpha, **metrics,
        }
