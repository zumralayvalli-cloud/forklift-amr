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


# Simülasyon: her durumun süresi (saniye). Gerçek robotta sensörler/olaylar belirler.
SURELER = {
    Durum.YUKE_GIT: 3,
    Durum.YUKLE: 2,
    Durum.BIRAKMAYA_GIT: 3,
    Durum.BIRAK: 2,
    Durum.GERI_DON: 3,
}

SONRAKI = {
    Durum.YUKE_GIT: Durum.YUKLE,
    Durum.YUKLE: Durum.BIRAKMAYA_GIT,
    Durum.BIRAKMAYA_GIT: Durum.BIRAK,
    Durum.BIRAK: Durum.GERI_DON,
    Durum.GERI_DON: Durum.BEKLE,
}


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
        if self.durum in (Durum.BEKLE, Durum.ACIL_DURUS):
            return
        self.gecen += dt
        if self.gecen >= SURELER[self.durum]:
            self._gec(SONRAKI[self.durum])
            if self.durum == Durum.BEKLE:
                print("Görev tamamlandı\n")
                self.gorev = None


if __name__ == "__main__":
    robot = GorevYoneticisi()
    DT = 0.5
    t = 0.0
    while t < 22:
        if t == 1.0:
            robot.gorev_al("A1", "B2")
        if t == 5.0:
            print("!!! Kill switch basıldı")
            robot.acil_durdur()
        if t == 8.0:
            print("Kill switch bırakıldı")
            robot.devam_et()
        if t == 10.0:
            robot.gorev_al("C1", "D1")  # robot meşgulken reddedilmeli
        robot.adim(DT)
        t += DT
        time.sleep(DT / 5)  # simülasyonu hızlandır