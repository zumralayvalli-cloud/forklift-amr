import time

import cv2
import paho.mqtt.client as mqtt

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("localhost", 1883)
client.loop_start()

cap = cv2.VideoCapture(0)
detector = cv2.QRCodeDetector()

son_veri = None
son_zaman = 0.0

while True:
    ok, frame = cap.read()
    if not ok:
        print("Kamera okunamadı")
        break

    veri, nokta, _ = detector.detectAndDecode(frame)
    simdi = time.time()
    # Aynı QR'ı 2 saniye içinde tekrar yayınlama
    if veri and (veri != son_veri or simdi - son_zaman > 2):
        print("QR yayınlandı:", veri)
        client.publish("amr/qr", veri)
        son_veri = veri
        son_zaman = simdi

    cv2.imshow("QR", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
client.loop_stop()
client.disconnect()