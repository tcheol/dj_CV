# ─────────────────────────────────────────────
#  app_window.py  –  Main application window
# ─────────────────────────────────────────────
#
#  Hosts the OpenCV camera feed on the left and
#  the song panel on the right inside a single
#  clean Tkinter window.
#
#  Usage (from main.py):
#      from app_window import AppWindow
#      win = AppWindow()
#      win.mainloop()          # blocking – runs the Tk event loop
# ─────────────────────────────────────────────

import tkinter as tk
from tkinter import font as tkfont
import cv2
from PIL import Image, ImageTk   # pip install Pillow

from song_panel    import SongPanel
from import_dialog import ImportDialog
from config        import WINDOW_NAME, CAMERA_WIDTH, CAMERA_HEIGHT


# ── Palette ───────────────────────────────────
BG       = "#0E0E0E"   # near-black canvas
SURFACE  = "#1A1A1A"   # card / panel surface
BORDER   = "#2A2A2A"   # subtle rule
ACCENT   = "#E8E8E8"   # primary text / highlights
MUTED    = "#666666"   # secondary text
ACTIVE   = "#FFFFFF"   # active / selected


class AppWindow(tk.Tk):
    """
    Top-level Tkinter window for the Gesture DJ Controller.

    Layout
    ──────
    ┌──────────────────────────────────┬──────────────┐
    │  Header bar  (title + shortcuts) │              │
    ├──────────────────────────────────┤  SongPanel   │
    │  Camera feed (OpenCV frames)     │              │
    └──────────────────────────────────┴──────────────┘
    """

    FEED_W = 854    # displayed camera width  (16:9 at ~67 % of 1280)
    FEED_H = 480    # displayed camera height
    PANEL_W = 340   # right-hand song panel width

    def __init__(self, camera_manager=None, dj_engine=None, song_library=None):
        super().__init__()

        self._cam     = camera_manager
        self._dj      = dj_engine
        self._library = song_library

        self._after_id = None   # holds the scheduled frame-update id

        self._configure_window()
        self._load_fonts()
        self._build_ui()

    # ── Window setup ──────────────────────────

    def _configure_window(self):
        self.title(WINDOW_NAME)
        self.configure(bg=BG)
        total_w = self.FEED_W + self.PANEL_W + 3   # 3 px divider
        total_h = self.FEED_H + 48                  # 48 px header
        self.geometry(f"{total_w}x{total_h}")

        # Centre on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - total_w) // 2
        y  = (sh - total_h) // 2
        self.geometry(f"{total_w}x{total_h}+{x}+{y}")

        self._fullscreen = False
        self.resizable(True, True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<KeyPress-q>",  lambda _: self._on_close())
        self.bind("<KeyPress-i>",  lambda _: self._open_import())
        self.bind("<KeyPress-f>",  lambda _: self._toggle_fullscreen())
        self.bind("<F11>",         lambda _: self._toggle_fullscreen())
        self.bind("<Escape>",      lambda _: self._exit_fullscreen())
        self.bind("<Configure>",   self._on_resize)

    def _load_fonts(self):
        self._font_title  = tkfont.Font(family="Helvetica Neue", size=13, weight="bold")
        self._font_label  = tkfont.Font(family="Helvetica Neue", size=11)
        self._font_hint   = tkfont.Font(family="Helvetica Neue", size=10)

    # ── UI construction ───────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_body()

    def _build_header(self):
        hdr = tk.Frame(self, bg=SURFACE, height=48)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        # Title
        tk.Label(
            hdr, text=WINDOW_NAME.upper(),
            bg=SURFACE, fg=ACTIVE,
            font=self._font_title,
            padx=20,
        ).pack(side="left", fill="y")

        # Keyboard hint pills  (Q = quit  |  I = import)
        hints = [("Q", "quit"), ("I", "import"), ("F", "fullscreen")]
        for key, label in hints:
            pill = tk.Frame(hdr, bg=BORDER, padx=8, pady=0)
            pill.pack(side="right", padx=(0, 8), fill="y", pady=12)
            tk.Label(pill, text=key,   bg=BORDER, fg=ACTIVE, font=self._font_hint).pack(side="left")
            tk.Label(pill, text=f" {label}", bg=BORDER, fg=MUTED,  font=self._font_hint).pack(side="left")

        # Thin bottom rule
        tk.Frame(hdr, bg=BORDER, height=1).place(relx=0, rely=1.0, relwidth=1, anchor="sw")

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # ── Left: camera canvas ───────────────
        self._canvas = tk.Canvas(
            body,
            width=self.FEED_W, height=self.FEED_H,
            bg=SURFACE, highlightthickness=0,
        )
        self._canvas.pack(side="left")

        # Placeholder text until the first frame arrives
        self._canvas.create_text(
            self.FEED_W // 2, self.FEED_H // 2,
            text="Waiting for camera…",
            fill=MUTED, font=self._font_label,
            tags="placeholder",
        )

        # ── Divider ───────────────────────────
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # ── Right: song panel ─────────────────
        self._song_panel = SongPanel(
            body,
            width=self.PANEL_W,
            on_import=self._open_import,
            dj_engine=self._dj,
            song_library=self._library,
        )
        self._song_panel.pack(side="left", fill="both", expand=True)

    # ── Fullscreen ───────────────────────────

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self.attributes("-fullscreen", self._fullscreen)

    def _exit_fullscreen(self):
        if self._fullscreen:
            self._fullscreen = False
            self.attributes("-fullscreen", False)

    def _on_resize(self, event=None):
        """Resize the camera canvas whenever the window size changes."""
        if event and event.widget is not self:
            return
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        hdr_h = 48

        if self._fullscreen:
            # Camera fills the whole screen, panel slides off
            feed_w = win_w
            feed_h = win_h
        else:
            # Normal layout: camera takes window minus panel
            feed_w = max(100, win_w - self.PANEL_W - 3)
            feed_h = max(100, win_h - hdr_h)

        self._canvas.config(width=feed_w, height=feed_h)

    # ── Camera feed loop ──────────────────────

    def start_feed(self):
        """
        Begin polling the camera and drawing frames onto the canvas.
        Call this after mainloop() would block — typically run in a thread
        or call before mainloop() and let Tkinter's after() drive it.
        """
        self._update_frame()

    def _update_frame(self):
        """Scheduled every ~33 ms to pull a frame and refresh the canvas."""
        if self._cam is not None:
            frame = self._cam.read()
            if frame is not None:
                self._draw_frame(frame)

        # Reschedule
        self._after_id = self.after(33, self._update_frame)

    def _draw_frame(self, bgr_frame):
        """Convert a BGR OpenCV frame to a Tk PhotoImage and blit it."""
        self._canvas.delete("placeholder")

        # Use actual canvas size so it fills correctly in fullscreen
        cw = self._canvas.winfo_width()  or self.FEED_W
        ch = self._canvas.winfo_height() or self.FEED_H

        rgb   = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        img   = Image.fromarray(rgb).resize((cw, ch), Image.BILINEAR)
        photo = ImageTk.PhotoImage(img)

        self._canvas.create_image(0, 0, anchor="nw", image=photo)
        self._canvas._photo = photo

    # ── Overlay helpers ───────────────────────

    def draw_overlay(self, bgr_frame):
        """
        External hook — call this from your main gesture loop to push a
        pre-annotated frame (with landmark overlays) into the canvas.
        """
        self._draw_frame(bgr_frame)

    # ── Import dialog ─────────────────────────

    def _open_import(self):
        ImportDialog(self, on_confirm=self._on_songs_imported)

    def _on_songs_imported(self, paths):
        if paths and self._library is not None:
            added = self._library.add_files(paths)
            if added:
                self._song_panel.refresh()
                # Auto-play the first newly imported song via DJ engine
                first_song = self._library.songs[-added]
                if self._dj is not None:
                    self._dj.load_and_play(first_song)
                    print(f'[INFO] Now playing: {first_song.title}')
                else:
                    print('[WARN] No DJ engine attached — cannot play audio.')
        elif paths and self._library is None:
            print('[WARN] No song library attached — songs not saved.')

    def stop(self):
        """Stop playback."""
        if self._dj is not None:
            self._dj.stop()

    # ── Lifecycle ─────────────────────────────

    def _on_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self.destroy()
