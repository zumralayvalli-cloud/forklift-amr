import json
import threading
import time

import paho.mqtt.client as mqtt

from gorev_yoneticisi import GorevYoneticisi

BROKER = "localhost"
PORT = 1883

robot = GorevYoneticisi()
kilit = threading.Lock()  # MQTT mesajları ayrı bir iş parçacığında gelir


def baglandi(client, userdata, flags, reason_code, properties):
    print("Broker'a bağlandı:", reason_code)
    client.subscribe("amr/gorev")
    client.subscribe("amr/kill")
    client.subscribe("amr/qr")


def mesaj_geldi(client, userdata, msg):
    metin = msg.payload.decode()
    with kilit:
        if msg.topic == "amr/gorev":
            try:
                veri = json.loads(metin)
                robot.gorev_al(veri["yuk"], veri["birakma"])
            except (json.JSONDecodeError, KeyError, TypeError):
                print("Geçersiz görev mesajı:", metin)
        elif msg.topic == "amr/kill":
            if metin == "1":
                print("!!! Kill switch basıldı")
                robot.acil_durdur()
            else:
                print("Kill switch bırakıldı")
                robot.devam_et()
        elif msg.topic == "amr/qr":
            robot.qr_okundu(metin.strip())

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = baglandi
client.on_message = mesaj_geldi
client.connect(BROKER, PORT)
client.loop_start()

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
    client.loop_stop()
    client.disconnect()