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
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Nav2 düğümleri iki grupta başlatılır (nav2_bringup da böyle yapar):
# önce harita + konum bulma, birkaç saniye sonra yol planlama ve izleme.
# Planlayıcının maliyet haritası açılırken "map -> base_link" dönüşümünü bekliyor;
# amcl'den hemen sonra açılınca bu dönüşüm henüz yoktu ve açılış başarısız oluyordu.
KONUM_DUGUMLERI = [
    ("nav2_map_server", "map_server"),
    ("nav2_amcl", "amcl"),
]
NAVIGASYON_DUGUMLERI = [
    ("nav2_planner", "planner_server"),
    ("nav2_controller", "controller_server"),
    ("nav2_behaviors", "behavior_server"),
    ("nav2_bt_navigator", "bt_navigator"),
]
NAVIGASYON_GECIKMESI = 8.0   # saniye; konum bulma hazır olsun diye


def generate_launch_description():
    paket = get_package_share_directory("forklift_sim")
    ayarlar = os.path.join(paket, "config", "nav2.yaml")
    harita = LaunchConfiguration("harita")

    simulasyon = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(paket, "launch", "sim.launch.py"))
    )

    dugumler = []
    for paket_adi, ad in KONUM_DUGUMLERI + NAVIGASYON_DUGUMLERI:
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

    def yonetici(ad, dugum_listesi):
        # bond_timeout: yönetici her düğümü başlattıktan sonra onunla bağ kurmayı bekler;
        # sanal makine yavaş olduğu için varsayılan 4 sn yerine 20 sn.
        return Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name=ad,
            parameters=[{"use_sim_time": True, "autostart": True, "bond_timeout": 20.0,
                         "node_names": [d for _, d in dugum_listesi]}],
            output="screen",
        )

    konum_yoneticisi = yonetici("lifecycle_manager_localization", KONUM_DUGUMLERI)
    navigasyon_yoneticisi = TimerAction(
        period=NAVIGASYON_GECIKMESI,
        actions=[yonetici("lifecycle_manager_navigation", NAVIGASYON_DUGUMLERI)],
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
        konum_yoneticisi,
        navigasyon_yoneticisi,
        rviz,
    ])
