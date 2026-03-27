# ─────────────────────────────────────────────
#  song_panel.py  –  Track list sidebar
# ─────────────────────────────────────────────
#
#  Displays loaded tracks in a scrollable list.
#  Each row shows: title · artist · BPM · duration
#  Clicking a row selects it for the DJ engine.
# ─────────────────────────────────────────────

import tkinter as tk
from tkinter import font as tkfont


# ── Palette (mirrors app_window.py) ──────────
BG       = "#0E0E0E"
SURFACE  = "#1A1A1A"
SURFACE2 = "#222222"   # alternating row shade
BORDER   = "#2A2A2A"
ACCENT   = "#E8E8E8"
MUTED    = "#666666"
ACTIVE   = "#FFFFFF"
SELECTED = "#2C2C2C"   # selected row fill
SEL_BAR  = "#FFFFFF"   # left accent bar on selected row


class SongRow(tk.Frame):
    """Single track row inside the panel."""

    ROW_H = 56

    def __init__(self, parent, track: dict, index: int,
                 on_select=None, **kwargs):
        bg = SURFACE2 if index % 2 == 0 else SURFACE
        super().__init__(parent, bg=bg, height=self.ROW_H, **kwargs)
        self.pack_propagate(False)

        self._track     = track
        self._index     = index
        self._on_select = on_select
        self._bg        = bg
        self._selected  = False

        self._build(bg)
        self.bind("<Button-1>", self._click)

    def _build(self, bg):
        # ── Left accent bar (hidden until selected) ──
        self._bar = tk.Frame(self, bg=bg, width=3)
        self._bar.pack(side="left", fill="y")

        inner = tk.Frame(self, bg=bg, padx=12, pady=0)
        inner.pack(side="left", fill="both", expand=True)
        inner.bind("<Button-1>", self._click)

        title_font  = tkfont.Font(family="Helvetica Neue", size=12, weight="bold")
        detail_font = tkfont.Font(family="Helvetica Neue", size=10)

        # Title
        self._lbl_title = tk.Label(
            inner,
            text=self._track.get("title", "Unknown"),
            bg=bg, fg=ACCENT,
            font=title_font,
            anchor="w",
        )
        self._lbl_title.pack(fill="x", pady=(10, 1))
        self._lbl_title.bind("<Button-1>", self._click)

        # Detail row: artist · BPM · duration
        detail_frame = tk.Frame(inner, bg=bg)
        detail_frame.pack(fill="x")
        detail_frame.bind("<Button-1>", self._click)

        artist   = self._track.get("artist",   "—")
        bpm      = self._track.get("bpm",      "—")
        duration = self._track.get("duration", "—")
        detail   = f"{artist}   ·   {bpm} BPM   ·   {duration}"

        lbl = tk.Label(
            detail_frame,
            text=detail,
            bg=bg, fg=MUTED,
            font=detail_font,
            anchor="w",
        )
        lbl.pack(fill="x")
        lbl.bind("<Button-1>", self._click)

        # Bottom rule
        tk.Frame(self, bg=BORDER, height=1).pack(side="bottom", fill="x")

    def _click(self, _event=None):
        if self._on_select:
            self._on_select(self._index, self._track)

    def set_selected(self, selected: bool):
        self._selected = selected
        bg = SELECTED if selected else self._bg
        bar_color = SEL_BAR if selected else bg
        self._bar.configure(bg=bar_color)
        for widget in self.winfo_children():
            try:
                widget.configure(bg=bg)
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                try:
                    child.configure(bg=bg)
                except tk.TclError:
                    pass
        self.configure(bg=bg)


class SongPanel(tk.Frame):
    """
    Right-hand panel containing a header, scrollable track list,
    and an empty-state prompt when no songs are loaded.
    """

    def __init__(self, parent, width=340,
                 on_import=None, dj_engine=None, song_library=None,
                 **kwargs):
        super().__init__(parent, bg=BG, width=width, **kwargs)
        self.pack_propagate(False)

        self._width        = width
        self._on_import    = on_import
        self._dj           = dj_engine
        self._library      = song_library
        self._rows         = []
        self._selected_idx = -1

        self._build_fonts()
        self._build_header()
        self._build_list()
        self._build_empty_state()

    # ── Fonts ─────────────────────────────────

    def _build_fonts(self):
        self._font_header  = tkfont.Font(family="Helvetica Neue", size=11, weight="bold")
        self._font_label   = tkfont.Font(family="Helvetica Neue", size=11)
        self._font_hint    = tkfont.Font(family="Helvetica Neue", size=10)
        self._font_empty   = tkfont.Font(family="Helvetica Neue", size=12)
        self._font_empty_s = tkfont.Font(family="Helvetica Neue", size=10)

    # ── Header ────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=SURFACE, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="TRACKS",
            bg=SURFACE, fg=MUTED,
            font=self._font_header,
            padx=16,
        ).pack(side="left", fill="y")

        # Import button
        btn = tk.Label(
            hdr, text="+ Import",
            bg=SURFACE, fg=ACCENT,
            font=self._font_hint,
            padx=14, cursor="hand2",
        )
        btn.pack(side="right", fill="y")
        btn.bind("<Button-1>",  lambda _: self._on_import and self._on_import())
        btn.bind("<Enter>",     lambda _: btn.configure(fg=ACTIVE))
        btn.bind("<Leave>",     lambda _: btn.configure(fg=ACCENT))

        tk.Frame(hdr, bg=BORDER, height=1).place(
            relx=0, rely=1.0, relwidth=1, anchor="sw"
        )

    # ── Scrollable list ───────────────────────

    def _build_list(self):
        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True)

        # Thin custom scrollbar
        self._scrollbar = tk.Scrollbar(
            container, orient="vertical",
            bg=BORDER, troughcolor=BG,
            activebackground=MUTED,
            highlightthickness=0, bd=0, width=6,
        )
        self._scrollbar.pack(side="right", fill="y")

        self._canvas = tk.Canvas(
            container,
            bg=BG, highlightthickness=0,
            yscrollcommand=self._scrollbar.set,
        )
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.configure(command=self._canvas.yview)

        self._list_frame = tk.Frame(self._canvas, bg=BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw"
        )

        self._list_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>",     self._on_canvas_configure)

        # Mouse-wheel scrolling
        self._canvas.bind_all("<MouseWheel>",       self._on_mousewheel)
        self._canvas.bind_all("<Button-4>",         self._on_mousewheel)
        self._canvas.bind_all("<Button-5>",         self._on_mousewheel)

    def _on_frame_configure(self, _event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-event.delta / 60), "units")

    # ── Empty state ───────────────────────────

    def _build_empty_state(self):
        self._empty = tk.Frame(self._list_frame, bg=BG, pady=60)
        self._empty.pack(fill="x")

        tk.Label(
            self._empty,
            text="No tracks loaded",
            bg=BG, fg=MUTED,
            font=self._font_empty,
        ).pack()

        tk.Label(
            self._empty,
            text="Press  I  or click + Import",
            bg=BG, fg=BORDER,
            font=self._font_empty_s,
        ).pack(pady=(6, 0))

    # ── Public API ────────────────────────────

    def refresh(self, tracks: list = None):
        """
        Re-render the track list.
        If `tracks` is None and a song_library is attached,
        it reads tracks from there.
        """
        if tracks is None and self._library is not None:
            tracks = self._library.all_tracks()
        tracks = tracks or []

        # Clear existing rows
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._selected_idx = -1

        # Hide/show empty state
        if tracks:
            self._empty.pack_forget()
        else:
            self._empty.pack(fill="x")
            return

        for i, track in enumerate(tracks):
            row = SongRow(
                self._list_frame,
                track=track,
                index=i,
                on_select=self._select_track,
            )
            row.pack(fill="x")
            self._rows.append(row)

    def _select_track(self, index: int, track: dict):
        # Deselect previous
        if 0 <= self._selected_idx < len(self._rows):
            self._rows[self._selected_idx].set_selected(False)

        self._selected_idx = index

        if 0 <= index < len(self._rows):
            self._rows[index].set_selected(True)

        # Pass to DJ engine if available
        if self._dj is not None:
            self._dj.load_track(track)

    def select_by_index(self, index: int):
        """External hook — gesture system can call this to select a card."""
        if 0 <= index < len(self._rows):
            track = self._rows[index]._track
            self._select_track(index, track)

    @property
    def track_count(self) -> int:
        return len(self._rows)
