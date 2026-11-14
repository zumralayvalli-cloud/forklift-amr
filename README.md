# Otonom Forklift AMR

TEKNOFEST Sanayide Robotik Uygulamalar yarışması için otonom forklift mobil robot yazılımı.
Robot, fabrika otomasyon sisteminden (PLC) aldığı görevle bir paleti alma noktasından
bırakma noktasına taşır; yol üzerindeki kontrollü kapıdan izin alarak geçer.

## Klasörler

| Klasör | İçerik |
|---|---|
| `mission/` | Görev mantığı: durum makinesi, PLC haberleşmesi, kullanıcı arayüzü |
| `vision/` | Görüntü işleme: QR okuma, çizgi takibi |
| `ros/forklift_sim/` | ROS 2 paketi: Gazebo'da yarışma sahası ve robot modeli |

### mission/

| Dosya | Görevi |
|---|---|
| `robot_ana.py` | Ana program. Durum makinesini, PLC istemcisini ve arayüzü birlikte çalıştırır |
| `gorev_yoneticisi.py` | Şartnamedeki 8 durumlu durum makinesi ve görev akışı |
| `plc_istemci.py` | PLC ile UDP haberleşmesi (PAKET_TX 7 bayt, PAKET_RX 3 bayt) |
| `plc_sim.py` | Yarışmadaki PLC simülatörünün taklidi (test için) |
| `arayuz.py` | Web arayüzü: durum, görev, QR, PLC mesajları, uzaktan manuel kontrol |

### vision/

| Dosya | Görevi |
|---|---|
| `cizgi_takibi.py` | Mavi-turuncu-mavi şeritte çizgi takibi (sapma ve açı hesabı) |
| `test_cizgi_takibi.py` | Çizgi takibinin kamerasız testi |
| `qr_yayinci.py` | Kameradan QR okuyup MQTT'ye (`amr/qr`) yayınlar |
| `kamera_test.py` | Kamera ve QR okuma denemesi |

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Çalıştırma

Görev yazılımını sahte PLC ile denemek için iki terminal açın.

Terminal 1 (sahte PLC):

```bash
source .venv/bin/activate
python3 mission/plc_sim.py
```

Terminal 2 (robot):

```bash
source .venv/bin/activate
PLC_IP=127.0.0.1 GELISTIRME=1 python3 mission/robot_ana.py
```

Arayüz: <http://localhost:8080>

`GELISTIRME=1` arayüzde bir test paneli açar; QR okumayı, acil stopu ve mod anahtarını
buradan taklit edebilirsiniz. Yarışmada bu değişken verilmez.

Çizgi takibi:

```bash
python3 vision/test_cizgi_takibi.py        # kamerasız test
python3 vision/cizgi_takibi.py             # kamera ile canlı
python3 vision/cizgi_takibi.py --ayarla    # renk aralığını ayarla (s = kaydet, q = çık)
```

## Simülasyon

ROS 2 Jazzy ve Gazebo Harmonic kurulu bir Ubuntu 24.04 üzerinde:

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/zumralayvalli-cloud/forklift-amr.git
cd ~/ros2_ws && colcon build --symlink-install
source install/setup.bash
ros2 launch forklift_sim sim.launch.py
```

Robotu klavyeyle sürmek için ikinci bir terminalde:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Haritalama (simülasyon yerine bunu başlatın; sahayı, robotu, haritalamayı ve RViz'i birlikte açar):

```bash
sudo apt install -y ros-jazzy-slam-toolbox ros-jazzy-nav2-map-server
ros2 launch forklift_sim harita.launch.py
```

Robotu klavyeyle sahada gezdirin; RViz penceresinde harita oluşur. Bitince kaydedin:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/saha_haritasi
```

Saha ölçülerini değiştirmek için `ros/forklift_sim/scripts/saha_uret.py` dosyasının
başındaki sayıları düzenleyip betiği yeniden çalıştırın.

## Durum

Hazır olanlar: görev durum makinesi, PLC haberleşmesi, kullanıcı arayüzü, QR metni okuma,
çizgi algılama.

Eksik olanlar: sürüş ve konum, haritalama, rota tanımlama ve planlama, QR konum hesabı,
engelde durma, kaldırma mekanizması, gerçek donanım bağlantıları. Ayrıntılı yol haritası
`CLAUDE.md` dosyasında.
