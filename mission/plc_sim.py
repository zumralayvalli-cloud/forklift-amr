import random
import socket
import struct
import time

# Yarışmadaki PLC simülatörünü taklit eder (UDP, port 1515).
HOST = "0.0.0.0"
PORT = 1515
KAPI_ACMA_SURESI = 3.0   # robot kapıya gelince kapının açılması için geçen süre (sn)

DURUMLAR = {1: "IDLE", 2: "GOREV_ISLENIYOR", 3: "YUKSUZ_HAREKET", 4: "YUKLU_HAREKET",
            5: "KAPI_BEKLENIYOR", 6: "BASLANGICA_DONUS", 7: "HATA", 8: "ACIL_STOP"}


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.settimeout(0.2)
    print(f"Sahte PLC dinliyor: UDP {PORT}")

    alim = birakma = 0
    gorev_verildi = False
    gorev_basladi = False
    gorev_bitti = False
    kapi_baslangic = None
    kapi_acik_yazildi = False
    son_durum = None
    son_paket = None
    bagli = False

    while True:
        try:
            veri, adres = sock.recvfrom(64)
        except socket.timeout:
            if bagli and son_paket and time.monotonic() - son_paket > 1.0:
                print("ZAMAN AŞIMI: 1 saniyedir paket gelmedi, bağlantı koptu")
                bagli = False
            continue

        if len(veri) != 7:
            print("Geçersiz paket boyutu:", len(veri))
            continue

        son_paket = time.monotonic()
        if not bagli:
            print("Robot bağlandı:", adres)
            bagli = True

        durum, r_alim, r_birakma, x, y = struct.unpack("<BBBhh", veri)
        if durum != son_durum:
            print(f"Robot durumu: {durum} ({DURUMLAR.get(durum, '?')})  "
                  f"görev: A{r_alim}->B{r_birakma}  konum: ({x / 100:.2f}, {y / 100:.2f}) m")
            son_durum = durum

        kontrol = 2  # varsayılan: başla/devam et

        if durum == 1:
            if not gorev_verildi:
                alim, birakma = random.randint(1, 3), random.randint(1, 3)
                gorev_verildi = True
                print(f"PLC görev tanımladı: A{alim} -> B{birakma}")
            elif gorev_basladi and not gorev_bitti:
                gorev_bitti = True
                alim = birakma = 0
                print("PLC: görev tamamlandı, robot bekleme noktasında")
        elif durum >= 2:
            gorev_basladi = True

        if durum == 5:
            if kapi_baslangic is None:
                kapi_baslangic = time.monotonic()
                kapi_acik_yazildi = False
                print("PLC: robot kapıda, kapı açılıyor...")
            if time.monotonic() - kapi_baslangic < KAPI_ACMA_SURESI:
                kontrol = 1  # bekle
            elif not kapi_acik_yazildi:
                print("PLC: kapı açık, geçiş izni verildi")
                kapi_acik_yazildi = True
        else:
            kapi_baslangic = None

        sock.sendto(struct.pack("<BBB", alim, birakma, kontrol), adres)


if __name__ == "__main__":
    main()