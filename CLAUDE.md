# Proje bağlamı

TEKNOFEST Sanayide Robotik Uygulamalar yarışması için otonom forklift AMR. Hedef bir
sonraki yılın yarışması; elimizdeki şartname 2026 sürümü (V1.1) ve Ek Teknik Şartname.
Yeni şartname çıkınca protokol, saha ölçüleri ve QR metinleri değişebilir; bu yüzden
bu tür sabitler tek yerde tutulmalı.

Proje sahibi robotik ve Linux'ta yeni. Açıklamalar Türkçe, adım adım ve sade olmalı.
Kod içindeki adlar ve yorumlar Türkçe (mevcut üslup korunur).

## Şartnameden kesin bilgiler

**Görev akışı:** Bekleme (BASLA) → PLC'den görev al → alma noktası (ALIM1-3) → yükü al →
kapı (KAPI1'de dur, izin bekle) → bırakma noktası (BIRAK1-3) → yükü bırak → dönüşte
kapıda yine izin al → bekleme noktası. Süre hedefi 30 dk, üst limit 45 dk.

**PLC protokolü (Ek Teknik Şartname):** UDP, PLC 192.168.100.100:1515, robot
192.168.100.10, izleme bilgisayarı 192.168.100.20, ağ geçidi 192.168.100.1.
- PAKET_TX (robot → PLC, saniyede bir, 7 bayt): durum, alım (1-3), bırakma (1-3),
  X int16 LE, Y int16 LE. X = int(x_metre × 100).
- PAKET_RX (PLC → robot, 3 bayt): alım, bırakma, kontrol (1 bekle, 2 başla/devam et).
- 1 saniye paket gelmezse PLC bağlantıyı kopmuş sayar.
- Durum kodları: 1 hazır bekleme, 2 görev işleniyor, 3 yüksüz hareket, 4 yüklü hareket,
  5 PLC komutu bekleniyor, 6 başlangıca dönüş, 7 hata, 8 acil stop.

**QR kodlar:** 50 × 50 mm, yerde. Q1 BASLA, Q2-Q4 ALIM1-3, Q5 KAPI1, Q6 KAPI2,
Q7 BIRAK3, Q8 BIRAK2, Q9 BIRAK1. Alma/bırakma QR'ı noktadan yaklaşık 1,5 m önce.

**Saha:** 18 × 10 m, ortada kapılı duvar (kapı x ≈ 9 m). Sol yarıda başlangıç ve alma
noktaları, sağ yarıda bırakma noktaları. q5 kapının alma tarafında, q6 bırakma tarafında.
Deneme alanı 10 × 7 m.

**Şerit:** mavi-turuncu-mavi; turuncu ortada. **Palet:** 700 × 600 × 110 mm, çatal
boşlukları 300 mm arayla; yük 420 × 360 mm, en çok 5 kg.

**Toleranslar:** rotadan en çok 10 cm sapma; duruş noktalarında ±7,5 cm ve ±5°.
Yük, hareket yönünün tersinde taşınır. Engelde durulur, kaçınma manevrası yapılmaz.

**Puanlar:** haritalama 30, görevi tamamlama 30, rota hazırlama 20, PLC haberleşmesi 20,
kapıdan geçiş 20, arayüz 20, çizgi takibi 10, QR 10, çarpışma engelleme 10, sunum 10.
Arayüzde eksik her bilgi −4. Anahtar otomatikteyken uzaktan kontrol yapılamamalı.

## Alınan kararlar

- **ROS 2 Jazzy + Gazebo Harmonic**, Ubuntu 24.04 ARM64 üzerinde. LiDAR ile haritalama
  zorunlu olduğu için hazır araçlar (slam_toolbox, Nav2) kullanılacak.
- Geliştirme makinesi M4 Mac (16 GB). ROS ve Gazebo, UTM içindeki Ubuntu sanal
  makinesinde (`forklift-ros`, 8 GB bellek, 6 çekirdek, 64 GB disk) çalışır.
- Sanal makinede Gazebo'nun varsayılan çizim motoru (ogre2) çöküyor; her zaman
  ogre ile açılır. `sim.launch.py` Gazebo sunucusunu (`gz sim -s`, yazılımsal çizim)
  ve penceresini (`gz sim -g`, ekran kartı) ayrı süreçler olarak başlatır.
- ROS paketleri `ros/` altında durur. Repo, sanal makinede `~/ros2_ws/src/forklift-amr`
  olarak klonlanır ve `~/ros2_ws` içinde `colcon build` ile derlenir.
- Saha ölçüleri tek yerde: `ros/forklift_sim/scripts/saha_uret.py`. `worlds/saha.sdf`
  bu betikle üretilir, elle düzenlenmez. Koordinat orijini sahanın sol alt köşesi.
- Robot modelinde `base_link` iki tahrik tekerinin ortasında (robot bu noktanın
  etrafında döner); gövde 0,2 m arkaya, 0,6 m öne uzanır, LiDAR 0,45 m önde. Nav2'deki
  footprint ve `sim.launch.py`'deki LiDAR TF'i buna göre.
- Navigasyon haritası (`ros/forklift_sim/maps/saha.pgm/.yaml`) `saha_uret.py` ile duvar
  ölçülerinden üretilir; koordinatları saha koordinatlarıyla aynı. LiDAR'la çıkarılan
  harita yalnızca haritalamanın çalıştığını göstermek için; yarışmada gerçek harita
  LiDAR ile çıkarılıp başlangıç noktası tanıtılacak.
- Nav2 kendi başlatma dosyamızla (`nav.launch.py`) kuruluyor, `nav2_bringup` kullanılmıyor:
  map_server, amcl, planner (NavFn, A*), controller (Regulated Pure Pursuit; MPPI sanal
  makinede ağır), behavior_server, bt_navigator. Duruş toleransı ±7 cm / ±0,08 rad.
  Şartname engelde durmayı, kaçınmayı değil istiyor; Nav2'nin yeniden planlaması ileride
  bu kurala göre sınırlanmalı.
- Simülasyondaki LiDAR bilerek 355° tarar (±3,1 rad, 356 ölçüm): slam_toolbox tam tur
  taramalarda beklenen ölçüm sayısını yanlış hesaplayıp taramaları reddedebiliyor.
- Mevcut `mission/` kodu düz Python olarak kalır ve Mac'te doğrudan çalışır; ileride
  ROS 2 içinde bir düğüm olarak sarılacak, baştan yazılmayacak.
- Robot bilgisayarı olarak Raspberry Pi 5 düşünülüyor (aynı Ubuntu ve ROS sürümü).
- Sunum dosyası (38 slayt) Ek Teknik Şartname'den önce yazıldı; durum kodları, protokol
  ve QR içerikleri orada eski. Kod doğru olanı kullanıyor, sunum güncellenecek.

## Bilinen ortam sorunu

Proje sahibinin kullandığı ağlardan biri şifresiz (http) apt isteklerini 403 ile
reddediyor; https sorunsuz. Ubuntu'da paket kaynakları https olmalı:
`sudo sed -i 's|http://ports|https://ports|' /etc/apt/sources.list.d/ubuntu.sources`
ROS deposu da https olmalı, ama `packages.ros.org` https sertifikası geçersiz (ad
uyuşmuyor). Çalışan çözüm, aynı paketleri sunan OSUOSL adresi (doğrulandı, Nav2 kuruldu):
`/etc/apt/sources.list.d/ros2.sources` içinde
`URIs: https://ftp.osuosl.org/pub/ros/packages.ros.org/ros2/ubuntu`
(ros2-apt-source paketi güncellenirse dosya eski haline dönebilir; 403 ya da sertifika
hatası görülürse adresi tekrar değiştir.)
Bu ağ ping'i de engelliyor.
Ubuntu 24.04.3 ARM masaüstü ISO'su çekirdeği internetten indirir; internetsiz kurulmaz.

## Çözülen sorun: haritalamada bozuk LiDAR

`harita.launch.py` açıkken (slam + RViz) `gpu_lidar` bütün ölçümleri 0,15-1,0 m
veriyordu; harita robotun çevresinde 1 m'lik halka olarak çıkıyordu. Neden: LiDAR ve
RViz sanal ekran kartını paylaşınca sürücü bozuluyor. Çözüm: `sim.launch.py` Gazebo
sunucusunu `LIBGL_ALWAYS_SOFTWARE=1` ile, pencereyi ekran kartıyla ayrı süreçlerde
açıyor; RViz de yazılımsal çizimle açılıyor. Doğrulandı: ölçümler doğru, RViz harita ve
LiDAR noktalarını gösteriyor, kaydedilen harita (220 × 381 hücre, 5 cm) sahaya uyuyor.
Gazebo Harmonic'te CPU tabanlı LiDAR yok (gz-sim 10'la geliyor).
Teşhis aracı: `ros/forklift_sim/scripts/lidar_kontrol.py`.

## Kodun durumu

| Kalem | Durum |
|---|---|
| Durum makinesi (`gorev_yoneticisi.py`) | Hazır; hareketler zamanlayıcıyla taklit ediliyor |
| PLC haberleşmesi | Hazır, sahte PLC ile denendi |
| Kullanıcı arayüzü | Hazır; rota tanımlama ve harita ekranı yok |
| QR okuma | Metin okunuyor; kameraya göre konum hesabı yok |
| Çizgi takibi | Algılama hazır (sapma ve açı), sürüşe bağlı değil; piksel → mm kalibrasyonu yok |
| Simülasyon (`ros/forklift_sim`) | Saha, yer işaretleri, diferansiyel sürüşlü robot ve LiDAR sanal makinede çalışıyor; klavyeyle sürüş denendi. Kapı, şerit, QR görselleri, kamera, çatal yok |
| Sürüş, odometri, konum | Simülasyonda `/cmd_vel`, `/odom`, `/scan` var; PLC paketine bağlı değil (konum 0,00 gidiyor) |
| Haritalama | Simülasyonda çalışıyor: klavyeyle gezdirilerek iki oda ve geçit doğru haritalandı, `~/saha_haritasi.pgm/.yaml` olarak sanal makinede kayıtlı (repoda değil) |
| Otonom sürüş (Nav2) | `nav.launch.py` + `config/nav2.yaml` yazıldı. Nav2 kuruldu (OSUOSL adresiyle); RViz'den hedef verilerek denenecek |
| Rota planlama | `mission/rota_planlayici.py`: takım arkadaşı (Şevval) Dijkstra ile ekledi; nokta grafiği ve mesafeler örnek değerler, A3/B2/B3 henüz yok. Görev alınınca rota hesaplanıp arayüz durumuna (`aktif_rota`) yazılıyor, harekete bağlı değil |
| Engelde durma | Yok |
| Kaldırma, acil stop, mod anahtarı donanımı | Yok (mod yalnızca geliştirme panelinden değişiyor) |

## Yol haritası

1. ~~Ubuntu sanal makinesine ROS 2 Jazzy ve Gazebo kurulumu.~~ Tamamlandı.
2. Gazebo'da saha ve basit robot modeli: ilk sürüm çalışıyor. Kapı, şeritler,
   QR görselleri ve kamera daha sonra eklenecek.
3. Sürüş ve odometri; konumu PLC paketine bağlamak.
4. ~~Haritalama (slam_toolbox) ve haritayı kaydetme.~~ Simülasyonda tamamlandı.
5. Arayüzde rota tanımlama, en kısa yol hesabı, yol takibi. Sıra: (a) Nav2 ile RViz'den
   hedefe gitme, (b) durak koordinatlarını tek dosyada toplama, Şevval'in grafiğini
   tamamlama, (c) görev yöneticisini durakları Nav2'ye gönderecek şekilde bağlama ve
   gerçek konumu PLC paketine yazma.
6. Durum makinesindeki zamanlayıcıları gerçek olaylarla değiştirmek.
7. Çizgi takibini sürüşe bağlamak, QR konumu (solvePnP), yük alma yanaşması.
8. Engelde durma.
9. Gerçek donanıma taşıma.

## Çalıştırma ve test

```bash
python3 mission/plc_sim.py                                         # sahte PLC
PLC_IP=127.0.0.1 GELISTIRME=1 python3 mission/robot_ana.py         # robot + arayüz :8080
python3 vision/test_cizgi_takibi.py                                # çizgi takibi testi
```

Simülasyon (Ubuntu sanal makinesinde):

```bash
cd ~/ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch forklift_sim sim.launch.py                      # saha + robot
ros2 run teleop_twist_keyboard teleop_twist_keyboard        # ayrı terminalde klavyeyle sürüş
ros2 launch forklift_sim harita.launch.py                   # saha + robot + haritalama + RViz
ros2 run nav2_map_server map_saver_cli -f ~/saha_haritasi   # haritayı kaydet
ros2 launch forklift_sim nav.launch.py                      # saha + robot + Nav2 + RViz (2D Goal Pose ile hedef)
python3 ros/forklift_sim/scripts/saha_uret.py               # saha ölçüsü değişince dünya ve haritayı yeniden üret
```

Nav2 kurulumu: `sudo apt install -y ros-jazzy-navigation2`.

Klavyeyle sürüşte Türkçe Q klavyede ileri tuşu noktalı `i` (Ş'nin sağında); noktasız `ı`
robotu durdurur. Harita çerçevesinin orijini robotun başladığı yerdir ve robotun ilk
baktığı yön +x'tir; saha koordinatlarına (sol alt köşe orijin) çevirmek ayrı bir adım.

MQTT yalnızca robot içi girişler için kullanılıyor: `amr/qr` (okunan QR metni),
`amr/kill` (1 basılı, 0 bırakıldı), `amr/durum` (robot durumu). Broker yoksa program
yine çalışır; QR ve acil stop geliştirme panelinden girilir.
