import logging
import os
import threading
import time

import paho.mqtt.client as mqtt

from arayuz import uygulama_olustur
from gorev_yoneticisi import GorevYoneticisi
from plc_istemci import PlcIstemci

# MQTT yalnızca robot içindeki yerel girişler için: QR okuyucu ve kill switch
BROKER = "localhost"
MQTT_PORT = 1883
ARAYUZ_PORT = int(os.environ.get("ARAYUZ_PORT", "8080"))

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
mqtt_var = False
try:
    client.connect(BROKER, MQTT_PORT)
    client.loop_start()
    mqtt_var = True
except OSError:
    print("MQTT broker bulunamadı: QR ve kill yalnızca arayüzün geliştirme panelinden girilebilir")

# Kullanıcı arayüzü (web). Her istek terminale yazılmasın diye Flask günlüğü kısılır.
logging.getLogger("werkzeug").setLevel(logging.ERROR)
uygulama = uygulama_olustur(robot, kilit)
threading.Thread(
    target=lambda: uygulama.run(host="0.0.0.0", port=ARAYUZ_PORT, threaded=True, use_reloader=False),
    daemon=True,
).start()
print(f"Arayüz: http://localhost:{ARAYUZ_PORT}")

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
            if mqtt_var:
                client.publish("amr/durum", durum, retain=True)
            son_durum = durum

        time.sleep(0.1)
except KeyboardInterrupt:
    print("Robot kapatılıyor")
    plc.durdur()
    if mqtt_var:
        client.loop_stop()
        client.disconnect()