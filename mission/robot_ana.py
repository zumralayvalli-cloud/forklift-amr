import os
import threading
import time

import paho.mqtt.client as mqtt

from gorev_yoneticisi import GorevYoneticisi
from plc_istemci import PlcIstemci

# MQTT yalnızca robot içindeki yerel girişler için: QR okuyucu ve kill switch
BROKER = "localhost"
PORT = 1883

robot = GorevYoneticisi()
kilit = threading.Lock()


def baglandi(client, userdata, flags, reason_code, properties):
    print("Broker'a bağlandı:", reason_code)
    client.subscribe("amr/qr")
    client.subscribe("amr/kill")


def mesaj_geldi(client, userdata, msg):
    metin = msg.payload.decode()
    with kilit:
        if msg.topic == "amr/qr":
            robot.qr_okundu(metin)
        elif msg.topic == "amr/kill":
            if metin == "1":
                print("!!! Kill switch basıldı")
                robot.acil_durdur()
            else:
                print("Kill switch bırakıldı")
                robot.devam_et()


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = baglandi
client.on_message = mesaj_geldi
client.connect(BROKER, PORT)
client.loop_start()

plc = PlcIstemci(robot, kilit)
plc.start()

son_durum = None
son_zaman = time.time()

try:
    while True:
        simdi = time.time()
        with kilit:
            robot.adim(simdi - son_zaman)
            durum = robot.durum.name
        son_zaman = simdi

        if durum != son_durum:
            client.publish("amr/durum", durum, retain=True)
            son_durum = durum

        time.sleep(0.1)
except KeyboardInterrupt:
    print("Robot kapatılıyor")
    plc.durdur()
    client.loop_stop()
    client.disconnect()