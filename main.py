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

from config          import WINDOW_NAME
from hand_tracker    import HandTracker
from gesture_classifier import classify, GestureDebouncer
from dj_engine       import DJEngine
from song_library    import SongLibrary
from ui_renderer     import UIRenderer
from event_bus       import EventBus


def main():
    # ── Camera ───────────────────────────────────────────
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print('[ERROR] Cannot open webcam. Check that your camera is connected.')
        sys.exit(1)

    # Request 1280×720; fall back gracefully if camera doesn't support it
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # ── Components ───────────────────────────────────────
    tracker   = HandTracker()
    debouncer = GestureDebouncer()
    dj        = DJEngine()
    library   = SongLibrary()
    renderer  = UIRenderer()
    bus       = EventBus(dj, library)

    # Import callback — must run on the main thread (tkinter requirement)
    def do_import():
        added = library.import_songs_dialog()
        if added:
            print(f'[INFO] Imported {added} song(s).')

    bus.set_import_callback(do_import)

    print('─' * 50)
    print('  DJ Controller started')
    print('  Q = quit   |   I = import songs')
    print('─' * 50)

    hovered_card = -1

    while True:
        ret, frame = cap.read()
        if not ret:
            print('[ERROR] Lost camera feed.')
            break

        # Mirror so the image acts like a mirror (natural for the user)
        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]

        # ── Hand detection ───────────────────────────────
        results     = tracker.process(frame)
        raw_gesture = None
        index_tip   = None

        if results.multi_hand_landmarks:
            # Use only the first detected hand for control
            hand = results.multi_hand_landmarks[0]
            raw_gesture = classify(hand)
            index_tip   = tracker.get_index_tip_px(hand, w, h)
            tracker.draw_landmarks(frame, hand)

        # ── Hover (live, no debounce) ────────────────────
        if raw_gesture == 'point' and index_tip:
            hovered_card = renderer.get_card_at(index_tip)
        else:
            hovered_card = -1

        # Reset debouncer when no hands visible
        if not results.multi_hand_landmarks:
            debouncer.reset()

        # ── Debounce & fire ──────────────────────────────
        fired = debouncer.update(raw_gesture)
        if fired:
            if fired == 'point' and hovered_card >= 0:
                bus.dispatch('point_select', hovered_card)
            elif fired != 'point':
                bus.dispatch(fired)

        # ── Render UI overlay ────────────────────────────
        renderer.render(frame, library, dj, raw_gesture, hovered_card)

        cv2.imshow(WINDOW_NAME, frame)

        # ── Keyboard shortcuts ───────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('i'):
            do_import()

    # ── Cleanup ──────────────────────────────────────────
    print('[INFO] Shutting down...')
    tracker.close()
    dj.cleanup()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
