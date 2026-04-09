import cv2
import mediapipe as mp


class HandTracker:
    def __init__(self):
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands()
        self.mpDraw = mp.solutions.drawing_utils

    def find_hand(self, img):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(imgRGB)

        lm_list = []

        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                for id, lm in enumerate(handLms.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append((id, cx, cy))

                    if id in [4,8,12,16,20]:
                        cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
                    
                self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)
        return img, lm_list
