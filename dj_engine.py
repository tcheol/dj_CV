"""
DJ audio engine.

Uses two pygame mixer channels (Deck A and Deck B) so two tracks can
play simultaneously for crossfading.

MP3 / FLAC / AAC require pydub + ffmpeg to convert to WAV in memory
before passing to pygame.mixer.Sound.  WAV and OGG are loaded directly.
"""

import io
import os
import threading
import time

import pygame

import config

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False


class DJEngine:

    def __init__(self):
        pygame.mixer.init(
            frequency=config.SAMPLE_RATE,   
            size=-16,
            channels=2,
            buffer=2048,
        )
        pygame.mixer.set_num_channels(8)

        self._ch_a = pygame.mixer.Channel(0)   # Deck A
        self._ch_b = pygame.mixer.Channel(1)   # Deck B
        self._active = 'a'                     # which deck is "on air"

        self._sound_a = None
        self._sound_b = None

        self.volume       = config.DEFAULT_VOLUME
        self.is_playing   = False
        self.is_looping   = False
        self.is_loading   = False
        self.current_song = None
        self.status_msg   = ''

        self._lock = threading.Lock()

    # ── Internal helpers ─────────────────────────────────

    def _active_ch(self):
        return self._ch_a if self._active == 'a' else self._ch_b

    def _inactive_ch(self):
        return self._ch_b if self._active == 'a' else self._ch_a

    def _get_title(self, song) -> str:
        """Safely get a display title from any song object or dict."""
        if hasattr(song, 'display_title'):
            return song.display_title()
        if hasattr(song, 'title'):
            return song.title
        if isinstance(song, dict):
            return song.get('title', 'Unknown')
        return str(song)

    def _get_path(self, song) -> str:
        """Safely get the file path from any song object or dict."""
        if hasattr(song, 'path'):
            return song.path
        if isinstance(song, dict):
            return song.get('path', '')
        return str(song)

    def _load_sound(self, path):
        """Convert any audio file to a pygame.mixer.Sound object."""
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.wav', '.ogg'):
            return pygame.mixer.Sound(path)
        if HAS_PYDUB:
            audio = AudioSegment.from_file(path)
            audio = (audio
                     .set_frame_rate(config.SAMPLE_RATE)
                     .set_channels(2)
                     .set_sample_width(2))
            buf = io.BytesIO()
            audio.export(buf, format='wav')
            buf.seek(0)
            return pygame.mixer.Sound(buf)
        raise RuntimeError(
            f'Cannot load {ext} file: install pydub + ffmpeg for MP3/FLAC support.'
        )

    # ── Playback ─────────────────────────────────────────

    def load_track(self, song):
        """
        Load a track and start playing it immediately.
        Accepts a Song object or a plain dict with 'path' and 'title' keys.
        This is the primary method called by app_window and song_panel.
        """
        self.load_and_play(song)

    def load_and_play(self, song):
        """Load song in a background thread and start playing."""
        self.is_loading   = True
        self.current_song = song
        self.status_msg   = f'Loading: {self._get_title(song)}'
        print(f'[DJ] Loading: {self._get_title(song)}')
        t = threading.Thread(target=self._play_thread, args=(song,), daemon=True)
        t.start()

    def _play_thread(self, song):
        path = self._get_path(song)
        try:
            sound = self._load_sound(path)
        except Exception as e:
            self.status_msg = f'Load error: {e}'
            self.is_loading = False
            print(f'[DJ] Error loading {path}: {e}')
            return

        with self._lock:
            self._active_ch().stop()
            loops = -1 if self.is_looping else 0
            self._active_ch().play(sound, loops=loops)
            self._active_ch().set_volume(self.volume)
            if self._active == 'a':
                self._sound_a = sound
            else:
                self._sound_b = sound
            self.is_playing = True
            self.is_loading = False
            self.status_msg = ''
            print(f'[DJ] Now playing: {self._get_title(song)}')

    def crossfade_to(self, song):
        """Fade out current deck and fade in the new song on the other deck."""
        self.is_loading   = True
        self.current_song = song
        self.status_msg   = f'Crossfading: {self._get_title(song)}'
        t = threading.Thread(target=self._crossfade_thread, args=(song,), daemon=True)
        t.start()

    def _crossfade_thread(self, song):
        path = self._get_path(song)
        try:
            sound = self._load_sound(path)
        except Exception as e:
            self.status_msg = f'Load error: {e}'
            self.is_loading = False
            return

        half_ms = config.CROSSFADE_MS // 2
        steps   = 20
        step_t  = (half_ms / 1000) / steps

        with self._lock:
            # Fade out current deck
            self._active_ch().fadeout(half_ms)

            # Switch to other deck
            self._active = 'b' if self._active == 'a' else 'a'
            if self._active == 'a':
                self._sound_a = sound
            else:
                self._sound_b = sound

            loops = -1 if self.is_looping else 0
            self._active_ch().set_volume(0)
            self._active_ch().play(sound, loops=loops)

        # Fade in the new deck (outside lock to avoid blocking)
        for i in range(1, steps + 1):
            self._active_ch().set_volume(self.volume * i / steps)
            time.sleep(step_t)

        with self._lock:
            self._active_ch().set_volume(self.volume)
            self.is_playing = True
            self.is_loading = False
            self.status_msg = ''

    def toggle_play_pause(self):
        with self._lock:
            if self.is_playing:
                self._active_ch().pause()
                self.is_playing = False
            else:
                self._active_ch().unpause()
                self.is_playing = True

    def stop(self):
        with self._lock:
            self._ch_a.stop()
            self._ch_b.stop()
            self.is_playing = False
            self.status_msg = ''

    # ── Volume ───────────────────────────────────────────

    def volume_up(self):
        self.volume = min(1.0, round(self.volume + 0.02, 2))
        self._apply_volume()

    def volume_down(self):
        self.volume = max(0.0, round(self.volume - 0.02, 2))
        self._apply_volume()

    def _apply_volume(self):
        with self._lock:
            self._active_ch().set_volume(self.volume)

    # ── Loop ─────────────────────────────────────────────

    def toggle_loop(self):
        self.is_looping = not self.is_looping
        # Restart with new loop setting if something is loaded
        if self.current_song and self.is_playing:
            self.load_and_play(self.current_song)

    # ── Seeking ──────────────────────────────────────────

    def seek(self, ratio: float):
        """
        Seek to a position in the current song.
        ratio: 0.0 = start, 1.0 = end
        Reloads and plays the song from the new offset using pydub.
        """
        if not self.current_song:
            return
        ratio = max(0.0, min(1.0, ratio))
        path  = self._get_path(self.current_song)

        import threading
        t = threading.Thread(
            target=self._seek_thread, args=(path, ratio), daemon=True)
        t.start()

    def _seek_thread(self, path: str, ratio: float):
        try:
            import io, os
            ext = os.path.splitext(path)[1].lower()

            if HAS_PYDUB:
                from pydub import AudioSegment
                audio    = AudioSegment.from_file(path)
                duration = len(audio)          # milliseconds
                start_ms = int(ratio * duration)
                sliced   = audio[start_ms:]
                sliced   = (sliced
                            .set_frame_rate(config.SAMPLE_RATE)
                            .set_channels(2)
                            .set_sample_width(2))
                buf = io.BytesIO()
                sliced.export(buf, format='wav')
                buf.seek(0)
                import pygame
                sound = pygame.mixer.Sound(buf)
            elif ext in ('.wav', '.ogg'):
                import pygame
                sound = pygame.mixer.Sound(path)
            else:
                print('[DJ] Seek needs pydub for MP3/FLAC. Install: pip install pydub')
                return

            with self._lock:
                self._active_ch().stop()
                loops = -1 if self.is_looping else 0
                self._active_ch().play(sound, loops=loops)
                self._active_ch().set_volume(self.volume)
                if self._active == 'a':
                    self._sound_a = sound
                else:
                    self._sound_b = sound
                self.is_playing   = True
                self.is_loading   = False
                self._seek_offset = ratio   # remember where we seeked to
                print(f'[DJ] Seeked to {int(ratio*100)}%')
        except Exception as e:
            print(f'[DJ] Seek error: {e}')

    def get_progress(self) -> float:
        """
        Return playback progress as 0.0–1.0.
        Accounts for any seek offset.
        """
        try:
            ch    = self._active_ch()
            sound = (self._sound_a if self._active == 'a' else self._sound_b)
            if sound and self.is_playing:
                total_ms = sound.get_length() * 1000
                pos_ms   = ch.get_pos()
                if total_ms > 0 and pos_ms >= 0:
                    offset   = getattr(self, '_seek_offset', 0.0)
                    progress = offset + (1.0 - offset) * (pos_ms / total_ms)
                    return min(1.0, progress)
        except Exception:
            pass
        return 0.0

    # ── Cleanup ──────────────────────────────────────────

    def cleanup(self):
        self._ch_a.stop()
        self._ch_b.stop()
        pygame.mixer.quit()
