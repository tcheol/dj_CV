class EventBus:
    def __init__(self, dj_engine=None, song_library=None, song_panel=None):
        self._dj         = dj_engine
        self._library    = song_library
        self._song_panel = song_panel   # needed to sync volume bar UI

        self._actions = self._build_action_map()

    def set_song_panel(self, panel):
        """Call this after the window is built to wire up the volume bar."""
        self._song_panel = panel

    def _build_action_map(self) -> dict:
        dj  = self._dj
        lib = self._library

        return {
            "open_palm":     lambda: dj.toggle_play_pause() if dj else None,
            "fist":          lambda: dj.stop()              if dj else None,
            "thumb_up":      self._volume_up,
            "thumb_down":    self._volume_down,
            "peace":         lambda: dj.toggle_loop()       if dj else None,
            "pinch":         lambda: dj.crossfade_to(
                                lib.songs[lib.queued_idx]
                             ) if dj and lib and lib.queued_idx >= 0 else None,
            "rock_on":         self._skip_to_next,
        }

    # ── Volume helpers (update bar UI after change) ───────

    def _volume_up(self):
        if self._dj:
            self._dj.volume_up()
            self._sync_volume_bar()

    def _volume_down(self):
        if self._dj:
            self._dj.volume_down()
            self._sync_volume_bar()

    def _sync_volume_bar(self):
        """Push the current dj volume level into the song panel bar."""
        if self._song_panel and self._dj:
            try:
                self._song_panel.update_volume(self._dj.volume)
            except Exception:
                pass

    # ── Dispatch ──────────────────────────────────────────

    def dispatch(self, gesture: str, extra=None) -> None:
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


    def _skip_to_next(self):
        lib = self._library
        dj  = self._dj

        if not lib or not lib.songs:
            return

        # Advance index, wrapping around to the start
        lib.queued_idx = (lib.queued_idx + 1) % len(lib.songs)
        next_song = lib.songs[lib.queued_idx]

        if dj:
            dj.load_track(next_song)
            if hasattr(dj, "play"):
                dj.play()
            else:
                dj.toggle_play_pause()

        print(f"[EventBus] point → skipped to {next_song.title}")

