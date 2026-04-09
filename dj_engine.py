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

        self.volume      = config.DEFAULT_VOLUME
        self.is_playing  = False
        self.is_looping  = False
        self.is_loading  = False
        self.current_song = None
        self.status_msg  = ''

        self._lock = threading.Lock()

    # ── Internal helpers ─────────────────────────────────

    def _active_ch(self):
        return self._ch_a if self._active == 'a' else self._ch_b

    def _inactive_ch(self):
        return self._ch_b if self._active == 'a' else self._ch_a

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

    def load_and_play(self, song):
        """Load song in a background thread and start playing."""
        self.is_loading  = True
        self.current_song = song
        self.status_msg  = f'Loading: {song.display_title()}'
        t = threading.Thread(target=self._play_thread, args=(song,), daemon=True)
        t.start()

    def _play_thread(self, song):
        try:
            sound = self._load_sound(song.path)
        except Exception as e:
            self.status_msg = f'Load error: {e}'
            self.is_loading = False
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

    def crossfade_to(self, song):
        """Fade out current deck and fade in the new song on the other deck."""
        self.is_loading   = True
        self.current_song = song
        self.status_msg   = f'Crossfading: {song.display_title()}'
        t = threading.Thread(target=self._crossfade_thread, args=(song,), daemon=True)
        t.start()

    def _crossfade_thread(self, song):
        try:
            sound = self._load_sound(song.path)
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

    # ── Cleanup ──────────────────────────────────────────

    def cleanup(self):
        self._ch_a.stop()
        self._ch_b.stop()
        pygame.mixer.quit()
