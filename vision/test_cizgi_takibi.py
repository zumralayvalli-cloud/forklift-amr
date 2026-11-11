"""cizgi_takibi.cizgi_bul için kamerasız test.

Çalıştırma:  python3 vision/test_cizgi_takibi.py
Yapay bir zemin görüntüsü üretir (gri zemin, mavi-turuncu-mavi şerit) ve
hesaplanan sapma ile açının beklenen değerlere yakın olduğunu kontrol eder.
"""

import math

import cv2
import numpy as np

from cizgi_takibi import cizgi_bul

G, Y = 640, 480                 # görüntü boyutu
MAVI = (180, 110, 60)           # BGR
TURUNCU = (30, 130, 240)        # BGR
ZEMIN = (150, 150, 150)


def sahne(alt_x, aci_derece, serit=True):
    """Alt kenarı alt_x pikselinde kesen, aci_derece kadar yatık bir şerit çizer."""
    img = np.full((Y, G, 3), ZEMIN, np.uint8)
    if serit:
        dx = math.tan(math.radians(aci_derece)) * Y
        alt, ust = (int(alt_x), Y - 1), (int(alt_x + dx), 0)
        cv2.line(img, alt, ust, MAVI, 90)       # dış mavi bant
        cv2.line(img, alt, ust, TURUNCU, 30)    # ortadaki turuncu bant
    # zemin dokusu gibi hafif gürültü
    gurultu = np.random.default_rng(0).integers(-8, 9, img.shape, dtype=np.int16)
    return np.clip(img.astype(np.int16) + gurultu, 0, 255).astype(np.uint8)


def kontrol(ad, alt_x, aci):
    s = cizgi_bul(sahne(alt_x, aci))
    assert s["bulundu"], f"{ad}: çizgi bulunamadı"
    beklenen = alt_x - G / 2
    assert abs(s["sapma_px"] - beklenen) < 6, f"{ad}: sapma {s['sapma_px']:.1f}, beklenen {beklenen}"
    assert abs(s["aci"] - aci) < 2, f"{ad}: açı {s['aci']:.1f}, beklenen {aci}"
    print(f"TAMAM  {ad:28s} sapma {s['sapma_px']:+7.1f} px   açı {s['aci']:+5.1f}°")


if __name__ == "__main__":
    kontrol("ortada, düz", 320, 0)
    kontrol("sağda, düz", 420, 0)
    kontrol("solda, düz", 200, 0)
    kontrol("ortada, sağa yatık", 320, 15)
    kontrol("sağda, sola yatık", 400, -20)

    assert not cizgi_bul(sahne(0, 0, serit=False))["bulundu"], "boş zeminde çizgi bulundu"
    print("TAMAM  şerit yokken 'çizgi yok'")

    # Yalnızca mavi bant varsa (turuncu yok) çizgi sayılmamalı
    yalniz_mavi = np.full((Y, G, 3), ZEMIN, np.uint8)
    cv2.line(yalniz_mavi, (320, Y - 1), (320, 0), MAVI, 90)
    assert not cizgi_bul(yalniz_mavi)["bulundu"], "mavi bant turuncu sanıldı"
    print("TAMAM  yalnızca mavi bant çizgi sayılmıyor")
    print("\nTüm testler geçti.")
