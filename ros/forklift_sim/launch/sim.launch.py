"""Yarışma sahasını Gazebo'da açar, robotu başlangıç alanına koyar, ROS köprüsünü kurar.

Kullanım:  ros2 launch forklift_sim sim.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

# Robotun doğduğu yer; scripts/saha_uret.py içindeki BASLANGIC ile aynı olmalı.
BASLANGIC_X, BASLANGIC_Y = "1.9", "1.5"
BASLANGIC_YON = "1.5708"   # +y yönüne (q1'e doğru) bakar


def generate_launch_description():
    paket = get_package_share_directory("forklift_sim")
    dunya = os.path.join(paket, "worlds", "saha.sdf")
    robot = os.path.join(paket, "models", "forklift", "model.sdf")
    kopru_ayari = os.path.join(paket, "config", "kopru.yaml")

    # Sanal makinede varsayılan çizim motoru (ogre2) çöküyor; ogre ile açılır.
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": f"-r {dunya} --render-engine ogre"}.items(),
    )

    robot_ekle = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-file", robot, "-name", "forklift",
                   "-x", BASLANGIC_X, "-y", BASLANGIC_Y, "-z", "0.02", "-Y", BASLANGIC_YON],
        output="screen",
    )

    kopru = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[{"config_file": kopru_ayari}],
        output="screen",
    )

    return LaunchDescription([gazebo, robot_ekle, kopru])
