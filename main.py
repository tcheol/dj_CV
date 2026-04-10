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
        camera_manager = cam,https://github.com/tcheol/dj_CV/blob/main/main.py
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


if __name__ == '__main__':
    main()
