from glob import glob
from setuptools import find_packages, setup

package_name = "openmv_camera"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml", "POSE_TF_ASSUMPTIONS.md"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
        ("share/" + package_name + "/rviz", glob("rviz/*.rviz")),
        ("share/" + package_name + "/openmv", glob("openmv/*.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Night2heartbreak",
    maintainer_email="noreply@example.com",
    description="OpenMV H7 Plus ROS 2 camera, tracking, PnP, filtering, replay and RViz",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "openmv_camera_node = openmv_camera.camera_node:main",
            "openmv_stream_check = openmv_camera.stream_check:main",
            "openmv_hsv_node = openmv_camera.hsv_node:main",
            "openmv_square_node = openmv_camera.square_node:main",
            "openmv_tracking_node = openmv_camera.tracking_node:main",
            "openmv_pose_node = openmv_camera.pose_node:main",
            "openmv_pose_filter_node = openmv_camera.pose_filter_node:main",
            "openmv_visualization_node = openmv_camera.visualization_node:main",
        ],
    },
)
