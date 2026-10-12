import math
from enum import Enum


class Durum(Enum):
    # Değerler PLC protokolündeki PAKET_TX Byte0 kodlarıdır (Ek Teknik Şartname)
    IDLE = 1              # göreve hazır bekleme
    GOREV_ISLENIYOR = 2   # görev alındı, işleniyor
    YUKSUZ_HAREKET = 3    # görev alındı, yüksüz hareket
    YUKLU_HAREKET = 4     # görev alındı, yüklü hareket
    KAPI_BEKLENIYOR = 5   # fabrika otomasyon sistemi komutu bekleniyor
    BASLANGICA_DONUS = 6  # görev tamamlandı, başlangıç noktasına hareket
    HATA = 7              # hata durumu
    ACIL_STOP = 8         # acil stop durumu


# QR kod metinleri (Ek Teknik Şartname, Tablo 2)
BEKLEME_QR = "BASLA"                                   # Q1
ALMA_QR = {1: "ALIM1", 2: "ALIM2", 3: "ALIM3"}         # Q2, Q3, Q4
KAPI_GIDIS_QR = "KAPI1"                                # Q5
KAPI_DONUS_QR = "KAPI2"                                # Q6 (dönüşte kullanılması varsayım)
BIRAKMA_QR = {1: "BIRAK1", 2: "BIRAK2", 3: "BIRAK3"}   # Q9, Q8, Q7

# Simülasyon süreleri (saniye). Gerçek robotta sensörler belirler.
ROTA_HESAPLAMA_SURESI = 1.0
YUKLEME_SURESI = 2.0
BIRAKMA_SURESI = 2.0

# Şartname: 30 dk hedef, 45 dk üst limit
HEDEF_SURE = 30 * 60
UST_LIMIT = 45 * 60


class GorevYoneticisi:
    def __init__(self):
        self.durum = Durum.IDLE
        self.faz = ""
        self.gecen = 0.0
        self.toplam_sure = 0.0
        self.mod = "otomatik"        # robot üzerindeki anahtar: "otomatik" / "manuel"
        self.gorev = None            # {"alim": 1..3, "birakma": 1..3}
        self.yuklu = False
        self.baslat_izni = False     # PLC "Göreve başla" (kontrol=2) verdi mi
        self.kapi_sonrasi = None
        self.son_biten = None        # biten görev tekrar kabul edilmesin
        self.konum = (0.0, 0.0)      # metre; odometri/haritalama bağlanınca güncellenecek
        self.son_qr = None
        self.hata_mesaji = None
        self.plc_bagli = False
        self.mesajlar = []           # arayüz için: ("gelen"/"giden", içerik)
        self._kayit_acil = None
        self._kayit_hata = None

    # ---------- yardımcılar ----------
    def _gec(self, yeni, faz=""):
        ek = f" ({faz})" if faz else ""
        print(f"[{self.durum.name}] -> [{yeni.name}]{ek}")
        self.durum = yeni
        self.faz = faz
        self.gecen = 0.0

    def konum_guncelle(self, x_m, y_m):
        self.konum = (x_m, y_m)

    def paket_bilgisi(self):
        """PAKET_TX için: (durum, alım, bırakma, x_m, y_m)"""
        alim = self.gorev["alim"] if self.gorev else 0
        birakma = self.gorev["birakma"] if self.gorev else 0
        return (self.durum.value, alim, birakma, self.konum[0], self.konum[1])

    def durum_bilgisi(self):
        """Kullanıcı arayüzü için tüm bilgiler tek yerde."""
        return {
            "durum": self.durum.name,
            "faz": self.faz,
            "mod": self.mod,
            "gorev": self.gorev,
            "yuklu": self.yuklu,
            "son_qr": self.son_qr,
            "plc_bagli": self.plc_bagli,
            "hata": self.hata_mesaji,
            "konum": self.konum,
            "gecen_sure_sn": round(self.toplam_sure, 1),
        }

    def beklenen_qr(self):
        if self.mod != "otomatik" or self.gorev is None:
            return None
        d, f = self.durum, self.faz
        if d == Durum.YUKSUZ_HAREKET and f == "alma_noktasina_gidiyor":
            return ALMA_QR[self.gorev["alim"]]
        if d == Durum.YUKLU_HAREKET and f == "kapiya_gidiyor":
            return KAPI_GIDIS_QR
        if d == Durum.YUKLU_HAREKET and f == "birakma_noktasina_gidiyor":
            return BIRAKMA_QR[self.gorev["birakma"]]
        if d == Durum.BASLANGICA_DONUS and f == "kapiya_gidiyor":
            return KAPI_DONUS_QR
        if d == Durum.BASLANGICA_DONUS and f == "beklemeye_gidiyor":
            return BEKLEME_QR
        return None

    # ---------- dış olaylar ----------
    def gorev_al(self, alim, birakma):
        if self.mod != "otomatik":
            print("Manuel moddayken görev alınamaz")
            return False
        if self.durum != Durum.IDLE:
            print(f"Meşgul ({self.durum.name}), görev reddedildi")
            return False
        if alim not in ALMA_QR or birakma not in BIRAKMA_QR:
            print(f"Geçersiz nokta: A{alim} -> B{birakma}")
            return False
        self.gorev = {"alim": alim, "birakma": birakma}
        self.toplam_sure = 0.0
        self.yuklu = False
        self.baslat_izni = False
        print(f"Görev alındı: A{alim} -> B{birakma}")
        self._gec(Durum.GOREV_ISLENIYOR)
        return True

    def plc_rx(self, alim, birakma, kontrol, gonderilen_durum):
        """PLC'den gelen PAKET_RX. gonderilen_durum: bu cevabın ait olduğu PAKET_TX'teki durum kodu."""
        self.plc_bagli = True
        self.mesajlar.append(("gelen", {"alim": alim, "birakma": birakma, "kontrol": kontrol}))

        if (alim, birakma) == (0, 0):
            self.son_biten = None  # PLC görevi sıfırladı, yeni görev kabul edilebilir

        # Yeni görev: sadece boştayken, PLC robotun IDLE olduğunu gördükten sonra
        if (self.durum == Durum.IDLE and gonderilen_durum == Durum.IDLE.value
                and alim in ALMA_QR and birakma in BIRAKMA_QR
                and (alim, birakma) != self.son_biten):
            self.gorev_al(alim, birakma)

        if kontrol == 1 and self.durum == Durum.GOREV_ISLENIYOR:
            self.baslat_izni = False
        elif kontrol == 2:
            if self.durum == Durum.GOREV_ISLENIYOR:
                self.baslat_izni = True
            elif self.durum == Durum.KAPI_BEKLENIYOR and gonderilen_durum == Durum.KAPI_BEKLENIYOR.value:
                # PLC robotun kapıda olduğunu gördü ve geçiş izni verdi
                durum, faz = self.kapi_sonrasi
                print("PLC: kapı açık, geçiş izni verildi")
                self._gec(durum, faz)

    def qr_okundu(self, veri):
        veri = veri.strip().upper()
        self.son_qr = veri
        beklenen = self.beklenen_qr()
        if beklenen is None:
            return
        if veri != beklenen:
            print(f"Yanlış QR: {veri} (beklenen: {beklenen})")
            return
        print(f"QR doğrulandı: {veri}")
        d, f = self.durum, self.faz
        if d == Durum.YUKSUZ_HAREKET and f == "alma_noktasina_gidiyor":
            self._gec(Durum.YUKSUZ_HAREKET, "yukleniyor")
        elif d == Durum.YUKLU_HAREKET and f == "kapiya_gidiyor":
            self.kapi_sonrasi = (Durum.YUKLU_HAREKET, "birakma_noktasina_gidiyor")
            self._gec(Durum.KAPI_BEKLENIYOR)
        elif d == Durum.YUKLU_HAREKET and f == "birakma_noktasina_gidiyor":
            self._gec(Durum.YUKLU_HAREKET, "birakiyor")
        elif d == Durum.BASLANGICA_DONUS and f == "kapiya_gidiyor":
            self.kapi_sonrasi = (Durum.BASLANGICA_DONUS, "beklemeye_gidiyor")
            self._gec(Durum.KAPI_BEKLENIYOR)
        elif d == Durum.BASLANGICA_DONUS and f == "beklemeye_gidiyor":
            self._bitir()

    def acil_durdur(self):
        if self.durum == Durum.ACIL_STOP:
            return
        self._kayit_acil = (self.durum, self.faz, self.gecen)
        self._gec(Durum.ACIL_STOP)

    def devam_et(self):
        if self.durum != Durum.ACIL_STOP:
            return
        durum, faz, gecen = self._kayit_acil
        self._gec(durum, faz)
        self.gecen = gecen

    def hata_bildir(self, mesaj):
        if self.durum == Durum.ACIL_STOP:
            print("Acil stop aktif, hata kaydı beklemeye alındı:", mesaj)
            return
        if self.durum == Durum.HATA:
            return
        self.hata_mesaji = mesaj
        self._kayit_hata = (self.durum, self.faz, self.gecen)
        self._gec(Durum.HATA)

    def hata_temizle(self):
        if self.durum != Durum.HATA:
            return
        durum, faz, gecen = self._kayit_hata
        self.hata_mesaji = None
        self._gec(durum, faz)
        self.gecen = gecen

    def mod_degistir(self, yeni):
        if yeni not in ("otomatik", "manuel"):
            return
        if yeni != self.mod:
            print(f"Mod: {self.mod} -> {yeni}")
            self.mod = yeni

    def uzaktan_komut(self, sol, sag):
        """Uzaktan manuel sürüş. Sadece manuel modda ve acil stop yokken çalışır."""
        if self.mod != "manuel":
            print("Uzaktan kontrol reddedildi: anahtar OTOMATİK konumda")
            return False
        if self.durum == Durum.ACIL_STOP:
            print("Uzaktan kontrol reddedildi: acil stop aktif")
            return False
        print(f"Uzaktan komut: V,{sol},{sag}")
        return True

    # ---------- zaman ----------
    def adim(self, dt):
        if self.gorev is not None:
            self.toplam_sure += dt  # yarışma saati ne olursa olsun işler
        if self.mod != "otomatik":
            return
        if self.durum in (Durum.IDLE, Durum.ACIL_STOP, Durum.HATA, Durum.KAPI_BEKLENIYOR):
            return
        self.gecen += dt
        d, f = self.durum, self.faz
        if d == Durum.GOREV_ISLENIYOR:
            if self.gecen >= ROTA_HESAPLAMA_SURESI and self.baslat_izni:
                self._gec(Durum.YUKSUZ_HAREKET, "alma_noktasina_gidiyor")
        elif d == Durum.YUKSUZ_HAREKET and f == "yukleniyor" and self.gecen >= YUKLEME_SURESI:
            self.yuklu = True
            self._gec(Durum.YUKLU_HAREKET, "kapiya_gidiyor")
        elif d == Durum.YUKLU_HAREKET and f == "birakiyor" and self.gecen >= BIRAKMA_SURESI:
            self.yuklu = False
            self._gec(Durum.BASLANGICA_DONUS, "kapiya_gidiyor")

    def _bitir(self):
        sure = self.toplam_sure
        if sure <= HEDEF_SURE:
            puan = int((HEDEF_SURE - sure) // 60)
        else:
            puan = -math.ceil((sure - HEDEF_SURE) / 60)
        print(f"Görev tamamlandı. Süre: {sure:.1f} sn, süre puanı: {puan:+d}")
        if sure > UST_LIMIT:
            print("UYARI: 45 dakikalık üst limit aşıldı")
        self.son_biten = (self.gorev["alim"], self.gorev["birakma"])
        self.gorev = None
        self._gec(Durum.IDLE)
        print()