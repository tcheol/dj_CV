# ─────────────────────────────────────────────
#  app_window.py  –  Main application window
# ─────────────────────────────────────────────

import tkinter as tk
from tkinter import font as tkfont
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import sys

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

# ── Overlay panel colours (BGRA for OpenCV) ───
OVERLAY_BG     = (18,  18,  18)   # #121212 panel background
OVERLAY_ALPHA  = 0.82             # 0 = fully transparent, 1 = fully opaque
OVERLAY_BORDER = (42,  42,  42)   # #2A2A2A divider line
TEXT_PRIMARY   = (232, 232, 232)  # #E8E8E8
TEXT_MUTED     = (102, 102, 102)  # #666666
TEXT_ACTIVE    = (255, 255, 255)
ACCENT_BAR     = (255, 255, 255)  # selected track left bar
SEL_BG         = (44,  44,  44)   # selected track background


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
        self.bind("<Configure>",  self._on_resize)

    def _load_fonts(self):
        self._font_title = tkfont.Font(family="Helvetica Neue", size=13, weight="bold")
        self._font_label = tkfont.Font(family="Helvetica Neue", size=11)
        self._font_hint  = tkfont.Font(family="Helvetica Neue", size=10)

    # ── UI construction ───────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_body()

    def _build_header(self):
        hdr = tk.Frame(self, bg=SURFACE, height=48)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text=WINDOW_NAME.upper(),
            bg=SURFACE, fg=ACTIVE,
            font=self._font_title, padx=20,
        ).pack(side="left", fill="y")

        hints = [("Q", "quit"), ("I", "import"), ("F", "fullscreen")]
        for key, label in hints:
            pill = tk.Frame(hdr, bg=BORDER, padx=8)
            pill.pack(side="right", padx=(0, 8), fill="y", pady=12)
            tk.Label(pill, text=key,         bg=BORDER, fg=ACTIVE, font=self._font_hint).pack(side="left")
            tk.Label(pill, text=f" {label}", bg=BORDER, fg=MUTED,  font=self._font_hint).pack(side="left")

        tk.Frame(hdr, bg=BORDER, height=1).place(relx=0, rely=1.0, relwidth=1, anchor="sw")

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # ── Camera canvas (fills everything in fullscreen) ──
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

        # ── Divider (hidden in fullscreen) ───
        self._divider = tk.Frame(body, bg=BORDER, width=1)
        self._divider.pack(side="left", fill="y")

        # ── Song panel (hidden in fullscreen) ─
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
            # Hide the Tkinter panel — we'll draw it on the frame instead
            self._divider.pack_forget()
            self._song_panel.pack_forget()
        else:
            # Restore normal layout
            self._divider.pack(side="left", fill="y")
            self._song_panel.pack(side="left", fill="both")

    def _exit_fullscreen(self):
        if self._fullscreen:
            self._fullscreen = False
            self.attributes("-fullscreen", False)
            self._divider.pack(side="left", fill="y")
            self._song_panel.pack(side="left", fill="both")

    def _on_resize(self, event=None):
        if event and event.widget is not self:
            return

    # ── Camera feed ───────────────────────────

    def start_feed(self):
        self._update_frame()

    def _update_frame(self):
        if self._cam is not None:
            frame = self._cam.read()
            if frame is not None:
                self._draw_frame(frame)
        self._after_id = self.after(33, self._update_frame)

    def _draw_frame(self, bgr_frame):
        self._canvas.delete("placeholder")

        cw = self._canvas.winfo_width()  or self.FEED_W
        ch = self._canvas.winfo_height() or self.FEED_H

        frame = cv2.resize(bgr_frame, (cw, ch), interpolation=cv2.INTER_LINEAR)

        # In fullscreen, draw the transparent panel overlay onto the frame
        if self._fullscreen and self._library is not None:
            frame = self._draw_panel_overlay(frame, cw, ch)

        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self._canvas.create_image(0, 0, anchor="nw", image=photo)
        self._canvas._photo = photo

    # ── Unicode font loader ───────────────────

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        """
        Load the best available font that supports Unicode / CJK characters.
        Falls back gracefully if no TrueType font is found.
        """
        candidates = [
            # Windows
            "C:/Windows/Fonts/arialuni.ttf",
            "C:/Windows/Fonts/Arial.ttf",
            "C:/Windows/Fonts/msgothic.ttc",
            # macOS
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            # Linux — Noto covers Korean, Japanese, Chinese, Arabic, etc.
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

    # ── PIL text helper ───────────────────────

    def _put_text(self, img_pil: Image.Image, text: str, xy: tuple,
                  color: tuple, font: ImageFont.FreeTypeFont):
        """Draw Unicode text onto a PIL image in-place."""
        draw = ImageDraw.Draw(img_pil)
        # color is BGR tuple — convert to RGB for PIL
        rgb = (color[2], color[1], color[0])
        draw.text(xy, text, font=font, fill=rgb)

    # ── Transparent overlay panel ─────────────

    def _draw_panel_overlay(self, frame, fw, fh):
        """Draw a semi-transparent song panel on the right of the frame."""
        pw = self.PANEL_W + 40
        px = fw - pw

        # ── Background blend ──────────────────
        overlay = frame.copy()
        cv2.rectangle(overlay, (px, 0), (fw, fh), OVERLAY_BG, -1)
        cv2.line(overlay, (px, 0), (px, fh), OVERLAY_BORDER, 1)
        frame = cv2.addWeighted(overlay, OVERLAY_ALPHA, frame, 1 - OVERLAY_ALPHA, 0)

        # ── Header background ─────────────────
        header_h = 48
        cv2.rectangle(frame, (px, 0), (fw, header_h), (26, 26, 26), -1)
        cv2.line(frame, (px, header_h), (fw, header_h), OVERLAY_BORDER, 1)

        # Convert frame to PIL for Unicode text rendering
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        font_title  = self._load_font(13)
        font_detail = self._load_font(11)
        font_small  = self._load_font(10)

        # Header label
        self._put_text(img_pil, "TRACKS", (px + 16, 16), TEXT_MUTED, font_small)

        # ── Track rows ────────────────────────
        tracks = self._library.all_tracks()
        row_h  = 56

        # Convert back to BGR to draw rectangles, then back to PIL for text
        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        for i, track in enumerate(tracks[:8]):
            row_y = header_h + i * row_h
            if row_y + row_h > fh:
                break

            is_selected = (
                hasattr(self._song_panel, '_selected_idx') and
                self._song_panel._selected_idx == i
            )

            row_bg = SEL_BG if is_selected else (
                (28, 28, 28) if i % 2 == 0 else (22, 22, 22)
            )
            cv2.rectangle(frame, (px, row_y), (fw, row_y + row_h), row_bg, -1)

            if is_selected:
                cv2.rectangle(frame, (px, row_y), (px + 3, row_y + row_h), ACCENT_BAR, -1)

            cv2.line(frame, (px, row_y + row_h), (fw, row_y + row_h), OVERLAY_BORDER, 1)

            # Convert to PIL to draw Unicode text
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            title  = track.get("title",  "Unknown")
            artist = track.get("artist", "—")
            dur    = track.get("duration", "—")
            bpm    = track.get("bpm", "—")

            title_color  = TEXT_ACTIVE if is_selected else TEXT_PRIMARY
            self._put_text(img_pil, title,  (px + 14, row_y + 8),  title_color,  font_title)

            detail = f"{artist}  ·  {bpm} BPM  ·  {dur}"
            self._put_text(img_pil, detail, (px + 14, row_y + 28), TEXT_MUTED, font_detail)

            frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        # ── Now playing footer ─────────────────
        if self._dj and hasattr(self._dj, 'current_song') and self._dj.current_song:
            song     = self._dj.current_song
            title    = song.title if hasattr(song, 'title') else song.get('title', '')
            footer_y = fh - 48
            cv2.rectangle(frame, (px, footer_y), (fw, fh), (15, 15, 15), -1)
            cv2.line(frame, (px, footer_y), (fw, footer_y), OVERLAY_BORDER, 1)

            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self._put_text(img_pil, "NOW PLAYING", (px + 14, footer_y + 6),  TEXT_MUTED,  font_small)
            self._put_text(img_pil, title,          (px + 14, footer_y + 22), TEXT_ACTIVE, font_title)
            frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        return frame

    # ── Overlay hook ──────────────────────────

    def draw_overlay(self, bgr_frame):
        self._draw_frame(bgr_frame)

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
                    print('[WARN] No DJ engine attached — cannot play audio.')
        elif paths and self._library is None:
            print('[WARN] No song library attached — songs not saved.')

    def stop(self):
        if self._dj is not None:
            self._dj.stop()

    # ── Lifecycle ─────────────────────────────

    def _on_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self.destroy()
