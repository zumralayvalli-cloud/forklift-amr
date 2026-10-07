import cv2

cap = cv2.VideoCapture(0)
detector = cv2.QRCodeDetector()

while True:
    ok, frame = cap.read()
    if not ok:
        print("Kamera okunamadı")
        break

    veri, nokta, _ = detector.detectAndDecode(frame)
    if veri:
        print("QR:", veri)

    cv2.imshow("Kamera", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()