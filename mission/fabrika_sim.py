import json
import time

import paho.mqtt.client as mqtt


def baglandi(client, userdata, flags, reason_code, properties):
    client.subscribe("amr/durum")


def mesaj_geldi(client, userdata, msg):
    print("Robot durumu:", msg.payload.decode())


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = baglandi
client.on_message = mesaj_geldi
client.connect("localhost", 1883)
client.loop_start()

time.sleep(1)
gorev = {"yuk": "A1", "birakma": "B2"}
client.publish("amr/gorev", json.dumps(gorev))
print("Görev gönderildi:", gorev)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()