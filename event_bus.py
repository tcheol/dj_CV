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
            "open_palm":     lambda: dj.toggle_play_pause() if dj  else None,
            "fist":          lambda: dj.stop()              if dj  else None,
            "thumb_up":      lambda: dj.volume_up()         if dj  else None,
            "thumb_down":    lambda: dj.volume_down()       if dj  else None,
            "peace":         lambda: dj.toggle_loop()       if dj  else None,
            "pinch":         lambda: dj.crossfade_to(
                                lib.songs[lib.queued_idx]
                             ) if dj and lib and lib.queued_idx >= 0 else None,
        }

    def dispatch(self, gesture: str, extra=None) -> None:
        """
        Fire the action mapped to a gesture name.

        Parameters
        ----------
        gesture : str
            One of the recognised gesture names from gesture_classifier.py.
        extra : any
            Optional payload — e.g. a card index for 'point_select'.
        """
        # point_select carries a card index as extra
        if gesture == 'point_select':
            if self._library and extra is not None:
                result = self._library.get_song_by_visible_idx(extra)
                if result:
                    song, abs_idx = result
                    self._library.queued_idx = abs_idx
                    if self._dj:
                        self._dj.load_track(song)
                        print(f"[EventBus] point_select → {song.title}")
            return

        action = self._actions.get(gesture)
        if action:
            print(f"[EventBus] {gesture}")
            action()
        else:
            print(f"[EventBus] Unrecognised gesture: '{gesture}'")
