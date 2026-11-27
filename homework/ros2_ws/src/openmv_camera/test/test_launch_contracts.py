from pathlib import Path
import unittest


PACKAGE = Path(__file__).resolve().parents[1]


class LaunchContractTest(unittest.TestCase):
    def test_live_pipeline_starts_all_nodes_and_optional_rviz(self):
        source = (PACKAGE / "launch" / "pipeline.launch.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("Node("), 8)
        self.assertEqual(source.count('executable="openmv_'), 7)
        self.assertIn('executable="openmv_camera_node"', source)
        self.assertIn('executable="openmv_visualization_node"', source)
        self.assertIn('IfCondition(LaunchConfiguration("rviz"))', source)

    def test_replay_excludes_camera_and_enables_simulated_time(self):
        source = (PACKAGE / "launch" / "replay.launch.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("processing_node(\""), 6)
        self.assertNotIn('processing_node("openmv_camera_node"', source)
        self.assertIn('{"use_sim_time": True}', source)

    def test_replay_reuses_all_algorithm_configs(self):
        source = (PACKAGE / "launch" / "replay.launch.py").read_text(encoding="utf-8")
        for name in (
            "hsv.yaml", "square.yaml", "tracking.yaml", "pose.yaml", "filter.yaml",
            "visualization.yaml",
        ):
            self.assertIn(f'"{name}"', source)
        setup = (PACKAGE / "setup.py").read_text(encoding="utf-8")
        self.assertIn('glob("launch/*.launch.py")', setup)

    def test_rviz_config_is_shipped_and_used_by_both_launches(self):
        setup = (PACKAGE / "setup.py").read_text(encoding="utf-8")
        self.assertIn('glob("rviz/*.rviz")', setup)
        self.assertTrue((PACKAGE / "rviz" / "target.rviz").is_file())
        for name in ("pipeline.launch.py", "replay.launch.py"):
            source = (PACKAGE / "launch" / name).read_text(encoding="utf-8")
            self.assertIn('PathJoinSubstitution([package_share, "rviz", "target.rviz"])', source)

    def test_external_mount_never_publishes_assumed_static_tf(self):
        source = (PACKAGE / "openmv_camera" / "pose_node.py").read_text(encoding="utf-8")
        self.assertIn('if self._settings["mount_tf_mode"] == "assumed_static":', source)
        self.assertIn('mount_tf_mode changes require editing YAML and restarting', source)
        config = (PACKAGE / "config" / "pose.yaml").read_text(encoding="utf-8")
        self.assertIn('mount_tf_mode: "assumed_static"', config)


if __name__ == "__main__":
    unittest.main()
