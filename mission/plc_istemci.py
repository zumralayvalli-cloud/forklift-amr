import os
import socket
import struct
import threading
import time

# Ek Teknik Şartname: PLC simülatörü UDP, 192.168.100.100:1515
PLC_IP = os.environ.get("PLC_IP", "192.168.100.100")
PLC_PORT = int(os.environ.get("PLC_PORT", "1515"))
PERIYOT = 0.9          # saniyede bir PAKET_TX
YANIT_BEKLEME = 0.5    # bir pakete cevap için beklenen süre


def tx_paketi(durum, alim, birakma, x_m, y_m):
    """PAKET_TX: 7 byte. Durum, alım, bırakma, X (int16 LSB,MSB), Y (int16 LSB,MSB). X = int(x*100)."""
    x = max(-32768, min(32767, int(round(x_m * 100))))
    y = max(-32768, min(32767, int(round(y_m * 100))))
    return struct.pack("<BBBhh", durum, alim, birakma, x, y)


def rx_coz(veri):
    """PAKET_RX: 3 byte. Alım, bırakma, kontrol (1: bekle, 2: başla/devam et)."""
    if len(veri) < 3:
        return None
    return struct.unpack("<BBB", veri[:3])


class PlcIstemci(threading.Thread):
    def __init__(self, robot, kilit, ip=PLC_IP, port=PLC_PORT):
        super().__init__(daemon=True)
        self.robot = robot
        self.kilit = kilit
        self.adres = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(YANIT_BEKLEME)
        self._dur = threading.Event()
        self._kacirilan = 0

    def durdur(self):
        self._dur.set()

    def run(self):
        print(f"PLC istemcisi başladı -> {self.adres[0]}:{self.adres[1]}")
        sonraki = time.monotonic()
        while not self._dur.is_set():
            with self.kilit:
                bilgi = self.robot.paket_bilgisi()
            try:
                self.sock.sendto(tx_paketi(*bilgi), self.adres)
                self._yanit_bekle(bilgi[0])
            except OSError as hata:
                self._kayip(f"ağ hatası: {hata}")
            sonraki += PERIYOT
            kalan = sonraki - time.monotonic()
            if kalan > 0:
                time.sleep(kalan)
            else:
                sonraki = time.monotonic()

    def _yanit_bekle(self, gonderilen_durum):
        try:
            veri, _ = self.sock.recvfrom(64)
        except socket.timeout:
            self._kayip("PLC cevap vermedi")
            return
        sonuc = rx_coz(veri)
        if sonuc is None:
            print("PLC: geçersiz paket boyutu:", len(veri))
            return
        self._kacirilan = 0
        alim, birakma, kontrol = sonuc
        with self.kilit:
            self.robot.plc_rx(alim, birakma, kontrol, gonderilen_durum)

    def _kayip(self, neden):
        self._kacirilan += 1
        if self._kacirilan == 2:
            print(f"PLC bağlantısı kayıp ({neden})")
            with self.kilit:
                self.robot.plc_bagli = False