import unittest

from openmv_camera.tracking import TemporalTracker


DEFAULTS = {
    "max_association_distance_px": 50.0,
    "max_area_ratio": 2.0,
    "velocity_alpha": 0.5,
    "min_hits": 1,
    "max_missed_frames": 2,
    "track_timeout_sec": 0.5,
}


def target(x, y=100.0, area=1000.0):
    return {
        "center_px": [float(x), float(y)],
        "area_px": float(area),
        "vertices": [[x - 10, y - 10], [x + 10, y - 10],
                     [x + 10, y + 10], [x - 10, y + 10]],
    }


class TemporalTrackerTest(unittest.TestCase):
    def test_motion_preserves_track_id(self):
        tracker = TemporalTracker(DEFAULTS)
        first = tracker.update([target(20)], 0.0)
        second = tracker.update([target(35)], 0.05)
        self.assertEqual(first["selected_track_id"], second["selected_track_id"])
        self.assertEqual(second["tracking_state"], "tracked")

    def test_two_targets_are_associated_one_to_one(self):
        tracker = TemporalTracker(DEFAULTS)
        first = tracker.update([target(20, area=900), target(200, area=1100)], 0.0)
        ids_by_x = {item["center_px"][0]: item["track_id"] for item in first["targets"]}
        second = tracker.update([target(205, area=1100), target(25, area=900)], 0.05)
        self.assertEqual(len(second["targets"]), 2)
        for item in second["targets"]:
            expected_x = 25.0 if item["center_px"][0] < 100 else 205.0
            original_x = 20.0 if expected_x == 25.0 else 200.0
            self.assertEqual(item["track_id"], ids_by_x[original_x])

    def test_brief_occlusion_outputs_nothing_and_reuses_id(self):
        tracker = TemporalTracker(DEFAULTS)
        track_id = tracker.update([target(50)], 0.0)["selected_track_id"]
        occluded = tracker.update([], 0.05)
        self.assertEqual(occluded["tracking_state"], "occluded")
        self.assertEqual(occluded["targets"], [])
        recovered = tracker.update([target(55)], 0.10)
        self.assertEqual(recovered["selected_track_id"], track_id)
        self.assertEqual(recovered["reacquisitions_total"], 1)

    def test_long_occlusion_loses_track_and_assigns_new_id(self):
        tracker = TemporalTracker(DEFAULTS)
        first_id = tracker.update([target(50)], 0.0)["selected_track_id"]
        tracker.update([], 0.05)
        tracker.update([], 0.10)
        lost = tracker.update([], 0.15)
        self.assertEqual(lost["lost_track_ids"], [first_id])
        new = tracker.update([target(50)], 0.20)
        self.assertNotEqual(new["selected_track_id"], first_id)

    def test_prediction_bridges_short_gap_during_motion(self):
        settings = dict(DEFAULTS, max_association_distance_px=15.0, velocity_alpha=1.0)
        tracker = TemporalTracker(settings)
        track_id = tracker.update([target(0)], 0.0)["selected_track_id"]
        tracker.update([target(10)], 0.05)
        tracker.update([], 0.10)
        recovered = tracker.update([target(30)], 0.15)
        self.assertEqual(recovered["selected_track_id"], track_id)

    def test_tentative_track_is_not_sent_to_pnp(self):
        tracker = TemporalTracker(dict(DEFAULTS, min_hits=2))
        first = tracker.update([target(50)], 0.0)
        self.assertEqual(first["tracking_state"], "tentative")
        self.assertEqual(first["targets"], [])
        second = tracker.update([target(52)], 0.05)
        self.assertEqual(second["tracking_state"], "tracked")
        self.assertEqual(second["selected_track_id"], first["tracks"][0]["track_id"])

    def test_distant_detection_does_not_reuse_id(self):
        tracker = TemporalTracker(DEFAULTS)
        first_id = tracker.update([target(0)], 0.0)["selected_track_id"]
        second = tracker.update([target(200)], 0.05)
        self.assertNotEqual(second["selected_track_id"], first_id)

    def test_area_gate_rejects_implausible_match(self):
        tracker = TemporalTracker(DEFAULTS)
        first_id = tracker.update([target(50, area=1000)], 0.0)["selected_track_id"]
        second = tracker.update([target(50, area=5000)], 0.05)
        self.assertNotEqual(second["selected_track_id"], first_id)

    def test_non_monotonic_timestamp_is_rejected(self):
        tracker = TemporalTracker(DEFAULTS)
        tracker.update([target(50)], 1.0)
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            tracker.update([target(50)], 1.0)


if __name__ == "__main__":
    unittest.main()
