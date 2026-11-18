"""Yarışma sahasını Gazebo'da açar, robotu başlangıç alanına koyar, ROS köprüsünü kurar.

Kullanım:  ros2 launch forklift_sim sim.launch.py

Gazebo iki ayrı süreç olarak açılır:
  - sunucu (fizik + sensörler): yazılımsal çizimle. Sanal makinede LiDAR ekran kartıyla
    çalışınca, özellikle RViz de açıkken, bozuk ölçüm (hep 0,15-1,0 m) üretiyordu.
  - pencere (GUI): ekran kartıyla, akıcı görüntü için.
Sorun çıkarsa sunucuyu da ekran kartıyla açmak için:
    ros2 launch forklift_sim sim.launch.py lidar_yazilimsal:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Robotun doğduğu yer; scripts/saha_uret.py içindeki BASLANGIC ile aynı olmalı.
BASLANGIC_X, BASLANGIC_Y = "1.9", "1.5"
BASLANGIC_YON = "1.5708"   # +y yönüne (q1'e doğru) bakar


def _gazebo(context):
    paket = get_package_share_directory("forklift_sim")
    dunya = os.path.join(paket, "worlds", "saha.sdf")
    yazilimsal = LaunchConfiguration("lidar_yazilimsal").perform(context).lower() in ("1", "true", "evet")

    # Varsayılan çizim motoru (ogre2) sanal makinede çöküyor; her ikisi de ogre ile açılır.
    sunucu = ExecuteProcess(
        cmd=["gz", "sim", "-s", "-r", "--render-engine-server", "ogre", dunya],
        additional_env={"LIBGL_ALWAYS_SOFTWARE": "1"} if yazilimsal else {},
        output="screen",
    )
    pencere = ExecuteProcess(
        cmd=["gz", "sim", "-g", "--render-engine-gui", "ogre"],
        output="screen",
    )
    return [sunucu, pencere]


def generate_launch_description():
    paket = get_package_share_directory("forklift_sim")
    robot = os.path.join(paket, "models", "forklift", "model.sdf")
    kopru_ayari = os.path.join(paket, "config", "kopru.yaml")

    robot_ekle = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-world", "saha", "-file", robot, "-name", "forklift",
                   "-x", BASLANGIC_X, "-y", BASLANGIC_Y, "-z", "0.02", "-Y", BASLANGIC_YON],
        output="screen",
    )

    # LiDAR'ın gövdeye göre yeri; models/forklift/model.sdf içindeki sensör pozu ile aynı olmalı.
    lidar_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=["--x", "0.45", "--y", "0", "--z", "0.27",
                   "--frame-id", "base_link", "--child-frame-id", "lidar_link"],
        parameters=[{"use_sim_time": True}],
    )

    kopru = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[{"config_file": kopru_ayari}],
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument("lidar_yazilimsal", default_value="true",
                              description="Gazebo sunucusunu (LiDAR) yazılımsal çizimle çalıştır"),
        OpaqueFunction(function=_gazebo),
        robot_ekle,
        lidar_tf,
        kopru,
    ])
