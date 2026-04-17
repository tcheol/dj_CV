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
            "point":         self._delete_current_song,
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

    # ── Delete current song ───────────────────────────────

    def _delete_current_song(self):
        lib = self._library
        dj  = self._dj

        if not lib or lib.queued_idx < 0 or lib.queued_idx >= len(lib.songs):
            return

        old_idx      = lib.queued_idx
        removed_song = lib.songs.pop(old_idx)
        print(f"[EventBus] Deleted → {removed_song.title}")

        if len(lib.songs) == 0:
            lib.queued_idx = -1
            if dj:
                dj.stop()
            return

        lib.queued_idx = old_idx if old_idx < len(lib.songs) else len(lib.songs) - 1
        next_song = lib.songs[lib.queued_idx]

        if dj:
            dj.load_track(next_song)

        print(f"[EventBus] Now playing → {next_song.title}")
