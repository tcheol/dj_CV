import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import RunningMode
import numpy as np
import os


# ── Landmark indices (same as gesture_classifier.py) ──
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17),
]

MODEL_PATH = "hand_landmarker.task"


class _FakeLandmark:
    """Wraps a single (x, y, z) so gesture_classifier can read .landmark[i].x/y"""
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class _FakeHandLandmarks:
    """
    Mimics the mediapipe NormalizedLandmarkList object so that
    gesture_classifier.classify() works without any changes.
    """
    def __init__(self, landmarks):
        self.landmark = [_FakeLandmark(lm.x, lm.y, lm.z) for lm in landmarks]


class HandTracker:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"\n[HandTracker] Model file not found: '{MODEL_PATH}'\n"
                "Download it from:\n"
                "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
                "hand_landmarker/float16/1/hand_landmarker.task\n"
                f"Then place it in your project folder next to main.py."
            )

        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._detector = vision.HandLandmarker.create_from_options(options)
        print('[HandTracker] Initialized successfully (MediaPipe 0.10+).')

    def find_hand(self, img):
        """
        Process a BGR frame and return:
          img            – annotated frame with landmarks drawn
          lm_list        – list of (id, cx, cy) in pixel coords
          hand_landmarks – fake landmark object compatible with gesture_classifier
        """
        h, w, _ = img.shape

        # Convert BGR → RGB for MediaPipe
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self._detector.detect(mp_image)

        lm_list        = []
        hand_landmarks = None

        if result.hand_landmarks:
            lms = result.hand_landmarks[0]   # first hand only
            hand_landmarks = _FakeHandLandmarks(lms)

            # Build pixel-coord list and draw
            for id, lm in enumerate(lms):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append((id, cx, cy))

                if id in [4, 8, 12, 16, 20]:
                    cv2.circle(img, (cx, cy), 10, (255, 0, 255), cv2.FILLED)

            # Draw connections
            for a, b in HAND_CONNECTIONS:
                if a < len(lm_list) and b < len(lm_list):
                    cv2.line(
                        img,
                        (lm_list[a][1], lm_list[a][2]),
                        (lm_list[b][1], lm_list[b][2]),
                        (255, 255, 255), 1
                    )

        return img, lm_list, hand_landmarks
