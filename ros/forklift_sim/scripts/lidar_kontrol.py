#!/usr/bin/env python3
"""LiDAR verisini kontrol eder: /scan konusundan tek bir tarama alır ve özetler.

Kullanım (simülasyon açıkken, robot başlangıç yerinde dururken):
    python3 ~/ros2_ws/src/forklift-amr/ros/forklift_sim/scripts/lidar_kontrol.py

Çıktı:
  - taramanın açı ve mesafe ayarları,
  - robotun önü, solu, arkası ve sağındaki ölçümler (başlangıçta beklenen değerlerle),
  - LiDAR'ın gördüğü noktaların yukarıdan bakışla kaba bir çizimi.
"""

import math

BEKLENEN = {          # robot başlangıçta (1,9 ; 1,5), +y'ye bakarken; LiDAR tekerlek ekseninin 45 cm önünde
    "ön": 8.0,
    "sol": 1.85,
    "arka": 1.9,
    "sağ": 5.55,
}
YONLER = {"ön": 0.0, "sol": math.pi / 2, "arka": math.pi, "sağ": -math.pi / 2}


def olcum_al(ranges, aci_min, aci_artis, aci):
    """İstenen açıya en yakın ölçümü döndürür (arka için ±π uçlarını da dener)."""
    en_iyi, en_iyi_fark = None, None
    for i, r in enumerate(ranges):
        a = aci_min + i * aci_artis
        fark = abs(math.atan2(math.sin(a - aci), math.cos(a - aci)))
        if en_iyi_fark is None or fark < en_iyi_fark:
            en_iyi, en_iyi_fark = (r, a), fark
    return en_iyi


def ozet(ranges, aci_min, aci_max, aci_artis, mesafe_min, mesafe_max):
    satirlar = []
    gecerli = [r for r in ranges if mesafe_min <= r <= mesafe_max and math.isfinite(r)]
    satirlar.append(f"Ölçüm sayısı: {len(ranges)}   açı: {math.degrees(aci_min):.1f}° .. "
                    f"{math.degrees(aci_max):.1f}°   adım: {math.degrees(aci_artis):.2f}°")
    satirlar.append(f"Geçerli ölçüm: {len(gecerli)}   menzil dışı / sonsuz: {len(ranges) - len(gecerli)}")
    if gecerli:
        sirali = sorted(gecerli)
        satirlar.append(f"En yakın: {sirali[0]:.2f} m   ortanca: {sirali[len(sirali) // 2]:.2f} m   "
                        f"en uzak: {sirali[-1]:.2f} m")
    satirlar.append("")
    satirlar.append("Yön     ölçülen   beklenen")
    for ad, aci in YONLER.items():
        r, a = olcum_al(ranges, aci_min, aci_artis, aci)
        olculen = f"{r:.2f} m" if math.isfinite(r) else "sonsuz"
        satirlar.append(f"{ad:6s}  {olculen:>8s}   {BEKLENEN[ad]:.2f} m   (açı {math.degrees(a):+.0f}°)")
    satirlar.append("")
    satirlar.append(cizim(ranges, aci_min, aci_artis, mesafe_min, mesafe_max))
    return "\n".join(satirlar)


def cizim(ranges, aci_min, aci_artis, mesafe_min, mesafe_max, yaricap=9.0, gen=61, yuk=31):
    """Robot ortada (R), önü yukarı. Her karakter yaklaşık 0,3 m × 0,6 m."""
    izgara = [[" "] * gen for _ in range(yuk)]
    for i, r in enumerate(ranges):
        if not (mesafe_min <= r <= mesafe_max and math.isfinite(r)):
            continue
        a = aci_min + i * aci_artis
        ileri, sola = r * math.cos(a), r * math.sin(a)
        sutun = int(round((-sola / yaricap) * (gen // 2))) + gen // 2
        satir = int(round((-ileri / yaricap) * (yuk // 2))) + yuk // 2
        if 0 <= sutun < gen and 0 <= satir < yuk:
            izgara[satir][sutun] = "#"
    izgara[yuk // 2][gen // 2] = "R"
    cerceve = "+" + "-" * gen + "+"
    return "\n".join([f"Yukarıdan bakış (±{yaricap:.0f} m, robotun önü yukarı):", cerceve]
                     + ["|" + "".join(s) + "|" for s in izgara] + [cerceve])


def main():
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan

    rclpy.init()
    dugum = rclpy.create_node("lidar_kontrol")
    gelen = []
    dugum.create_subscription(LaserScan, "/scan", gelen.append, qos_profile_sensor_data)
    print("/scan bekleniyor (en çok 10 saniye)...")
    bitis = dugum.get_clock().now().nanoseconds + 10 * 10**9
    while not gelen and dugum.get_clock().now().nanoseconds < bitis:
        rclpy.spin_once(dugum, timeout_sec=0.2)
    if not gelen:
        print("HATA: /scan konusundan veri gelmedi. Simülasyon açık mı?")
    else:
        m = gelen[0]
        print(f"Çerçeve: {m.header.frame_id}")
        print(ozet(list(m.ranges), m.angle_min, m.angle_max, m.angle_increment,
                   m.range_min, m.range_max))
    dugum.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
