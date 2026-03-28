"""
camera_test.py  –  Simple camera preview
Press Q to quit.
"""

import cv2

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("Camera preview started — press Q to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Could not read from camera.")
        break

    frame = cv2.flip(frame, 1)  # mirror so it feels natural
    cv2.imshow("Camera Preview", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Camera closed.")
