"""Görüntü işleme ile çizgi takibi (şartname görev 4).

Ek Teknik Şartname Şekil 5 ve 6'ya göre yerdeki şerit mavi-turuncu-mavi renklidir.
Bu modül ortadaki turuncu bandı renk (HSV) ile ayırır ve robotun çizgiye göre
yanal sapmasını ve açı hatasını hesaplar.

Kullanım:
    python3 vision/cizgi_takibi.py                  # kamera ile canlı izleme
    python3 vision/cizgi_takibi.py --ayarla         # renk aralığını kaydırıcılarla ayarla
    python3 vision/cizgi_takibi.py --goruntu a.png  # tek bir fotoğraf üzerinde dene

Tuşlar: q = çık, s = renk ayarını kaydet (--ayarla modunda).

cizgi_bul() fonksiyonu kameradan ve ekrandan bağımsızdır; ileride sürüş
kontrolüne (ROS 2 düğümü) aynen bağlanabilir.
"""

import argparse
import json
import math
import os

import cv2
import numpy as np

AYAR_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cizgi_ayar.json")

# Turuncu bant için başlangıç değerleri (OpenCV: H 0-179, S ve V 0-255).
# Işık koşullarına göre sahada --ayarla ile güncellenir.
VARSAYILAN_AYAR = {
    "h_min": 5, "h_max": 25,
    "s_min": 100, "s_max": 255,
    "v_min": 80, "v_max": 255,
    "min_alan": 800,   # bundan küçük turuncu lekeler çizgi sayılmaz (piksel²)
}


def ayar_yukle(dosya=AYAR_DOSYASI):
    ayar = dict(VARSAYILAN_AYAR)
    try:
        with open(dosya, encoding="utf-8") as f:
            ayar.update(json.load(f))
    except (OSError, ValueError):
        pass
    return ayar


def ayar_kaydet(ayar, dosya=AYAR_DOSYASI):
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(ayar, f, indent=2)


def cizgi_bul(goruntu, ayar=None):
    """Görüntünün alt yarısında turuncu çizgiyi arar.

    Dönen sözlük:
        bulundu   : çizgi görüldü mü
        sapma_px  : çizginin robota en yakın noktasının görüntü ortasından uzaklığı
                    (piksel; + ise çizgi sağda, robot sağa dönmeli)
        sapma     : aynı değer -1..+1 aralığına ölçeklenmiş
        aci       : çizginin ileri yöne göre açısı (derece; + ise çizgi sağa yatık)
        maske     : turuncu bölgelerin siyah-beyaz görüntüsü (hata ayıklama için)
        nokta, yon: çizim için çizgi üzerindeki nokta ve birim yön (ROI koordinatı)
    """
    ayar = ayar or VARSAYILAN_AYAR
    h, w = goruntu.shape[:2]
    roi = goruntu[h // 2:, :]          # robotun önündeki zemin
    roi_h = roi.shape[0]

    hsv = cv2.cvtColor(cv2.GaussianBlur(roi, (5, 5), 0), cv2.COLOR_BGR2HSV)
    alt = np.array([ayar["h_min"], ayar["s_min"], ayar["v_min"]], dtype=np.uint8)
    ust = np.array([ayar["h_max"], ayar["s_max"], ayar["v_max"]], dtype=np.uint8)
    maske = cv2.inRange(hsv, alt, ust)

    # Küçük lekeleri sil, çizgideki boşlukları (yansıma, QR etiketi) kapat
    maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    maske = cv2.morphologyEx(maske, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

    sonuc = {"bulundu": False, "sapma_px": 0.0, "sapma": 0.0, "aci": 0.0,
             "maske": maske, "nokta": None, "yon": None}

    konturlar, _ = cv2.findContours(maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not konturlar:
        return sonuc
    en_buyuk = max(konturlar, key=cv2.contourArea)
    if cv2.contourArea(en_buyuk) < ayar["min_alan"]:
        return sonuc

    vx, vy, x0, y0 = (float(v) for v in cv2.fitLine(en_buyuk, cv2.DIST_L2, 0, 0.01, 0.01).ravel())
    if vy > 0:                         # yön hep ileriyi (görüntüde yukarıyı) göstersin
        vx, vy = -vx, -vy

    # Açı: 0 = çizgi dümdüz ileri gidiyor
    aci = math.degrees(math.atan2(vx, -vy))

    # Yanal sapma: çizginin görüntünün en alt satırını (robota en yakın yer) kestiği nokta
    if abs(vy) > 0.2:
        x_alt = x0 + (roi_h - 1 - y0) * vx / vy
        x_alt = max(0.0, min(w - 1.0, x_alt))
    else:                              # çizgi neredeyse yatay: ağırlık merkezini kullan
        x_alt = x0
    sapma_px = x_alt - w / 2.0

    sonuc.update(bulundu=True, sapma_px=sapma_px, sapma=sapma_px / (w / 2.0), aci=aci,
                 nokta=(x0, y0), yon=(vx, vy))
    return sonuc


def ciz(goruntu, sonuc):
    """Sonucu görüntünün üzerine çizer (yalnızca izleme için)."""
    h, w = goruntu.shape[:2]
    ust = h // 2
    cv2.line(goruntu, (w // 2, ust), (w // 2, h - 1), (0, 255, 0), 1)   # görüntü ortası
    cv2.line(goruntu, (0, ust), (w - 1, ust), (120, 120, 120), 1)       # ROI sınırı
    if sonuc["bulundu"]:
        (x0, y0), (vx, vy) = sonuc["nokta"], sonuc["yon"]
        p1 = (int(x0 - vx * 1000), int(y0 - vy * 1000) + ust)
        p2 = (int(x0 + vx * 1000), int(y0 + vy * 1000) + ust)
        cv2.line(goruntu, p1, p2, (0, 0, 255), 2)
        yazi = f"sapma {sonuc['sapma_px']:+.0f} px   aci {sonuc['aci']:+.1f} derece"
        renk = (0, 255, 0)
    else:
        yazi, renk = "CIZGI YOK", (0, 0, 255)
    cv2.putText(goruntu, yazi, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, renk, 2)
    return goruntu


def _kaydiricilari_ac(ayar):
    cv2.namedWindow("Ayar")
    for ad, ust in (("h_min", 179), ("h_max", 179), ("s_min", 255),
                    ("s_max", 255), ("v_min", 255), ("v_max", 255)):
        cv2.createTrackbar(ad, "Ayar", ayar[ad], ust, lambda _deger: None)


def _kaydiricilari_oku(ayar):
    for ad in ("h_min", "h_max", "s_min", "s_max", "v_min", "v_max"):
        ayar[ad] = cv2.getTrackbarPos(ad, "Ayar")


def main():
    p = argparse.ArgumentParser(description="Mavi-turuncu-mavi şeritte çizgi takibi")
    p.add_argument("--kamera", type=int, default=0, help="kamera numarası (varsayılan 0)")
    p.add_argument("--goruntu", help="kamera yerine tek bir görüntü dosyası kullan")
    p.add_argument("--ayarla", action="store_true", help="renk aralığını kaydırıcılarla ayarla")
    args = p.parse_args()

    ayar = ayar_yukle()
    if args.ayarla:
        _kaydiricilari_ac(ayar)

    sabit = None
    cap = None
    if args.goruntu:
        sabit = cv2.imread(args.goruntu)
        if sabit is None:
            raise SystemExit(f"Görüntü okunamadı: {args.goruntu}")
    else:
        cap = cv2.VideoCapture(args.kamera)

    son_yazi = None
    while True:
        if sabit is not None:
            kare = sabit.copy()
        else:
            ok, kare = cap.read()
            if not ok:
                print("Kamera okunamadı")
                break

        if args.ayarla:
            _kaydiricilari_oku(ayar)
        sonuc = cizgi_bul(kare, ayar)

        if sonuc["bulundu"]:
            yazi = f"sapma {sonuc['sapma_px']:+.0f} px ({sonuc['sapma']:+.2f})  açı {sonuc['aci']:+.1f}°"
        else:
            yazi = "çizgi yok"
        if yazi != son_yazi:
            print(yazi)
            son_yazi = yazi

        cv2.imshow("Cizgi takibi", ciz(kare, sonuc))
        cv2.imshow("Maske", sonuc["maske"])
        tus = cv2.waitKey(30 if sabit is not None else 1) & 0xFF
        if tus == ord("q"):
            break
        if tus == ord("s") and args.ayarla:
            ayar_kaydet(ayar)
            print("Renk ayarı kaydedildi:", AYAR_DOSYASI)

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
