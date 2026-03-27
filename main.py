"""
Gesture-Controlled DJ Controller
─────────────────────────────────
Run:  python main.py

Controls
  Q          quit
  I          open import dialog
  Gestures   see hint panel (top-right of window)
"""

import sys
import cv2

from config          import WINDOW_NAME, DISPLAY_WIDTH, DISPLAY_HEIGHT
from camera          import CameraManager

# ── Stub imports (implement these next) ───────
# from hand_tracker       import HandTracker
# from gesture_classifier import classify, GestureDebouncer
# from dj_engine          import DJEngine
# from song_library       import SongLibrary
# from ui_renderer        import UIRenderer
# from event_bus          import EventBus


def main():
    # ── Camera ───────────────────────────────────────────
    cam = CameraManager()

    # Resize the display window to the configured size.
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # ── Components (uncomment as you build each module) ──
    # tracker   = HandTracker()
    # debouncer = GestureDebouncer()
    # dj        = DJEngine()
    # library   = SongLibrary()
    # renderer  = UIRenderer()
    # bus       = EventBus(dj, library)

    print('─' * 50)
    print('  DJ Controller started')
    print(f'  Camera: {cam.width}×{cam.height} @ {cam.fps:.0f} fps')
    print('  Q = quit   |   I = import songs')
    print('─' * 50)

    while True:
        # ── Capture ──────────────────────────────────────
        frame = cam.read()

        if frame is None:
            print('[ERROR] Lost camera feed.')
            break

        h, w = frame.shape[:2]

        # ── Hand detection (stub) ─────────────────────────
        # results     = tracker.process(frame)
        # raw_gesture = None
        # index_tip   = None

        # if results.multi_hand_landmarks:
        #     hand        = results.multi_hand_landmarks[0]
        #     raw_gesture = classify(hand)
        #     index_tip   = tracker.get_index_tip_px(hand, w, h)
        #     tracker.draw_landmarks(frame, hand)

        # ── Hover, debounce, fire (stub) ──────────────────
        # hovered_card = -1
        # if raw_gesture == 'point' and index_tip:
        #     hovered_card = renderer.get_card_at(index_tip)
        # if not results.multi_hand_landmarks:
        #     debouncer.reset()
        # fired = debouncer.update(raw_gesture)
        # if fired:
        #     if fired == 'point' and hovered_card >= 0:
        #         bus.dispatch('point_select', hovered_card)
        #     elif fired != 'point':
        #         bus.dispatch(fired)

        # ── Render UI overlay (stub) ──────────────────────
        # renderer.render(frame, library, dj, raw_gesture, hovered_card)

        # ── Display ───────────────────────────────────────
        cv2.imshow(WINDOW_NAME, frame)

        # ── Keyboard shortcuts ────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('i'):
            print('[INFO] Import dialog — SongLibrary not yet implemented.')

    # ── Cleanup ──────────────────────────────────────────
    print('[INFO] Shutting down...')
    cam.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
