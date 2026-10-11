import time
from enum import Enum, auto


class Durum(Enum):
    BEKLE = auto()
    YUKE_GIT = auto()
    YUKLE = auto()
    BIRAKMAYA_GIT = auto()
    BIRAK = auto()
    GERI_DON = auto()
    ACIL_DURUS = auto()


# Sadece süreyle biten durumlar (kaldırma mekanizması simülasyonu).
# Diğer durumlar QR okunca biter.
SURELER = {
    Durum.YUKLE: 2,
    Durum.BIRAK: 2,
}

SONRAKI = {
    Durum.YUKE_GIT: Durum.YUKLE,
    Durum.YUKLE: Durum.BIRAKMAYA_GIT,
    Durum.BIRAKMAYA_GIT: Durum.BIRAK,
    Durum.BIRAK: Durum.GERI_DON,
    Durum.GERI_DON: Durum.BEKLE,
}

BASLANGIC_QR = "HOME"


class GorevYoneticisi:
    def __init__(self):
        self.durum = Durum.BEKLE
        self.onceki = None
        self.gorev = None
        self.gecen = 0.0
        self.kayitli_gecen = 0.0

    def _gec(self, yeni):
        print(f"[{self.durum.name}] -> [{yeni.name}]")
        self.durum = yeni
        self.gecen = 0.0
        if yeni == Durum.BEKLE:
            print("Görev tamamlandı\n")
            self.gorev = None

    def beklenen_qr(self):
        if self.gorev is None:
            return None
        if self.durum == Durum.YUKE_GIT:
            return self.gorev[0]
        if self.durum == Durum.BIRAKMAYA_GIT:
            return self.gorev[1]
        if self.durum == Durum.GERI_DON:
            return BASLANGIC_QR
        return None

    def qr_okundu(self, veri):
        beklenen = self.beklenen_qr()
        if beklenen is None:
            return  # şu an QR beklenmiyor (veya acil duruştayız)
        if veri == beklenen:
            print(f"QR doğrulandı: {veri}")
            self._gec(SONRAKI[self.durum])
        else:
            print(f"Yanlış QR: {veri} (beklenen: {beklenen})")

    def gorev_al(self, yuk_noktasi, birakma_noktasi):
        if self.durum != Durum.BEKLE:
            print(f"Meşgul ({self.durum.name}), görev reddedildi")
            return False
        self.gorev = (yuk_noktasi, birakma_noktasi)
        print(f"Görev alındı: {yuk_noktasi} -> {birakma_noktasi}")
        self._gec(Durum.YUKE_GIT)
        return True

    def acil_durdur(self):
        if self.durum == Durum.ACIL_DURUS:
            return
        self.onceki = self.durum
        self.kayitli_gecen = self.gecen
        self._gec(Durum.ACIL_DURUS)

    def devam_et(self):
        if self.durum != Durum.ACIL_DURUS:
            return
        kayit = self.kayitli_gecen
        self._gec(self.onceki)
        self.gecen = kayit

    def adim(self, dt):
        if self.durum not in SURELER:
            return
        self.gecen += dt
        if self.gecen >= SURELER[self.durum]:
            self._gec(SONRAKI[self.durum])


if __name__ == "__main__":
    robot = GorevYoneticisi()
    robot.gorev_al("A1", "B2")
    for qr, bekle in [("X9", 0), ("A1", 2.5), ("B2", 2.5), ("HOME", 0)]:
        robot.qr_okundu(qr)
        t = 0.0
        while t < bekle:
            robot.adim(0.5)
            t += 0.5