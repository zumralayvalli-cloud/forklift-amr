import cv2

cap = cv2.VideoCapture(0)

while True:
    ok, frame = cap.read()
    if not ok:
        print("Kamera okunamadı")
        break

    h, w = frame.shape[:2]

    # Görüntünün alt yarısına bak (robotun önündeki zemin)
    roi = frame[h // 2:, :]
    gri = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gri = cv2.GaussianBlur(gri, (5, 5), 0)

    # Koyu çizgiyi beyaz yap
    _, maske = cv2.threshold(gri, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # En büyük koyu bölgeyi bul
    konturlar, _ = cv2.findContours(maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if konturlar:
        en_buyuk = max(konturlar, key=cv2.contourArea)
        M = cv2.moments(en_buyuk)
        if M["m00"] > 500:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            sapma = cx - w // 2
            print(f"Sapma: {sapma} piksel")
            cv2.circle(roi, (cx, cy), 8, (0, 0, 255), -1)

    # Merkez çizgisi
    cv2.line(roi, (w // 2, 0), (w // 2, roi.shape[0]), (0, 255, 0), 1)

    cv2.imshow("Cizgi takibi", roi)
    cv2.imshow("Maske", maske)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()