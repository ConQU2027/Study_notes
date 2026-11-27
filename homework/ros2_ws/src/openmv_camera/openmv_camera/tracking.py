"""Timestamped multi-target association with bounded occlusion memory."""

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np


@dataclass
class Track:
    track_id: int
    center_px: np.ndarray
    area_px: float
    last_stamp_sec: float
    hits: int = 1
    missed_frames: int = 0
    velocity_px_sec: Optional[np.ndarray] = None
    state: str = "tentative"

    def predicted_center(self, stamp_sec: float) -> np.ndarray:
        if self.velocity_px_sec is None:
            return self.center_px.copy()
        return self.center_px + self.velocity_px_sec * (stamp_sec - self.last_stamp_sec)


def validate_tracking_settings(values: Dict) -> None:
    for key in ("max_association_distance_px", "track_timeout_sec"):
        if not np.isfinite(values[key]) or values[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if not np.isfinite(values["max_area_ratio"]) or values["max_area_ratio"] < 1:
        raise ValueError("max_area_ratio must be finite and at least 1")
    if not 0 <= values["velocity_alpha"] <= 1:
        raise ValueError("velocity_alpha must be in [0, 1]")
    for key in ("min_hits", "max_missed_frames"):
        value = values[key]
        if not isinstance(value, (int, np.integer)) or isinstance(value, (bool, np.bool_)):
            raise ValueError(f"{key} must be an integer")
    if not 1 <= values["min_hits"] <= 20:
        raise ValueError("min_hits must be in [1, 20]")
    if not 0 <= values["max_missed_frames"] <= 100:
        raise ValueError("max_missed_frames must be in [0, 100]")


def _validate_detections(targets) -> List[Dict]:
    if not isinstance(targets, list):
        raise ValueError("targets must be a list")
    detections = []
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("each target must be a dictionary")
        center = np.asarray(target["center_px"], dtype=np.float64).reshape(2)
        area = float(target["area_px"])
        if not np.all(np.isfinite(center)) or not np.isfinite(area) or area <= 0:
            raise ValueError("target center and area must be finite; area must be positive")
        copied = dict(target)
        copied["_center"] = center
        copied["_area"] = area
        detections.append(copied)
    return detections


class TemporalTracker:
    """Greedy globally distance-ordered, one-to-one image-space association."""

    def __init__(self, settings: Dict):
        self.settings = dict(settings)
        validate_tracking_settings(self.settings)
        self._tracks: List[Track] = []
        self._next_id = 1
        self._last_stamp: Optional[float] = None
        self.created_total = 0
        self.lost_total = 0
        self.reacquired_total = 0

    def reset(self) -> None:
        self._tracks.clear()
        self._last_stamp = None

    def _new_track(self, detection: Dict, stamp_sec: float) -> Track:
        track = Track(
            track_id=self._next_id,
            center_px=detection["_center"].copy(),
            area_px=detection["_area"],
            last_stamp_sec=stamp_sec,
            state="tracked" if self.settings["min_hits"] == 1 else "tentative",
        )
        self._next_id += 1
        self.created_total += 1
        self._tracks.append(track)
        return track

    def update(self, targets, stamp_sec: float) -> Dict:
        validate_tracking_settings(self.settings)
        stamp_sec = float(stamp_sec)
        if not np.isfinite(stamp_sec):
            raise ValueError("tracking timestamp must be finite")
        if self._last_stamp is not None and stamp_sec <= self._last_stamp:
            raise ValueError("tracking timestamps must be strictly increasing")
        detections = _validate_detections(targets)

        candidates = []
        for track_index, track in enumerate(self._tracks):
            predicted = track.predicted_center(stamp_sec)
            for detection_index, detection in enumerate(detections):
                distance = float(np.linalg.norm(detection["_center"] - predicted))
                area_ratio = max(track.area_px, detection["_area"]) / min(
                    track.area_px, detection["_area"]
                )
                if (
                    distance <= self.settings["max_association_distance_px"]
                    and area_ratio <= self.settings["max_area_ratio"]
                ):
                    candidates.append((
                        distance, track.track_id, track_index, detection_index, area_ratio,
                    ))
        candidates.sort(key=lambda item: (item[0], item[1], item[3]))

        matched_tracks = set()
        matched_detections = set()
        visible = []
        for distance, _, track_index, detection_index, area_ratio in candidates:
            if track_index in matched_tracks or detection_index in matched_detections:
                continue
            matched_tracks.add(track_index)
            matched_detections.add(detection_index)
            track = self._tracks[track_index]
            detection = detections[detection_index]
            dt = stamp_sec - track.last_stamp_sec
            measured_velocity = (detection["_center"] - track.center_px) / dt
            alpha = self.settings["velocity_alpha"]
            if track.velocity_px_sec is None:
                track.velocity_px_sec = measured_velocity
            else:
                track.velocity_px_sec = (
                    alpha * measured_velocity + (1.0 - alpha) * track.velocity_px_sec
                )
            was_occluded = track.missed_frames > 0
            track.center_px = detection["_center"].copy()
            track.area_px = detection["_area"]
            track.last_stamp_sec = stamp_sec
            track.hits += 1
            track.missed_frames = 0
            track.state = "tracked" if track.hits >= self.settings["min_hits"] else "tentative"
            if was_occluded and track.state == "tracked":
                self.reacquired_total += 1
            if track.state == "tracked":
                target = {
                    key: value for key, value in detection.items()
                    if key not in ("_center", "_area")
                }
                target["track_id"] = track.track_id
                target["tracking_state"] = track.state
                target["association_distance_px"] = round(distance, 4)
                target["association_area_ratio"] = round(area_ratio, 4)
                visible.append(target)

        lost_ids = []
        retained = []
        for track_index, track in enumerate(self._tracks):
            if track_index in matched_tracks:
                retained.append(track)
                continue
            track.missed_frames += 1
            elapsed = stamp_sec - track.last_stamp_sec
            if (
                track.missed_frames > self.settings["max_missed_frames"]
                or elapsed > self.settings["track_timeout_sec"]
            ):
                lost_ids.append(track.track_id)
                self.lost_total += 1
            else:
                track.state = "occluded"
                retained.append(track)
        self._tracks = retained

        for detection_index, detection in enumerate(detections):
            if detection_index in matched_detections:
                continue
            track = self._new_track(detection, stamp_sec)
            if track.state == "tracked":
                target = {
                    key: value for key, value in detection.items()
                    if key not in ("_center", "_area")
                }
                target["track_id"] = track.track_id
                target["tracking_state"] = track.state
                target["association_distance_px"] = 0.0
                target["association_area_ratio"] = 1.0
                visible.append(target)

        visible.sort(key=lambda target: target["area_px"], reverse=True)
        if visible:
            overall_state = "tracked"
        elif any(track.state == "tentative" for track in self._tracks):
            overall_state = "tentative"
        elif any(track.state == "occluded" for track in self._tracks):
            overall_state = "occluded"
        elif lost_ids:
            overall_state = "lost"
        else:
            overall_state = "no_target"

        track_info = []
        for track in sorted(self._tracks, key=lambda item: item.track_id):
            predicted = track.predicted_center(stamp_sec)
            track_info.append({
                "track_id": track.track_id,
                "state": track.state,
                "hits": track.hits,
                "missed_frames": track.missed_frames,
                "center_px": [round(float(value), 3) for value in track.center_px],
                "predicted_center_px": [round(float(value), 3) for value in predicted],
                "last_stamp_sec": round(track.last_stamp_sec, 9),
            })

        self._last_stamp = stamp_sec
        return {
            "tracking_state": overall_state,
            "targets": visible,
            "selected_track_id": visible[0]["track_id"] if visible else None,
            "active_track_count": len(self._tracks),
            "visible_track_count": len(visible),
            "lost_track_ids": lost_ids,
            "created_tracks_total": self.created_total,
            "lost_tracks_total": self.lost_total,
            "reacquisitions_total": self.reacquired_total,
            "tracks": track_info,
        }
