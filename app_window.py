# ─────────────────────────────────────────────
#  app_window.py  –  Main application window
# ─────────────────────────────────────────────

import tkinter as tk
from tkinter import font as tkfont
import cv2
import numpy as np
import random
import math
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os

from song_panel    import SongPanel
from import_dialog import ImportDialog
from config        import WINDOW_NAME, CAMERA_WIDTH, CAMERA_HEIGHT


# ── Palette ───────────────────────────────────
BG      = "#0E0E0E"
SURFACE = "#1A1A1A"
BORDER  = "#2A2A2A"
ACCENT  = "#E8E8E8"
MUTED   = "#666666"
ACTIVE  = "#FFFFFF"

# ── Overlay colours (BGR for OpenCV) ──────────
OVERLAY_BG     = (18,  18,  18)
OVERLAY_ALPHA  = 0.82
OVERLAY_BORDER = (42,  42,  42)
TEXT_PRIMARY   = (232, 232, 232)
TEXT_MUTED     = (102, 102, 102)
TEXT_ACTIVE    = (255, 255, 255)
ACCENT_BAR     = (255, 255, 255)
SEL_BG         = (44,  44,  44)

# ── Waveform colours ──────────────────────────
WAVE_BAR_IDLE   = (60,  60,  60)
WAVE_BAR_PLAYED = (220, 220, 220)
WAVE_BAR_HEAD   = (255, 255, 255)


class AppWindow(tk.Tk):
    FEED_W  = 854
    FEED_H  = 480
    PANEL_W = 340

    def __init__(self, camera_manager=None, dj_engine=None, song_library=None):
        super().__init__()

        self._cam        = camera_manager
        self._dj         = dj_engine
        self._library    = song_library
        self._after_id   = None
        self._fullscreen = False

        # Waveform bars — generated once per song load
        self._wave_bars   = []
        self._wave_song   = None   # track which song the bars belong to
        self._wave_bars_n = 120    # number of bars in the waveform

        self._configure_window()
        self._load_fonts()
        self._build_ui()

    # ── Window setup ──────────────────────────

    def _configure_window(self):
        self.title(WINDOW_NAME)
        self.configure(bg=BG)
        self.resizable(True, True)

        total_w = self.FEED_W + self.PANEL_W + 3
        total_h = self.FEED_H + 48
        self.geometry(f"{total_w}x{total_h}")

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - total_w) // 2
        y  = (sh - total_h) // 2
        self.geometry(f"{total_w}x{total_h}+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<KeyPress-q>", lambda _: self._on_close())
        self.bind("<KeyPress-i>", lambda _: self._open_import())
        self.bind("<KeyPress-f>", lambda _: self._toggle_fullscreen())
        self.bind("<F11>",        lambda _: self._toggle_fullscreen())
        self.bind("<Escape>",     lambda _: self._exit_fullscreen())

    def _load_fonts(self):
        self._font_title = tkfont.Font(family="TkDefaultFont", size=13, weight="bold")
        self._font_label = tkfont.Font(family="TkDefaultFont", size=11)
        self._font_hint  = tkfont.Font(family="TkDefaultFont", size=10)

    # ── UI construction ───────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_body()

    def _build_header(self):
        # Slim header — title only, no shortcut pills
        hdr = tk.Frame(self, bg=SURFACE, height=36)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text=WINDOW_NAME.upper(),
            bg=SURFACE, fg=ACTIVE,
            font=self._font_title, padx=20,
        ).pack(side="left", fill="y")

        tk.Frame(hdr, bg=BORDER, height=1).place(
            relx=0, rely=1.0, relwidth=1, anchor="sw"
        )

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(
            body, width=self.FEED_W, height=self.FEED_H,
            bg=SURFACE, highlightthickness=0,
        )
        self._canvas.pack(side="left", fill="both", expand=True)

        self._canvas.create_text(
            self.FEED_W // 2, self.FEED_H // 2,
            text="Waiting for camera…",
            fill=MUTED, font=self._font_label,
            tags="placeholder",
        )

        self._divider = tk.Frame(body, bg=BORDER, width=1)
        self._divider.pack(side="left", fill="y")

        self._song_panel = SongPanel(
            body,
            width=self.PANEL_W,
            on_import=self._open_import,
            dj_engine=self._dj,
            song_library=self._library,
        )
        self._song_panel.pack(side="left", fill="both")

    # ── Fullscreen ────────────────────────────

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self.attributes("-fullscreen", self._fullscreen)

        if self._fullscreen:
            self._divider.pack_forget()
            self._song_panel.pack_forget()
        else:
            self._divider.pack(side="left", fill="y")
            self._song_panel.pack(side="left", fill="both")

    def _exit_fullscreen(self):
        if self._fullscreen:
            self._fullscreen = False
            self.attributes("-fullscreen", False)
            self._divider.pack(side="left", fill="y")
            self._song_panel.pack(side="left", fill="both")

    # ── Frame drawing ─────────────────────────

    def start_feed(self):
        self._update_frame()

    def _update_frame(self):
        if self._cam is not None:
            frame = self._cam.read()
            if frame is not None:
                self._draw_frame(frame)
        self._after_id = self.after(33, self._update_frame)

    def draw_overlay(self, bgr_frame):
        self._draw_frame(bgr_frame)

    def _draw_frame(self, bgr_frame):
        self._canvas.delete("placeholder")

        cw = self._canvas.winfo_width()  or self.FEED_W
        ch = self._canvas.winfo_height() or self.FEED_H

        frame = cv2.resize(bgr_frame, (cw, ch), interpolation=cv2.INTER_LINEAR)

        # Always draw the waveform progress bar at the bottom
        frame = self._draw_waveform(frame, cw, ch)

        # In fullscreen, draw the panel overlay on top
        if self._fullscreen and self._library is not None:
            frame = self._draw_panel_overlay(frame, cw, ch)

        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self._canvas.create_image(0, 0, anchor="nw", image=photo)
        self._canvas._photo = photo

    # ── Waveform progress bar ─────────────────

    def _get_wave_bars(self, song_key: str, n: int) -> list:
        """Return (or generate) normalised bar heights [0..1] for a song."""
        if self._wave_song != song_key or len(self._wave_bars) != n:
            random.seed(hash(song_key) & 0xFFFFFF)
            raw = []
            phase = 0.0
            for i in range(n):
                phase += random.uniform(0.05, 0.25)
                h = (math.sin(phase) * 0.4 + 0.5 +
                     random.uniform(-0.15, 0.15))
                raw.append(max(0.05, min(1.0, h)))
            self._wave_bars  = raw
            self._wave_song  = song_key
            random.seed()   # restore randomness
        return self._wave_bars

    def _draw_waveform(self, frame, fw, fh):
        """Draw a song-waveform style progress bar at the bottom of the frame."""
        bar_zone_h = 56       # total height of the waveform zone
        bar_max_h  = 36       # tallest a bar can be
        bar_w      = 3        # width of each bar in px
        bar_gap    = 2        # gap between bars
        py         = fh - bar_zone_h  # top of the waveform zone

        # Dark background strip
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, py), (fw, fh), (10, 10, 10), -1)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

        # Top border line
        cv2.line(frame, (0, py), (fw, py), OVERLAY_BORDER, 1)

        # Figure out playback progress
        progress = 0.0
        song_key = "none"

        if self._dj and hasattr(self._dj, 'current_song') and self._dj.current_song:
            song = self._dj.current_song
            song_key = (song.path if hasattr(song, 'path')
                        else song.get('path', 'none'))

            # Try to get progress from pygame mixer
            try:
                import pygame
                ch = self._dj._active_ch()
                sound = (self._dj._sound_a
                         if self._dj._active == 'a'
                         else self._dj._sound_b)
                if sound and self._dj.is_playing:
                    total_ms = sound.get_length() * 1000
                    pos_ms   = ch.get_pos()       # ms since play() was called
                    if total_ms > 0 and pos_ms >= 0:
                        progress = min(1.0, pos_ms / total_ms)
            except Exception:
                pass

        # How many bars fit in the canvas width?
        n_bars = max(10, fw // (bar_w + bar_gap))
        bars   = self._get_wave_bars(song_key, n_bars)

        head_i = int(progress * (n_bars - 1))
        cx_bar = (fw - n_bars * (bar_w + bar_gap)) // 2   # center horizontally

        for i, norm_h in enumerate(bars):
            bh   = max(2, int(norm_h * bar_max_h))
            bx   = cx_bar + i * (bar_w + bar_gap)
            by   = py + (bar_zone_h - bh) // 2

            if i < head_i:
                colour = WAVE_BAR_PLAYED
            elif i == head_i:
                colour = WAVE_BAR_HEAD
            else:
                colour = WAVE_BAR_IDLE

            cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bh), colour, -1)

        # Song title + time overlay (left of waveform)
        if self._dj and hasattr(self._dj, 'current_song') and self._dj.current_song:
            song  = self._dj.current_song
            title = (song.title if hasattr(song, 'title')
                     else song.get('title', ''))
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            font_sm = self._load_font(10)
            font_md = self._load_font(12)
            self._put_text(img_pil, "NOW PLAYING", (14, py + 6),
                           TEXT_MUTED, font_sm)
            self._put_text(img_pil, title[:40], (14, py + 20),
                           TEXT_ACTIVE, font_md)
            frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        return frame

    # ── Fullscreen panel overlay ──────────────

    def _draw_panel_overlay(self, frame, fw, fh):
        """
        In fullscreen: draw the same panel that appears in normal mode —
        track list with numbers, volume bar — as a semi-transparent overlay
        on the right side of the frame.
        """
        pw  = self.PANEL_W + 40
        px  = fw - pw
        # Leave room for the waveform at the bottom
        wave_h    = 56
        panel_h   = fh - wave_h

        # ── Background blend ──────────────────
        overlay = frame.copy()
        cv2.rectangle(overlay, (px, 0), (fw, panel_h), OVERLAY_BG, -1)
        cv2.line(overlay, (px, 0), (px, panel_h), OVERLAY_BORDER, 1)
        frame = cv2.addWeighted(overlay, OVERLAY_ALPHA, frame, 1 - OVERLAY_ALPHA, 0)

        # ── Header ────────────────────────────
        header_h = 36
        cv2.rectangle(frame, (px, 0), (fw, header_h), (26, 26, 26), -1)
        cv2.line(frame, (px, header_h), (fw, header_h), OVERLAY_BORDER, 1)

        img_pil    = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        font_title = self._load_font(13)
        font_det   = self._load_font(11)
        font_sm    = self._load_font(10)
        font_num   = self._load_font(10)

        self._put_text(img_pil, "TRACKS", (px + 16, 10), TEXT_MUTED, font_sm)
        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        # ── Volume bar (vertical, right edge) ─
        vol_bar_w  = 18
        vol_bar_h  = panel_h - header_h - 16
        vol_bar_x  = fw - vol_bar_w - 6
        vol_bar_y  = header_h + 8

        # Track background
        cv2.rectangle(frame,
                      (vol_bar_x, vol_bar_y),
                      (vol_bar_x + vol_bar_w, vol_bar_y + vol_bar_h),
                      (40, 40, 40), -1)

        # Fill (from bottom up)
        vol = self._dj.volume if (self._dj and hasattr(self._dj, 'volume')) else 0.8
        fill_h = int(vol * vol_bar_h)
        cv2.rectangle(frame,
                      (vol_bar_x, vol_bar_y + vol_bar_h - fill_h),
                      (vol_bar_x + vol_bar_w, vol_bar_y + vol_bar_h),
                      (220, 220, 220), -1)

        # Percentage label
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        self._put_text(img_pil, f"{int(vol*100)}%",
                       (vol_bar_x - 2, vol_bar_y + vol_bar_h + 4),
                       TEXT_MUTED, font_sm)
        self._put_text(img_pil, "VOL",
                       (vol_bar_x, vol_bar_y - 14),
                       TEXT_MUTED, font_sm)
        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        # ── Track rows ────────────────────────
        tracks   = self._library.all_tracks()
        row_h    = 56
        track_pw = pw - vol_bar_w - 14   # available width minus vol bar

        for i, track in enumerate(tracks[:8]):
            row_y = header_h + i * row_h
            if row_y + row_h > panel_h:
                break

            is_selected = (
                hasattr(self._song_panel, '_selected_idx') and
                self._song_panel._selected_idx == i
            )

            row_bg = SEL_BG if is_selected else (
                (28, 28, 28) if i % 2 == 0 else (22, 22, 22)
            )
            cv2.rectangle(frame, (px, row_y),
                          (px + track_pw, row_y + row_h), row_bg, -1)

            if is_selected:
                cv2.rectangle(frame, (px, row_y),
                              (px + 3, row_y + row_h), ACCENT_BAR, -1)

            cv2.line(frame, (px, row_y + row_h),
                     (px + track_pw, row_y + row_h), OVERLAY_BORDER, 1)

            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            # Row number
            self._put_text(img_pil, str(i + 1),
                           (px + 8, row_y + 8), TEXT_MUTED, font_num)

            title  = track.get("title",    "Unknown")
            artist = track.get("artist",   "—")
            dur    = track.get("duration", "—")
            bpm    = track.get("bpm",      "—")

            tc = TEXT_ACTIVE if is_selected else TEXT_PRIMARY
            self._put_text(img_pil, title,
                           (px + 28, row_y + 8),  tc,        font_title)
            self._put_text(img_pil,
                           f"{artist}  ·  {bpm} BPM  ·  {dur}",
                           (px + 28, row_y + 28), TEXT_MUTED, font_det)

            frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        return frame

    # ── Unicode font loader ───────────────────

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            "C:/Windows/Fonts/arialuni.ttf",
            "C:/Windows/Fonts/Arial.ttf",
            "C:/Windows/Fonts/msgothic.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _put_text(self, img_pil, text, xy, color, font):
        draw = ImageDraw.Draw(img_pil)
        rgb  = (color[2], color[1], color[0])
        draw.text(xy, text, font=font, fill=rgb)

    # ── Import dialog ─────────────────────────

    def _open_import(self):
        ImportDialog(self, on_confirm=self._on_songs_imported)

    def _on_songs_imported(self, paths):
        if paths and self._library is not None:
            added = self._library.add_files(paths)
            if added:
                self._song_panel.refresh()
                first_song = self._library.songs[-added]
                if self._dj is not None:
                    self._dj.load_and_play(first_song)
                    print(f'[INFO] Now playing: {first_song.title}')
                else:
                    print('[WARN] No DJ engine attached.')
        elif paths and self._library is None:
            print('[WARN] No song library attached.')

    def stop(self):
        if self._dj is not None:
            self._dj.stop()

    # ── Lifecycle ─────────────────────────────

    def _on_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self.destroy()
