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
        self._volume   = 50     # volume level (0-100)

        self._configure_window()
        self._load_fonts()
        self._build_ui()

    # ── Window setup ──────────────────────────

    def _configure_window(self):
        self.title(WINDOW_NAME)
        self.configure(bg=BG)
        self.resizable(False, False)

        total_w = self.FEED_W + self.PANEL_W + 3   # 3 px divider
        total_h = self.FEED_H + 48 + 40             # 48 px header + 40 px volume bar
        self.geometry(f"{total_w}x{total_h}")

        # Centre on screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - total_w) // 2
        y  = (sh - total_h) // 2
        self.geometry(f"{total_w}x{total_h}+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<KeyPress-q>", lambda _: self._on_close())
        self.bind("<KeyPress-i>", lambda _: self._open_import())

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
        hints = [("Q", "quit"), ("I", "import")]
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

        # ── Left: camera + volume bar ─────────
        left_panel = tk.Frame(body, bg=BG)
        left_panel.pack(side="left")

        # Camera canvas
        self._canvas = tk.Canvas(
            left_panel,
            width=self.FEED_W, height=self.FEED_H,
            bg=SURFACE, highlightthickness=0,
        )
        self._canvas.pack()

        # Placeholder text until the first frame arrives
        self._canvas.create_text(
            self.FEED_W // 2, self.FEED_H // 2,
            text="Waiting for camera…",
            fill=MUTED, font=self._font_label,
            tags="placeholder",
        )

        # Volume bar
        self._volume_canvas = tk.Canvas(
            left_panel,
            width=self.FEED_W, height=40,
            bg=SURFACE, highlightthickness=0,
        )
        self._volume_canvas.pack(fill="x")
        self._volume_canvas.bind("<Configure>", lambda _: self._redraw_volume_bar())

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
        # Remove placeholder text on first real frame
        self._canvas.delete("placeholder")

        rgb   = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        img   = Image.fromarray(rgb).resize(
            (self.FEED_W, self.FEED_H), Image.BILINEAR
        )
        photo = ImageTk.PhotoImage(img)

        self._canvas.create_image(0, 0, anchor="nw", image=photo)
        # Keep a reference so Tkinter's GC doesn't discard it
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

    # ── Volume control ────────────────────────

    def _redraw_volume_bar(self):
        """Redraw the volume bar based on current volume level."""
        self._volume_canvas.delete("all")
        
        canvas_width = self._volume_canvas.winfo_width()
        canvas_height = self._volume_canvas.winfo_height()
        
        # Handle case where canvas hasn't been rendered yet
        if canvas_width <= 1:
            canvas_width = self.FEED_W
        if canvas_height <= 1:
            canvas_height = 40

        # Padding and dimensions
        padding = 12
        bar_height = 8
        bar_y = (canvas_height - bar_height) // 2

        # Background bar (unfilled)
        bar_width = canvas_width - 2 * padding
        self._volume_canvas.create_rectangle(
            padding, bar_y,
            padding + bar_width, bar_y + bar_height,
            fill=BORDER, outline=MUTED, width=1,
            tags="bg_bar"
        )

        # Filled bar (shows current volume)
        fill_width = (self._volume * bar_width) // 100
        if fill_width > 0:
            self._volume_canvas.create_rectangle(
                padding, bar_y,
                padding + fill_width, bar_y + bar_height,
                fill=ACCENT, outline=ACCENT, width=0,
                tags="fill_bar"
            )

        # Volume text label
        volume_text = f"Volume: {self._volume}%"
        self._volume_canvas.create_text(
            canvas_width // 2, canvas_height // 2,
            text=volume_text,
            fill=ACTIVE, font=self._font_label,
            tags="volume_text"
        )

    def handle_volume_up(self):
        """Increase volume by 5%."""
        self._volume = min(100, self._volume + 5)
        self._redraw_volume_bar()
        print(f'[INFO] Volume: {self._volume}%')

    def handle_volume_down(self):
        """Decrease volume by 5%."""
        self._volume = max(0, self._volume - 5)
        self._redraw_volume_bar()
        print(f'[INFO] Volume: {self._volume}%')

    def get_volume(self):
        """Get current volume level (0-100)."""
        return self._volume

    def set_volume(self, level):
        """Set volume level (0-100)."""
        self._volume = max(0, min(100, level))
        self._redraw_volume_bar()

    # ── Lifecycle ─────────────────────────────

    def _on_close(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self.destroy()
