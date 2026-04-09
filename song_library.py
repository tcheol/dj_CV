# ─────────────────────────────────────────────
#  song_library.py  –  Song data & persistence
# ─────────────────────────────────────────────
#
#  • Defines the Song dataclass (title, artist, duration, path)
#  • Loads / saves the song list to songs.json automatically
#  • Filters out missing files on startup
#  • Reads metadata via Mutagen (falls back to filename)
#  • Exposes a 5-card visible window for the gesture UI
# ─────────────────────────────────────────────

import os
import json
from dataclasses import dataclass, asdict
from typing import List, Optional

try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print('[WARN] mutagen not installed — metadata will fall back to filename.')
    print('       Run: pip install mutagen')


# ── Constants ─────────────────────────────────
LIBRARY_FILE   = "songs.json"   # persisted library path
VISIBLE_CARDS  = 5              # number of cards shown in the UI at once

# Supported audio extensions
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}


# ── Song dataclass ────────────────────────────

@dataclass
class Song:
    title:    str
    artist:   str
    duration: str   # formatted "M:SS"
    path:     str
    bpm:      str = "—"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Song":
        return Song(
            title    = d.get("title",    "Unknown"),
            artist   = d.get("artist",   "Unknown"),
            duration = d.get("duration", "—"),
            path     = d.get("path",     ""),
            bpm      = d.get("bpm",      "—"),
        )

    def as_panel_dict(self) -> dict:
        """Format expected by SongPanel / SongRow."""
        return {
            "title":    self.title,
            "artist":   self.artist,
            "duration": self.duration,
            "bpm":      self.bpm,
            "path":     self.path,
        }


# ── SongLibrary ───────────────────────────────

class SongLibrary:
    """
    Manages the full list of imported songs and the 5-card
    visible window used by the gesture UI.

    State
    ─────
    songs           – full list of Song objects
    now_playing_idx – index of the currently playing song (-1 = none)
    queued_idx      – index of the next song queued via gesture (-1 = none)
    scroll_offset   – index of the first song in the visible window
    visible_songs   – slice of songs[scroll_offset : scroll_offset + 5]
    """

    def __init__(self):
        self.songs:           List[Song] = []
        self.now_playing_idx: int        = -1
        self.queued_idx:      int        = -1
        self.scroll_offset:   int        = 0

        self._load()

    # ── Persistence ───────────────────────────

    def _load(self):
        """Load songs.json on startup; filter out missing files."""
        if not os.path.exists(LIBRARY_FILE):
            return

        try:
            with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARN] Could not load {LIBRARY_FILE}: {e}")
            return

        loaded = [Song.from_dict(d) for d in data]

        # Filter out files that no longer exist on disk
        before = len(loaded)
        self.songs = [s for s in loaded if os.path.isfile(s.path)]
        removed = before - len(self.songs)
        if removed:
            print(f"[INFO] Removed {removed} missing file(s) from library.")

        print(f"[INFO] Loaded {len(self.songs)} song(s) from {LIBRARY_FILE}.")
        self._clamp_scroll()

    def _save(self):
        """Persist the current song list to songs.json."""
        try:
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
                json.dump([s.to_dict() for s in self.songs], f, indent=2)
        except OSError as e:
            print(f"[ERROR] Could not save {LIBRARY_FILE}: {e}")

    # ── Adding songs ──────────────────────────

    def add_files(self, paths: List[str]) -> int:
        """
        Add songs from a list of file paths.
        Skips duplicates and unsupported formats.
        Returns the number of songs actually added.
        """
        existing_paths = {s.path for s in self.songs}
        added = 0

        for path in paths:
            path = os.path.abspath(path)
            ext  = os.path.splitext(path)[1].lower()

            if ext not in AUDIO_EXTENSIONS:
                print(f"[WARN] Skipping unsupported file: {path}")
                continue

            if path in existing_paths:
                print(f"[INFO] Already in library: {os.path.basename(path)}")
                continue

            if not os.path.isfile(path):
                print(f"[WARN] File not found: {path}")
                continue

            song = self._make_song(path)
            self.songs.append(song)
            existing_paths.add(path)
            added += 1
            print(f"[INFO] Added: {song.title} — {song.artist}")

        if added:
            self._save()
            self._clamp_scroll()

        return added

    def import_songs_dialog(self) -> int:
        """
        Opens a Tkinter file picker as a fallback import method.
        Returns the number of songs added.
        """
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            paths = filedialog.askopenfilenames(
                title="Select audio files",
                filetypes=[
                    ("Audio files", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a"),
                    ("All files",   "*.*"),
                ],
            )
            root.destroy()
        except Exception as e:
            print(f"[ERROR] Import dialog failed: {e}")
            return 0

        return self.add_files(list(paths))

    # ── Metadata extraction ───────────────────

    def _make_song(self, path: str) -> Song:
        """
        Build a Song from a file path.
        Uses Mutagen for metadata; falls back to the filename.
        """
        title    = os.path.splitext(os.path.basename(path))[0]
        artist   = "Unknown"
        duration = "—"

        if MUTAGEN_AVAILABLE:
            try:
                audio = MutagenFile(path, easy=True)
                if audio is not None:
                    title    = (audio.get("title",  [title])[0])
                    artist   = (audio.get("artist", ["Unknown"])[0])
                    secs     = int(audio.info.length) if hasattr(audio, "info") else 0
                    duration = f"{secs // 60}:{secs % 60:02d}"
            except Exception as e:
                print(f"[WARN] Could not read metadata for {os.path.basename(path)}: {e}")

        return Song(title=title, artist=artist, duration=duration, path=path)

    # ── Visible window ────────────────────────

    @property
    def visible_songs(self) -> List[Song]:
        """The 5 songs currently shown in the UI."""
        return self.songs[self.scroll_offset : self.scroll_offset + VISIBLE_CARDS]

    def get_song_by_visible_idx(self, i: int) -> Optional[tuple]:
        """
        Translate a card index (0–4) to (Song, absolute_index).
        Returns None if the index is out of range.
        """
        if not 0 <= i < len(self.visible_songs):
            return None
        abs_idx = self.scroll_offset + i
        return self.songs[abs_idx], abs_idx

    def scroll_up(self):
        """Move the visible window one song up."""
        if self.scroll_offset > 0:
            self.scroll_offset -= 1

    def scroll_down(self):
        """Move the visible window one song down."""
        max_offset = max(0, len(self.songs) - VISIBLE_CARDS)
        if self.scroll_offset < max_offset:
            self.scroll_offset += 1

    def _clamp_scroll(self):
        max_offset = max(0, len(self.songs) - VISIBLE_CARDS)
        self.scroll_offset = min(self.scroll_offset, max_offset)

    # ── Navigation ────────────────────────────

    def next_song_idx(self) -> int:
        """Return the index of the next song, wrapping around."""
        if not self.songs:
            return -1
        return (self.now_playing_idx + 1) % len(self.songs)

    def prev_song_idx(self) -> int:
        """Return the index of the previous song, wrapping around."""
        if not self.songs:
            return -1
        return (self.now_playing_idx - 1) % len(self.songs)

    # ── Public helpers ────────────────────────

    def all_tracks(self) -> List[dict]:
        """Return all songs as panel-ready dicts (used by SongPanel.refresh)."""
        return [s.as_panel_dict() for s in self.songs]

    def get_by_index(self, idx: int) -> Optional[Song]:
        if 0 <= idx < len(self.songs):
            return self.songs[idx]
        return None

    def __len__(self) -> int:
        return len(self.songs)
