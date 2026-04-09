"""
dj_audio.py

Two-deck audio engine for the gesture-controlled DJ controller.

Architecture

  Deck A  →  pygame.mixer channel 0
  Deck B  →  pygame.mixer channel 1

  Each deck holds one loaded track.  Both can play simultaneously,
  which is what enables real-time crossfading.

Format support

  WAV / OGG   – loaded directly into pygame.mixer.Sound (zero-copy path).
  MP3 / FLAC / AAC / M4A / anything else
              – decoded by pydub → exported to an in-memory WAV BytesIO
                → passed to pygame.mixer.Sound.  Requires ffmpeg on PATH.

Public API

  engine = DJEngine()

  engine.load(deck, path)         
  engine.play(deck)
  engine.pause(deck)
  engine.stop(deck)
  engine.toggle_loop(deck)          # returns new bool state
  engine.set_crossfade(position)    # 0.0 = full A, 1.0 = full B
  engine.set_master_volume(vol)     # 0.0 – 1.0
  engine.get_state(deck)            # DeckState dataclass

  engine.shutdown()                 # call on exit
"""

from __future__ import annotations

import io
import os
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import pygame

# pydub is optional – only needed for lossy/compressed formats
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


# Constants

SAMPLE_RATE = 44_100
CHANNELS = 2          # stereo
BUFFER_SIZE = 2_048      # samples; lower = less latency, higher = more stable
SAMPLE_BITS = -16        # signed 16-bit (pygame convention)

DECK_A_CH = 0
DECK_B_CH = 1

# Formats handled directly by pygame / SDL_mixer (no pydub needed)
NATIVE_FORMATS = {'.wav', '.ogg'}

# Enums / dataclasses

class PlayState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED  = auto()


@dataclass
class DeckState:
    """Snapshot of a deck's status – safe to read from any thread."""
    deck:str
    track_name:Optional[str]        # filename (stem) or None
    play_state:PlayState = PlayState.STOPPED
    loop:bool = False
    volume:float = 1.0   # 0.0 – 1.0 (pre-crossfade)
    position_s:float = 0.0   # playback position in seconds (best-effort)


# Internal deck object

class _Deck:
    """
    Manages one pygame mixer channel + its loaded Sound object.
    Not thread-safe on its own; DJEngine's lock guards all access.
    """

    def __init__(self, name: str, channel_id: int) -> None:
        self.name = name                              
        self.channel = pygame.mixer.Channel(channel_id)
        self.sound:Optional[pygame.mixer.Sound] = None
        self.track_path: Optional[Path]  = None
        self.play_state: PlayState = PlayState.STOPPED
        self.loop:bool = False
        self._volume:float = 1.0  # pre-crossfade

    # Volume (applied to the channel directly)

    def apply_volume(self, crossfade_vol: float) -> None:
        """Set the channel volume = deck volume × crossfade contribution."""
        self.channel.set_volume(self._volume * crossfade_vol)

    # Transport

    def play(self) -> None:
        if self.sound is None:
            return
        loops = -1 if self.loop else 0
        self.channel.play(self.sound, loops=loops)
        self.play_state = PlayState.PLAYING

    def pause(self) -> None:
        if self.play_state == PlayState.PLAYING:
            self.channel.pause()
            self.play_state = PlayState.PAUSED

    def unpause(self) -> None:
        if self.play_state == PlayState.PAUSED:
            self.channel.unpause()
            self.play_state = PlayState.PLAYING

    def stop(self) -> None:
        self.channel.stop()
        self.play_state = PlayState.STOPPED

    def toggle_loop(self) -> bool:
        self.loop = not self.loop
        # If currently playing, restart with new loop setting
        if self.play_state == PlayState.PLAYING:
            self.play()
        return self.loop

    # State snapshot

    def state(self) -> DeckState:
        return DeckState(
            deck = self.name,
            track_name = self.track_path.stem if self.track_path else None,
            play_state = self.play_state,
            loop = self.loop,
            volume = self._volume,
        )


# Audio loading helpers

def _load_sound(path: Path) -> pygame.mixer.Sound:
    """
    Load an audio file and return a pygame.mixer.Sound.

    Native formats (WAV, OGG) are passed straight to pygame.
    Everything else is decoded via pydub and converted to an
    in-memory WAV before loading.
    """
    suffix = path.suffix.lower()

    if suffix in NATIVE_FORMATS:
        return pygame.mixer.Sound(str(path))

    # pydub
    if not PYDUB_AVAILABLE:
        raise RuntimeError(
            f"Cannot load '{path.name}': pydub is not installed. "
            "Install it with:  pip install pydub\n"
            "You also need ffmpeg on your PATH for MP3/FLAC/AAC support."
        )

    # pydub uses ffmpeg under the hood for MP3, FLAC, AAC, M4A, etc.
    fmt = suffix.lstrip('.')          # e.g.  'mp3', 'flac', 'aac'
    if fmt == 'm4a':
        fmt = 'mp4'                   # ffmpeg expects 'mp4' for .m4a containers

    audio = AudioSegment.from_file(str(path), format=fmt)

    # Normalise to the mixer's sample rate / channels to avoid SDL resampling
    audio = audio.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS).set_sample_width(2)

    buf = io.BytesIO()
    audio.export(buf, format='wav')
    buf.seek(0)
    return pygame.mixer.Sound(buf)


# Public engine

class DJEngine:
    """
    Two-deck audio engine.  All public methods are thread-safe.

    Parameters
    ----------
    master_volume : float
        Initial master volume (0.0 – 1.0).
    """

    def __init__(self, master_volume: float = 0.9) -> None:
        self._init_mixer()
        self._lock = threading.Lock()
        self._crossfade_pos = 0.5          # 0.0 = full A, 1.0 = full B
        self._master_vol = master_volume
        self._deck_a = _Deck('a', DECK_A_CH)
        self._deck_b = _Deck('b', DECK_B_CH)
        self._apply_crossfade()

    # Setup / teardown

    @staticmethod
    def _init_mixer() -> None:
        """Initialise pygame and the mixer (idempotent)."""
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(SAMPLE_RATE, SAMPLE_BITS, CHANNELS, BUFFER_SIZE)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(2)
            print(f'[DJEngine] Mixer init: {pygame.mixer.get_init()}')

    def shutdown(self) -> None:
        """Stop all playback and quit the mixer.  Call on app exit."""
        with self._lock:
            self._deck_a.stop()
            self._deck_b.stop()
        pygame.mixer.quit()
        print('[DJEngine] Mixer shut down.')

    # Loading

    def load(self, deck: str, path: str | os.PathLike) -> None:
        """
        Load an audio file onto a deck.  Blocks until decoding is complete
        (for MP3/FLAC this may take a moment; consider calling from a thread).

        Parameters
        ----------
        deck : 'a' or 'b'
        path : path to audio file (WAV / OGG / MP3 / FLAC / AAC / M4A)
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Audio file not found: {p}")

        sound = _load_sound(p)            # may raise RuntimeError for bad format

        with self._lock:
            d = self._get_deck(deck)
            d.stop()
            d.sound = sound
            d.track_path = p
            d.play_state = PlayState.STOPPED
            print(f'[DJEngine] Deck {deck.upper()} loaded: {p.name}')

    # Transport

    def play(self, deck: str) -> None:
        """Play (or unpause) the specified deck."""
        with self._lock:
            d = self._get_deck(deck)
            if d.sound is None:
                print(f'[DJEngine] Deck {deck.upper()}: nothing loaded.')
                return
            if d.play_state == PlayState.PAUSED:
                d.unpause()
            else:
                d.play()
        print(f'[DJEngine] Deck {deck.upper()} playing.')

    def pause(self, deck: str) -> None:
        """Pause the specified deck (resume with play())."""
        with self._lock:
            self._get_deck(deck).pause()
        print(f'[DJEngine] Deck {deck.upper()} paused.')

    def stop(self, deck: str) -> None:
        """Stop the specified deck and reset to start."""
        with self._lock:
            self._get_deck(deck).stop()
        print(f'[DJEngine] Deck {deck.upper()} stopped.')

    def toggle_loop(self, deck: str) -> bool:
        """
        Toggle looping on a deck.

        Returns
        -------
        bool
            New loop state (True = looping).
        """
        with self._lock:
            state = self._get_deck(deck).toggle_loop()
        print(f'[DJEngine] Deck {deck.upper()} loop → {state}')
        return state

    # Volume / crossfade

    def set_crossfade(self, position: float) -> None:
        """
        Set the crossfader position.

        Parameters
        ----------
        position : float
            0.0 = Deck A at full volume, Deck B silent.
            0.5 = both decks at equal volume.
            1.0 = Deck B at full volume, Deck A silent.
        """
        position = max(0.0, min(1.0, position))
        with self._lock:
            self._crossfade_pos = position
            self._apply_crossfade()

    def set_master_volume(self, vol: float) -> None:
        """Set master volume (0.0 – 1.0).  Reapplies crossfade."""
        vol = max(0.0, min(1.0, vol))
        with self._lock:
            self._master_vol = vol
            self._apply_crossfade()

    def get_crossfade(self) -> float:
        """Return current crossfader position (0.0 – 1.0)."""
        with self._lock:
            return self._crossfade_pos

    # State queries

    def get_state(self, deck: str) -> DeckState:
        """Return a DeckState snapshot for the given deck ('a' or 'b')."""
        with self._lock:
            return self._get_deck(deck).state()

    def is_playing(self, deck: str) -> bool:
        with self._lock:
            return self._get_deck(deck).play_state == PlayState.PLAYING

    # Internal helpers

    def _get_deck(self, deck: str) -> _Deck:
        key = deck.lower()
        if key == 'a':
            return self._deck_a
        if key == 'b':
            return self._deck_b
        raise ValueError(f"Unknown deck '{deck}'. Use 'a' or 'b'.")

    def _apply_crossfade(self) -> None:
        """
        Compute per-deck volumes from the crossfade position and master volume,
        then push them to the pygame channels.

        Crossfade curve: linear equal-power approximation.
          Deck A volume = (1 - position) * master
          Deck B volume = position * master

        This gives a smooth, DJ-style crossfade without abrupt cuts.
        """
        pos = self._crossfade_pos
        vol_a = (1.0 - pos) * self._master_vol
        vol_b = pos * self._master_vol

        self._deck_a._volume = vol_a
        self._deck_b._volume = vol_b

        # apply_volume passes 1.0 as the crossfade multiplier since we've
        # already baked the crossfade into _volume above.
        self._deck_a.apply_volume(1.0)
        self._deck_b.apply_volume(1.0)


# Quick smoke test

# if __name__ == '__main__':
#     import time

#     engine = DJEngine()
#     print('DJEngine created.')
#     print('Deck A state:', engine.get_state('a'))
#     print('Deck B state:', engine.get_state('b'))

#     # Crossfade sweep test (no audio file needed)
#     print('\nCrossfade sweep test:')
#     for pos in [0.0, 0.25, 0.5, 0.75, 1.0]:
#         engine.set_crossfade(pos)
#         ch_a = pygame.mixer.Channel(DECK_A_CH).get_volume()
#         ch_b = pygame.mixer.Channel(DECK_B_CH).get_volume()
#         print(f'  pos={pos:.2f}  →  ch_A={ch_a:.3f}  ch_B={ch_b:.3f}')

#     engine.shutdown()
#     print('\nSmoke test passed.')
