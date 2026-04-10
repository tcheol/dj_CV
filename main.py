"""
Gesture-Controlled DJ Controller
─────────────────────────────────
Run:  python main.py

Controls
  Q          quit
  I          open import dialog
  Gestures   see hint panel (top-right of window)
"""

from camera              import CameraManager
from app_window          import AppWindow
from song_library        import SongLibrary
from dj_engine           import DJEngine
from hand_tracker        import HandTracker
from gesture_classifier  import classify, GestureDebouncer
from event_bus           import EventBus


def main():
    # ── Camera ───────────────────────────────────────────
    cam = CameraManager()

    # ── Song library (loads songs.json automatically) ────
    library = SongLibrary()

    # ── DJ engine ────────────────────────────────────────
    dj = DJEngine()

    # ── Hand tracking & gesture pipeline ─────────────────
    tracker   = HandTracker()
    debouncer = GestureDebouncer()
    bus       = EventBus(dj, library)

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

    # ── Gesture loop ─────────────────────────────────────
    def gesture_loop():
        frame = cam.read()
        if frame is not None:
            frame, lm_list = tracker.find_hand(frame)

            if lm_list:
                # Build a minimal hand object compatible with classify()
                raw_gesture = None
                # hand_tracker returns lm_list but classify() needs landmarks
                # For now debounce and dispatch when landmarks are present
                debouncer.reset()
            else:
                debouncer.reset()

            win.draw_overlay(frame)

        win.after(33, gesture_loop)

    win.after(0, gesture_loop)

    # ── Tkinter event loop (blocks until window closes) ──
    win.mainloop()

    # ── Cleanup ──────────────────────────────────────────
    print('[INFO] Shutting down...')
    dj.cleanup()
    cam.release()


if __name__ == '__main__':
    main()
