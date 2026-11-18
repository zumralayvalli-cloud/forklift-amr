#!/usr/bin/env python3
"""Yarışma sahasının Gazebo dünyasını (worlds/saha.sdf) ve navigasyon haritasını
(maps/saha.pgm + maps/saha.yaml) üretir.

Çalıştırma:  python3 ros/forklift_sim/scripts/saha_uret.py

Navigasyon haritası duvar ölçülerinden doğrudan çizilir; koordinatları saha
koordinatlarıyla aynıdır (orijin sol alt köşe). Yarışmada harita LiDAR ile çıkarılacak.

Ölçüler Ek Teknik Şartname Şekil 1'den alınmıştır. Şekilde açıkça yazan ölçüler
(18 m, 10 m, 9 m, 7,5 m, 4,5 m, 2,5 m, 5,5 m) kesindir; istasyon ve QR konumları
şekilden cetvelle okunmuş yaklaşık değerlerdir. Yeni şartname çıkınca yalnızca
bu dosyanın başındaki sayılar değiştirilip betik yeniden çalıştırılır.

Koordinat sistemi: orijin sahanın sol alt köşesi, x sağa, y yukarı (metre).
"""

import os

# ---------------- saha ölçüleri ----------------
SAHA_X, SAHA_Y = 18.0, 10.0
SOL_ODA_X = 7.5            # sol odanın sağ duvarı
SAG_ODA_X = 9.0            # sağ odanın sol duvarı
GECIT_ALT, GECIT_UST = 2.5, 5.5   # iki oda arasındaki geçidin y aralığı
ANA_HAT_Y = 4.5            # q1-q5-q6-q8 hattı (üstten 5,5 m)
KAPI_X = 8.25              # kontrollü kapının yeri (geçidin ortası)

DUVAR_KALINLIK = 0.10
DUVAR_YUKSEKLIK = 0.50

# Duvarlar: (x1, y1, x2, y2), eksenlere paralel
DUVARLAR = [
    # sol oda
    (0, 0, SOL_ODA_X, 0), (0, SAHA_Y, SOL_ODA_X, SAHA_Y), (0, 0, 0, SAHA_Y),
    (SOL_ODA_X, GECIT_UST, SOL_ODA_X, SAHA_Y), (SOL_ODA_X, 0, SOL_ODA_X, GECIT_ALT),
    # sağ oda
    (SAG_ODA_X, 0, SAHA_X, 0), (SAG_ODA_X, SAHA_Y, SAHA_X, SAHA_Y), (SAHA_X, 0, SAHA_X, SAHA_Y),
    (SAG_ODA_X, GECIT_UST, SAG_ODA_X, SAHA_Y), (SAG_ODA_X, 0, SAG_ODA_X, GECIT_ALT),
    # iki oda arasındaki geçidin yan duvarları
    (SOL_ODA_X, GECIT_ALT, SAG_ODA_X, GECIT_ALT), (SOL_ODA_X, GECIT_UST, SAG_ODA_X, GECIT_UST),
]

# Yerdeki işaretler: ad -> (x, y, renk). Yalnızca görseldir, robot üzerinden geçer.
QR_RENK = "1 1 1 1"
ALMA_RENK = "0.1 0.6 0.1 1"
BIRAKMA_RENK = "0.7 0.1 0.1 1"
ISARETLER = {
    # QR noktaları (beyaz kare)
    "q1_BASLA": (1.9, ANA_HAT_Y, QR_RENK),
    "q2_ALIM1": (1.9, 6.5, QR_RENK),
    "q3_ALIM2": (3.7, 6.5, QR_RENK),
    "q4_ALIM3": (5.5, 6.5, QR_RENK),
    "q5_KAPI1": (6.6, ANA_HAT_Y, QR_RENK),
    "q6_KAPI2": (10.0, ANA_HAT_Y, QR_RENK),
    "q7_BIRAK3": (11.5, 6.5, QR_RENK),
    "q8_BIRAK2": (14.9, ANA_HAT_Y, QR_RENK),
    "q9_BIRAK1": (11.5, 2.9, QR_RENK),
    # alma bölgeleri (yeşil)
    "alma1": (1.9, 8.6, ALMA_RENK),
    "alma2": (3.7, 8.6, ALMA_RENK),
    "alma3": (5.5, 8.6, ALMA_RENK),
    # bırakma bölgeleri (kırmızı)
    "birakma3": (11.5, 8.6, BIRAKMA_RENK),
    "birakma2": (16.9, ANA_HAT_Y, BIRAKMA_RENK),
    "birakma1": (11.5, 0.9, BIRAKMA_RENK),
    # başlangıç / bekleme alanı (mavi)
    "baslangic": (1.9, 1.5, "0.1 0.3 0.8 1"),
}
BASLANGIC = (1.9, 1.5)     # robotun doğduğu yer (launch dosyasıyla aynı olmalı)


def duvar(i, x1, y1, x2, y2):
    uzunluk = abs(x2 - x1) + abs(y2 - y1) + DUVAR_KALINLIK
    yatay = abs(x2 - x1) > abs(y2 - y1)
    boyut = (f"{uzunluk:.3f} {DUVAR_KALINLIK} {DUVAR_YUKSEKLIK}" if yatay
             else f"{DUVAR_KALINLIK} {uzunluk:.3f} {DUVAR_YUKSEKLIK}")
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return f"""
    <model name="duvar_{i}">
      <static>true</static>
      <pose>{cx:.3f} {cy:.3f} {DUVAR_YUKSEKLIK / 2} 0 0 0</pose>
      <link name="link">
        <collision name="collision"><geometry><box><size>{boyut}</size></box></geometry></collision>
        <visual name="visual">
          <geometry><box><size>{boyut}</size></box></geometry>
          <material><ambient>0.75 0.75 0.7 1</ambient><diffuse>0.75 0.75 0.7 1</diffuse></material>
        </visual>
      </link>
    </model>"""


def isaret(ad, x, y, renk):
    boyut = "0.25 0.25 0.002" if ad.startswith("q") else "0.7 0.6 0.002"
    return f"""
    <model name="{ad}">
      <static>true</static>
      <pose>{x} {y} 0.001 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>{boyut}</size></box></geometry>
          <material><ambient>{renk}</ambient><diffuse>{renk}</diffuse></material>
        </visual>
      </link>
    </model>"""


def dunya():
    govde = "".join(duvar(i, *d) for i, d in enumerate(DUVARLAR))
    govde += "".join(isaret(ad, *deger) for ad, deger in ISARETLER.items())
    return f"""<?xml version="1.0"?>
<!-- Bu dosya scripts/saha_uret.py tarafından üretilir; elle düzenlemeyin. -->
<sdf version="1.9">
  <world name="saha">
    <physics name="2ms" type="ignored">
      <max_step_size>0.002</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre</render_engine>
    </plugin>

    <light type="directional" name="gunes">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.3 0.2 -0.9</direction>
    </light>

    <model name="zemin">
      <static>true</static>
      <pose>{SAHA_X / 2} {SAHA_Y / 2} 0 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><plane><normal>0 0 1</normal><size>40 30</size></plane></geometry>
        </collision>
        <visual name="visual">
          <geometry><plane><normal>0 0 1</normal><size>40 30</size></plane></geometry>
          <material><ambient>0.45 0.45 0.45 1</ambient><diffuse>0.45 0.45 0.45 1</diffuse></material>
        </visual>
      </link>
    </model>
{govde}
  </world>
</sdf>
"""


# ---------------- navigasyon haritası ----------------
HARITA_COZUNURLUK = 0.05   # m / hücre
HARITA_PAY = 0.5           # sahanın çevresine bırakılan boşluk (m)


def harita():
    """Duvarları dolu (siyah), geri kalanı boş (beyaz) olan PGM resmi ve YAML üretir."""
    cozunurluk = HARITA_COZUNURLUK
    ox, oy = -HARITA_PAY, -HARITA_PAY
    gen = int(round((SAHA_X + 2 * HARITA_PAY) / cozunurluk))
    yuk = int(round((SAHA_Y + 2 * HARITA_PAY) / cozunurluk))
    yari = DUVAR_KALINLIK / 2
    kutular = [(min(x1, x2) - yari, min(y1, y2) - yari, max(x1, x2) + yari, max(y1, y2) + yari)
               for x1, y1, x2, y2 in DUVARLAR]
    pikseller = bytearray()
    for satir in range(yuk):                       # resmin ilk satırı haritanın en üstü
        y = oy + (yuk - 1 - satir + 0.5) * cozunurluk
        for sutun in range(gen):
            x = ox + (sutun + 0.5) * cozunurluk
            dolu = any(a <= x <= c and b <= y <= d for a, b, c, d in kutular)
            pikseller.append(0 if dolu else 254)
    pgm = f"P5\n{gen} {yuk}\n255\n".encode() + bytes(pikseller)
    yaml = (
        "# Bu dosya scripts/saha_uret.py tarafından üretilir; elle düzenlemeyin.\n"
        "image: saha.pgm\n"
        "mode: trinary\n"
        f"resolution: {cozunurluk}\n"
        f"origin: [{ox}, {oy}, 0.0]\n"
        "negate: 0\n"
        "occupied_thresh: 0.65\n"
        "free_thresh: 0.25\n"
    )
    return pgm, yaml


if __name__ == "__main__":
    kok = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    hedef = os.path.join(kok, "worlds", "saha.sdf")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(dunya())
    print("Yazıldı:", os.path.normpath(hedef))

    os.makedirs(os.path.join(kok, "maps"), exist_ok=True)
    pgm, yaml = harita()
    with open(os.path.join(kok, "maps", "saha.pgm"), "wb") as f:
        f.write(pgm)
    with open(os.path.join(kok, "maps", "saha.yaml"), "w", encoding="utf-8") as f:
        f.write(yaml)
    print("Yazıldı:", os.path.normpath(os.path.join(kok, "maps", "saha.pgm/.yaml")))
