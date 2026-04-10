import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class HandTracker:
    def __init__(self):
        # MediaPipe 0.10+ API
        try:
            self.mpHands = mp.solutions.hands
            self.hands   = self.mpHands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5,
            )
            self.mpDraw  = mp.solutions.drawing_utils
            self._ready  = True
            print('[HandTracker] Initialized successfully.')
        except Exception as e:
            print(f'[HandTracker] Init failed: {e}')
            self._ready = False

    def find_hand(self, img):
        """
        Process a BGR frame and return (annotated_img, lm_list, hand_landmarks).

        lm_list       — list of (id, cx, cy) in pixel coords
        hand_landmarks — raw MediaPipe landmark object for gesture_classifier
        """
        if not self._ready:
            return img, [], None

        imgRGB  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(imgRGB)

        lm_list        = []
        hand_landmarks = None

        if results.multi_hand_landmarks:
            # Use only first hand
            handLms = results.multi_hand_landmarks[0]
            hand_landmarks = handLms

            h, w, _ = img.shape
            for id, lm in enumerate(handLms.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append((id, cx, cy))

                # Draw fingertip dots
                if id in [4, 8, 12, 16, 20]:
                    cv2.circle(img, (cx, cy), 10, (255, 0, 255), cv2.FILLED)

            self.mpDraw.draw_landmarks(
                img, handLms, self.mpHands.HAND_CONNECTIONS
            )

        return img, lm_list, hand_landmarks
