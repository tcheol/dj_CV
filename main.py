"""
Gesture-Controlled DJ Controller
─────────────────────────────────
Run:  python main.py

Controls
  Q          quit
  I          open import dialog
  Gestures   see hint panel (top-right of window)
"""

from camera       import CameraManager
from app_window   import AppWindow
from song_library import SongLibrary
from dj_engine    import DJEngine

# ── Stub imports (uncomment as your team builds each module) ──
# from hand_tracker       import HandTracker
# from gesture_classifier import classify, GestureDebouncer
# from event_bus          import EventBus


def main():
    # ── Camera ───────────────────────────────────────────
    cam = CameraManager()

    # ── Song library (loads songs.json automatically) ────
    library = SongLibrary()

    # ── DJ engine ────────────────────────────────────────
    dj = DJEngine()

    # ── Components (uncomment as each module is ready) ───
    # tracker   = HandTracker()
    # debouncer = GestureDebouncer()
    # bus       = EventBus(dj, library)

    # ── Application window ───────────────────────────────
    win = AppWindow(
        camera_manager = cam,
        dj_engine      = dj,
        song_library   = library,
    )

    # Populate the song panel with any previously saved tracks
    win._song_panel.refresh()

    print('─' * 50)
    print('  DJ Controller started')
    print(f'  Camera  : {cam.width}×{cam.height} @ {cam.fps:.0f} fps')
    print(f'  Library : {len(library)} song(s) loaded')
    print('  Q = quit   |   I = import songs')
    print('─' * 50)

    # Start the camera-to-canvas polling loop
    win.start_feed()

    # ── Tkinter event loop (blocks until window closes) ──
    win.mainloop()

    # ── Cleanup ──────────────────────────────────────────
    print('[INFO] Shutting down...')
    dj.cleanup()
    cam.release()
    # tracker.close()   # uncomment when hand_tracker is ready
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


if __name__ == '__main__':
    main()
