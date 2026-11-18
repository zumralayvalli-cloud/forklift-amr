"""Simülasyonu açar ve Nav2 ile otonom sürüşü başlatır.

Kullanım:  ros2 launch forklift_sim nav.launch.py

RViz'de üstteki "2D Goal Pose" düğmesine basıp haritada bir yere tıklayın ve
fareyi bırakmadan robotun bakacağı yöne sürükleyin; robot oraya kendi gider.

Harita: maps/saha.yaml (saha ölçülerinden üretilir, bkz. scripts/saha_uret.py).
Başka bir harita için:  ros2 launch forklift_sim nav.launch.py harita:=/tam/yol/harita.yaml
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Sırayla başlatılıp yönetilecek Nav2 düğümleri
DUGUMLER = [
    ("nav2_map_server", "map_server"),
    ("nav2_amcl", "amcl"),
    ("nav2_planner", "planner_server"),
    ("nav2_controller", "controller_server"),
    ("nav2_behaviors", "behavior_server"),
    ("nav2_bt_navigator", "bt_navigator"),
]


def generate_launch_description():
    paket = get_package_share_directory("forklift_sim")
    ayarlar = os.path.join(paket, "config", "nav2.yaml")
    harita = LaunchConfiguration("harita")

    simulasyon = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(paket, "launch", "sim.launch.py"))
    )

    dugumler = []
    for paket_adi, ad in DUGUMLER:
        parametreler = [ayarlar, {"use_sim_time": True}]
        if ad == "map_server":
            parametreler.append({"yaml_filename": harita})
        dugumler.append(Node(
            package=paket_adi,
            executable=ad,
            name=ad,
            parameters=parametreler,
            output="screen",
        ))

    yonetici = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        parameters=[{"use_sim_time": True, "autostart": True,
                     "node_names": [ad for _, ad in DUGUMLER]}],
        output="screen",
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", os.path.join(paket, "rviz", "nav.rviz")],
        parameters=[{"use_sim_time": True}],
        # Sanal makinede RViz ekran kartıyla çizim yapamıyor (bkz. harita.launch.py)
        additional_env={"LIBGL_ALWAYS_SOFTWARE": "1"},
        output="log",
    )

    return LaunchDescription([
        DeclareLaunchArgument("harita", default_value=os.path.join(paket, "maps", "saha.yaml"),
                              description="Kullanılacak harita (.yaml)"),
        simulasyon,
        *dugumler,
        yonetici,
        rviz,
    ])
