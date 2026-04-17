"""
Gesture-Controlled DJ Controller
─────────────────────────────────
Run:  python main.py

Controls
  Q          quit
  I          open import dialog
  F / F11    toggle fullscreen
  Escape     exit fullscreen
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

    # Track hovered row for point gesture
    hovered_row   = -1

    def gesture_loop():
        nonlocal hovered_row

        frame = cam.read()
        if frame is not None:
            frame, lm_list, hand_landmarks = tracker.find_hand(frame)

            if hand_landmarks:
                raw_gesture = classify(hand_landmarks)

                # ── Point: live hover (no debounce) ──────────────────
                if raw_gesture == 'point':
                    hovered_row = win.get_pointed_row(lm_list)
                    # Draw a highlight ring on the fingertip
                    tip = next((lm for lm in lm_list if lm[0] == 8), None)
                    if tip:
                        import cv2
                        cv2.circle(frame, (tip[1], tip[2]), 14,
                                   (255, 255, 255), 2)
                else:
                    hovered_row = -1

                # ── Debounce all other gestures ───────────────────────
                fired = debouncer.update(raw_gesture)
                if fired:
                    if fired == 'point' and hovered_row >= 0:
                        bus.dispatch('point_select', hovered_row)
                    elif fired != 'point':
                        bus.dispatch(fired)
            else:
                hovered_row = -1
                debouncer.reset()

            win.draw_overlay(frame)

        win.after(33, gesture_loop)

    win.after(0, gesture_loop)
    win.mainloop()

    print('[INFO] Shutting down...')
    dj.cleanup()
    cam.release()


if __name__ == '__main__':
    main()
