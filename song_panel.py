# ─────────────────────────────────────────────
#  song_panel.py  –  Track list sidebar
# ─────────────────────────────────────────────

import tkinter as tk
from tkinter import font as tkfont


# ── Palette ───────────────────────────────────
BG       = "#0E0E0E"
SURFACE  = "#1A1A1A"
SURFACE2 = "#222222"
BORDER   = "#2A2A2A"
ACCENT   = "#E8E8E8"
MUTED    = "#666666"
ACTIVE   = "#FFFFFF"
SELECTED = "#2C2C2C"
SEL_BAR  = "#FFFFFF"
DRAG_BG  = "#333333"
VOL_FILL = "#FFFFFF"
VOL_BG   = "#2A2A2A"


class SongRow(tk.Frame):
    """Single numbered track row with drag-to-reorder support."""

    ROW_H = 56

    def __init__(self, parent, track: dict, index: int,
                 on_select=None, on_drag_start=None,
                 on_drag_motion=None, on_drag_end=None, **kwargs):
        bg = SURFACE2 if index % 2 == 0 else SURFACE
        super().__init__(parent, bg=bg, height=self.ROW_H, **kwargs)
        self.pack_propagate(False)

        self._track          = track
        self._index          = index
        self._on_select      = on_select
        self._on_drag_start  = on_drag_start
        self._on_drag_motion = on_drag_motion
        self._on_drag_end    = on_drag_end
        self._bg             = bg
        self._selected       = False

        self._build(bg)

    def _build(self, bg):
        # Left accent bar
        self._bar = tk.Frame(self, bg=bg, width=3)
        self._bar.pack(side="left", fill="y")

        # Track number
        num_font = tkfont.Font(family="TkDefaultFont", size=10)
        self._num_lbl = tk.Label(
            self, text=str(self._index + 1),
            bg=bg, fg=MUTED, font=num_font, width=3, anchor="e",
        )
        self._num_lbl.pack(side="left", fill="y", padx=(4, 0))

        # Drag handle
        handle_font = tkfont.Font(family="TkDefaultFont", size=13)
        self._handle = tk.Label(
            self, text="⠿", bg=bg, fg=BORDER,
            font=handle_font, cursor="fleur", padx=6,
        )
        self._handle.pack(side="left", fill="y")

        # Text content
        inner = tk.Frame(self, bg=bg, padx=8, pady=0)
        inner.pack(side="left", fill="both", expand=True)

        title_font  = tkfont.Font(family="TkDefaultFont", size=12, weight="bold")
        detail_font = tkfont.Font(family="TkDefaultFont", size=10)

        self._lbl_title = tk.Label(
            inner, text=self._track.get("title", "Unknown"),
            bg=bg, fg=ACCENT, font=title_font, anchor="w",
        )
        self._lbl_title.pack(fill="x", pady=(10, 1))

        artist   = self._track.get("artist",   "—")
        bpm      = self._track.get("bpm",      "—")
        duration = self._track.get("duration", "—")

        self._lbl_detail = tk.Label(
            inner,
            text=f"{artist}   ·   {bpm} BPM   ·   {duration}",
            bg=bg, fg=MUTED, font=detail_font, anchor="w",
        )
        self._lbl_detail.pack(fill="x")

        tk.Frame(self, bg=BORDER, height=1).pack(side="bottom", fill="x")

        # Click binds (everything except handle)
        for w in (self, inner, self._lbl_title, self._lbl_detail, self._num_lbl):
            w.bind("<Button-1>", self._click)

        # Drag binds (handle only)
        self._handle.bind("<ButtonPress-1>",   self._drag_start)
        self._handle.bind("<B1-Motion>",       self._drag_motion)
        self._handle.bind("<ButtonRelease-1>", self._drag_end)

    def _click(self, _=None):
        if self._on_select:
            self._on_select(self._index, self._track)

    def _drag_start(self, event):
        if self._on_drag_start:
            self._on_drag_start(self._index, event)

    def _drag_motion(self, event):
        if self._on_drag_motion:
            self._on_drag_motion(self._index, event)

    def _drag_end(self, event):
        if self._on_drag_end:
            self._on_drag_end(self._index, event)

    def update_number(self, new_index: int):
        self._index = new_index
        self._bg = SURFACE2 if new_index % 2 == 0 else SURFACE
        self._num_lbl.configure(text=str(new_index + 1))

    def set_dragging(self, dragging: bool):
        self._apply_bg(DRAG_BG if dragging else self._bg)

    def set_selected(self, selected: bool):
        self._selected = selected
        bg = SELECTED if selected else self._bg
        self._bar.configure(bg=SEL_BAR if selected else bg)
        self._apply_bg(bg)

    def _apply_bg(self, bg):
        self.configure(bg=bg)
        for w in self.winfo_children():
            try:
                w.configure(bg=bg)
            except tk.TclError:
                pass
            for c in w.winfo_children():
                try:
                    c.configure(bg=bg)
                except tk.TclError:
                    pass


class SongPanel(tk.Frame):
    """Right-hand panel: numbered tracks, drag reorder, volume bar."""

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

        self._drag_src    = -1
        self._drag_target = -1
        self._drop_line   = None

        self._build_fonts()
        self._build_header()
        self._build_volume_bar()   # pinned bottom — pack before list
        self._build_list()
        self._build_empty_state()

    # ── Fonts ─────────────────────────────────

    def _build_fonts(self):
        self._font_header  = tkfont.Font(family="TkDefaultFont", size=11, weight="bold")
        self._font_label   = tkfont.Font(family="TkDefaultFont", size=11)
        self._font_hint    = tkfont.Font(family="TkDefaultFont", size=10)
        self._font_empty   = tkfont.Font(family="TkDefaultFont", size=12)
        self._font_empty_s = tkfont.Font(family="TkDefaultFont", size=10)
        self._font_vol     = tkfont.Font(family="TkDefaultFont", size=9)

    # ── Header ────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=SURFACE, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="TRACKS",
            bg=SURFACE, fg=MUTED,
            font=self._font_header, padx=16,
        ).pack(side="left", fill="y")

        btn = tk.Label(
            hdr, text="+ Import",
            bg=SURFACE, fg=ACCENT,
            font=self._font_hint, padx=14, cursor="hand2",
        )
        btn.pack(side="right", fill="y")
        btn.bind("<Button-1>", lambda _: self._on_import and self._on_import())
        btn.bind("<Enter>",    lambda _: btn.configure(fg=ACTIVE))
        btn.bind("<Leave>",    lambda _: btn.configure(fg=ACCENT))

        tk.Frame(hdr, bg=BORDER, height=1).place(
            relx=0, rely=1.0, relwidth=1, anchor="sw"
        )

    # ── Volume bar (bottom) ───────────────────

    def _build_volume_bar(self):
        vol_frame = tk.Frame(self, bg=SURFACE, height=52)
        vol_frame.pack(fill="x", side="bottom")
        vol_frame.pack_propagate(False)

        tk.Frame(vol_frame, bg=BORDER, height=1).pack(fill="x")

        inner = tk.Frame(vol_frame, bg=SURFACE, padx=14, pady=6)
        inner.pack(fill="both", expand=True)

        # Label row
        label_row = tk.Frame(inner, bg=SURFACE)
        label_row.pack(fill="x")

        tk.Label(
            label_row, text="VOLUME",
            bg=SURFACE, fg=MUTED, font=self._font_vol,
        ).pack(side="left")

        self._vol_pct_lbl = tk.Label(
            label_row, text="80%",
            bg=SURFACE, fg=ACCENT, font=self._font_vol,
        )
        self._vol_pct_lbl.pack(side="right")

        # Bar track
        bar_track = tk.Frame(inner, bg=VOL_BG, height=6, cursor="hand2")
        bar_track.pack(fill="x", pady=(5, 0))
        bar_track.pack_propagate(False)

        self._vol_fill = tk.Frame(bar_track, bg=VOL_FILL, height=6)
        self._vol_fill.place(relx=0, rely=0, relheight=1, relwidth=0.8)

        bar_track.bind("<ButtonPress-1>", lambda e: self._vol_seek(e, bar_track))
        bar_track.bind("<B1-Motion>",     lambda e: self._vol_seek(e, bar_track))
        self._vol_fill.bind("<ButtonPress-1>", lambda e: self._vol_seek(e, bar_track))
        self._vol_fill.bind("<B1-Motion>",     lambda e: self._vol_seek(e, bar_track))

        self._vol_bar_track = bar_track
        self._vol_level     = 0.8

        if self._dj and hasattr(self._dj, 'volume'):
            self._vol_level = self._dj.volume
            self._refresh_vol_ui()

    def _vol_seek(self, event, bar_track):
        bar_track.update_idletasks()
        w = bar_track.winfo_width()
        if w <= 0:
            return
        ratio = max(0.0, min(1.0, event.x / w))
        self._vol_level = ratio
        self._refresh_vol_ui()
        if self._dj is not None:
            self._dj.volume = ratio
            self._dj._apply_volume()

    def _refresh_vol_ui(self):
        self._vol_fill.place(relwidth=self._vol_level)
        self._vol_pct_lbl.configure(text=f"{int(self._vol_level * 100)}%")

    def update_volume(self, level: float):
        """External hook — call to sync bar when volume changes via gesture."""
        self._vol_level = max(0.0, min(1.0, level))
        self._refresh_vol_ui()

    # ── Scrollable list ───────────────────────

    def _build_list(self):
        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True)

        self._scrollbar = tk.Scrollbar(
            container, orient="vertical",
            bg=BORDER, troughcolor=BG,
            activebackground=MUTED,
            highlightthickness=0, bd=0, width=6,
        )
        self._scrollbar.pack(side="right", fill="y")

        self._canvas = tk.Canvas(
            container, bg=BG, highlightthickness=0,
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
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>",   self._on_mousewheel)
        self._canvas.bind_all("<Button-5>",   self._on_mousewheel)

    def _on_frame_configure(self, _=None):
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
            self._empty, text="No tracks loaded",
            bg=BG, fg=MUTED, font=self._font_empty,
        ).pack()
        tk.Label(
            self._empty, text="Press  I  or click + Import",
            bg=BG, fg=BORDER, font=self._font_empty_s,
        ).pack(pady=(6, 0))

    # ── Drag-to-reorder ───────────────────────

    def _drag_start(self, index: int, event):
        self._drag_src    = index
        self._drag_target = index
        if 0 <= index < len(self._rows):
            self._rows[index].set_dragging(True)

    def _drag_motion(self, index: int, event):
        if self._drag_src < 0:
            return
        row     = self._rows[self._drag_src]
        abs_y   = row.winfo_rooty() + event.y
        frame_y = abs_y - self._list_frame.winfo_rooty()
        target  = max(0, min(len(self._rows) - 1, frame_y // SongRow.ROW_H))

        if target != self._drag_target:
            self._drag_target = target
            self._show_drop_line(target)

    def _drag_end(self, index: int, event):
        if self._drag_src < 0:
            return

        src = self._drag_src
        dst = self._drag_target

        if 0 <= src < len(self._rows):
            self._rows[src].set_dragging(False)
        self._hide_drop_line()
        self._drag_src    = -1
        self._drag_target = -1

        if src != dst and self._library is not None:
            songs = self._library.songs
            song  = songs.pop(src)
            songs.insert(dst, song)
            self._library._save()

            # Update selected index tracking
            if self._selected_idx == src:
                self._selected_idx = dst
            elif src < self._selected_idx <= dst:
                self._selected_idx -= 1
            elif dst <= self._selected_idx < src:
                self._selected_idx += 1

            self.refresh()

    def _show_drop_line(self, target_index: int):
        self._hide_drop_line()
        if not self._rows:
            return
        ref = self._rows[min(target_index, len(self._rows) - 1)]
        self._drop_line = tk.Frame(self._list_frame, bg=ACTIVE, height=2)
        self._drop_line.place(x=0, y=ref.winfo_y(), relwidth=1)
        self._drop_line.lift()

    def _hide_drop_line(self):
        if self._drop_line:
            self._drop_line.destroy()
            self._drop_line = None

    # ── Public API ────────────────────────────

    def refresh(self, tracks: list = None):
        if tracks is None and self._library is not None:
            tracks = self._library.all_tracks()
        tracks = tracks or []

        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._selected_idx = -1

        if tracks:
            self._empty.pack_forget()
        else:
            self._empty.pack(fill="x")
            return

        for i, track in enumerate(tracks):
            row = SongRow(
                self._list_frame,
                track=track, index=i,
                on_select=self._select_track,
                on_drag_start=self._drag_start,
                on_drag_motion=self._drag_motion,
                on_drag_end=self._drag_end,
            )
            row.pack(fill="x")
            self._rows.append(row)

    def _select_track(self, index: int, track: dict):
        if 0 <= self._selected_idx < len(self._rows):
            self._rows[self._selected_idx].set_selected(False)
        self._selected_idx = index
        if 0 <= index < len(self._rows):
            self._rows[index].set_selected(True)
        if self._dj is not None:
            self._dj.load_track(track)

    def select_by_index(self, index: int):
        if 0 <= index < len(self._rows):
            self._select_track(index, self._rows[index]._track)

    @property
    def track_count(self) -> int:
        return len(self._rows)
