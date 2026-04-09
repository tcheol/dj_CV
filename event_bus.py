class EventBus:
    def __init__(self, dj_engine=None, song_library=None):
        self._dj      = dj_engine
        self._library = song_library

        # Build the map once so dispatch() is just a dict lookup
        self._actions = self._build_action_map()

    def _build_action_map(self) -> dict:
        dj  = self._dj
        lib = self._library

        return {
            "open_palm":     lambda: dj.play_pause()        if dj  else None,
            "fist":          lambda: dj.stop()              if dj  else None,
            "thumb_up":      lambda: dj.volume_up()         if dj  else None,
            "thumb_down":    lambda: dj.volume_down()       if dj  else None,
            "point":         lambda: lib.select_hovered()   if lib else None,
            "peace":         lambda: dj.toggle_loop()       if dj  else None,
            "three_fingers": lambda: dj.next_track()        if dj  else None,
            "pinky":         lambda: dj.previous_track()    if dj  else None,
            "pinch":         lambda: dj.crossfade()         if dj  else None,
        }
    
def dispatch(self, gesture: str) -> None:
        action = self._actions.get(gesture)
        if action:
            print(f"[EventBus] {gesture}")
            action()
        else:
            print(f"[EventBus] Unrecognised gesture: '{gesture}'")