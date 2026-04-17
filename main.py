"""
Gesture-Controlled DJ Controller
─────────────────────────────────
Run:  python main.py

Controls
  Q          quit
  I          open import dialog
  F / F11    toggle fullscreen
  Gestures   see gesture_classifier.py
"""

from camera             import CameraManager
from app_window         import AppWindow
from song_library       import SongLibrary
from dj_engine          import DJEngine
from hand_tracker       import HandTracker
from gesture_classifier import classify, GestureDebouncer
from event_bus          import EventBus


def main():
    cam     = CameraManager()
    library = SongLibrary()
    dj      = DJEngine()

    tracker   = HandTracker()
    debouncer = GestureDebouncer()
    bus       = EventBus(dj, library)

    win = AppWindow(
        camera_manager = cam,
        dj_engine      = dj,
        song_library   = library,
    )

    win._song_panel.refresh()
    bus.set_song_panel(win._song_panel)

    print('─' * 50)
    print('  DJ Controller started')
    print(f'  Camera  : {cam.width}×{cam.height} @ {cam.fps:.0f} fps')
    print(f'  Library : {len(library)} song(s) loaded')
    print('  Q = quit   |   I = import   |   F = fullscreen')
    print('─' * 50)

    # ── Single unified loop — reads camera, runs hand tracking,
    #    draws landmarks, then pushes the annotated frame to the canvas.
    #    Do NOT call win.start_feed() — this loop replaces it.
    def gesture_loop():
        frame = cam.read()
        if frame is not None:
            # Run hand tracking and draw landmarks onto the frame
            frame, lm_list, hand_landmarks = tracker.find_hand(frame)

            if hand_landmarks:
                raw_gesture = classify(hand_landmarks)
                fired = debouncer.update(raw_gesture)
                if fired:
                    bus.dispatch(fired)
            else:
                debouncer.reset()

            # Push the annotated frame to the window canvas
            win.draw_overlay(frame)

        win.after(33, gesture_loop)

    win.after(0, gesture_loop)   # start on first Tk tick
    win.mainloop()

    print('[INFO] Shutting down...')
    dj.cleanup()
    cam.release()


if __name__ == '__main__':
    main()
