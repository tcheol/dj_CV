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

from camera      import CameraManager
from app_window  import AppWindow

# ── Stub imports (uncomment as your team builds each module) ──
# from hand_tracker       import HandTracker
# from gesture_classifier import classify, GestureDebouncer
# from dj_engine          import DJEngine
# from song_library       import SongLibrary
# from event_bus          import EventBus


def main():
    # ── Camera ───────────────────────────────────────────
    cam = CameraManager()

    # ── Components (uncomment as each module is ready) ───
    # tracker   = HandTracker()
    # debouncer = GestureDebouncer()
    # dj        = DJEngine()
    # library   = SongLibrary()
    # bus       = EventBus(dj, library)

    # ── Application window ───────────────────────────────
    win = AppWindow(
        camera_manager = cam,
        dj_engine      = None,   # swap to dj      when ready
        song_library   = None,   # swap to library  when ready
    )

    print('─' * 50)
    print('  DJ Controller started')
    print(f'  Camera: {cam.width}×{cam.height} @ {cam.fps:.0f} fps')
    print('  Q = quit   |   I = import songs')
    print('─' * 50)

    # Start the camera-to-canvas polling loop
    win.start_feed()

    # ── Main gesture loop (runs before mainloop blocks) ──
    # Once hand_tracker and gesture_classifier are ready,
    # replace start_feed() above with a manual loop like this:
    #
    # def gesture_loop():
    #     frame = cam.read()
    #     if frame is not None:
    #         results     = tracker.process(frame)
    #         raw_gesture = None
    #         index_tip   = None
    #
    #         if results.multi_hand_landmarks:
    #             hand        = results.multi_hand_landmarks[0]
    #             raw_gesture = classify(hand)
    #             index_tip   = tracker.get_index_tip_px(hand, cam.width, cam.height)
    #             tracker.draw_landmarks(frame, hand)
    #
    #         fired = debouncer.update(raw_gesture)
    #         if fired:
    #             bus.dispatch(fired)
    #
    #         win.draw_overlay(frame)
    #
    #     win.after(33, gesture_loop)
    #
    # win.after(0, gesture_loop)

    # ── Tkinter event loop (blocks until window closes) ──
    win.mainloop()

    # ── Cleanup ──────────────────────────────────────────
    print('[INFO] Shutting down...')
    cam.release()
    # tracker.close()   # uncomment when hand_tracker is ready


if __name__ == '__main__':
    main()
