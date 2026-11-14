"""Simülasyonu açar ve LiDAR ile haritalamayı başlatır.

Kullanım:  ros2 launch forklift_sim harita.launch.py

Robotu ayrı bir terminalde klavyeyle gezdirin:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard
Harita bitince kaydedin:
    ros2 run nav2_map_server map_saver_cli -f ~/saha_haritasi
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    paket = get_package_share_directory("forklift_sim")

    simulasyon = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(paket, "launch", "sim.launch.py"))
    )

    # LiDAR'ın gövdeye göre yeri; models/forklift/model.sdf içindeki sensör pozu ile aynı olmalı.
    lidar_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=["--x", "0.25", "--y", "0", "--z", "0.27",
                   "--frame-id", "base_link", "--child-frame-id", "lidar_link"],
        parameters=[{"use_sim_time": True}],
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("slam_toolbox"),
                         "launch", "online_async_launch.py")
        ),
        launch_arguments={
            "use_sim_time": "true",
            "slam_params_file": os.path.join(paket, "config", "slam.yaml"),
        }.items(),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", os.path.join(paket, "rviz", "harita.rviz")],
        parameters=[{"use_sim_time": True}],
        # Sanal makinenin ekran kartı sürücüsüyle RViz haritayı ve LiDAR noktalarını
        # çizemiyor; RViz yazılımsal çizimle açılır (2B harita için yeterince hızlı).
        additional_env={"LIBGL_ALWAYS_SOFTWARE": "1"},
        output="log",
    )

    return LaunchDescription([simulasyon, lidar_tf, slam, rviz])
