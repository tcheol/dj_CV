# ─────────────────────────────────────────────
#  import_dialog.py  –  Song import dialog
# ─────────────────────────────────────────────
#
#  Modal dialog that lets the user browse for
#  audio files and confirm the selection before
#  handing paths back to the app.
#
#  Usage:
#      ImportDialog(parent, on_confirm=callback)
#      # callback receives: list[str] of file paths
# ─────────────────────────────────────────────

import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog


# ── Palette (mirrors app_window.py) ──────────
BG       = "#0E0E0E"
SURFACE  = "#1A1A1A"
SURFACE2 = "#222222"
BORDER   = "#2A2A2A"
ACCENT   = "#E8E8E8"
MUTED    = "#666666"
ACTIVE   = "#FFFFFF"
DANGER   = "#CC4444"

# Supported audio extensions
AUDIO_TYPES = [
    ("Audio files", "*.mp3 *.wav *.flac *.aac *.ogg *.m4a"),
    ("MP3",         "*.mp3"),
    ("WAV",         "*.wav"),
    ("FLAC",        "*.flac"),
    ("All files",   "*.*"),
]


class ImportDialog(tk.Toplevel):
    """
    Modal file-import dialog.

    Flow
    ────
    1. Opens immediately with an empty staged list.
    2. User clicks "Browse" to pick one or more audio files.
       Files are appended to the staged list (duplicates ignored).
    3. Individual files can be removed with the × button.
    4. "Add to Library" confirms and calls on_confirm(paths).
    5. "Cancel" / window close discards everything.
    """

    W, H = 520, 440

    def __init__(self, parent, on_confirm=None):
        super().__init__(parent)
        self._on_confirm = on_confirm
        self._staged     = []   # list of absolute file paths

        self._configure_dialog(parent)
        self._build_fonts()
        self._build_ui()

        # Trigger a browse immediately on open for convenience
        self.after(100, self._browse)

    # ── Dialog setup ──────────────────────────

    def _configure_dialog(self, parent):
        self.title("Import Tracks")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry(f"{self.W}x{self.H}")
        self.transient(parent)
        self.grab_set()             # modal — blocks interaction with parent

        # Centre over parent
        parent.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width()  - self.W) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.H) // 2
        self.geometry(f"{self.W}x{self.H}+{px}+{py}")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<Return>", lambda _: self._confirm())

    def _build_fonts(self):
        self._font_title   = tkfont.Font(family="Helvetica Neue", size=13, weight="bold")
        self._font_label   = tkfont.Font(family="Helvetica Neue", size=11)
        self._font_small   = tkfont.Font(family="Helvetica Neue", size=10)
        self._font_btn     = tkfont.Font(family="Helvetica Neue", size=11, weight="bold")
        self._font_remove  = tkfont.Font(family="Helvetica Neue", size=12)

    # ── UI construction ───────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_file_list()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self, bg=SURFACE, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="Import Tracks",
            bg=SURFACE, fg=ACTIVE,
            font=self._font_title, padx=20,
        ).pack(side="left", fill="y")

        # Browse button in header
        browse_btn = tk.Label(
            hdr, text="+ Browse",
            bg=SURFACE, fg=ACCENT,
            font=self._font_small, padx=16,
            cursor="hand2",
        )
        browse_btn.pack(side="right", fill="y")
        browse_btn.bind("<Button-1>", lambda _: self._browse())
        browse_btn.bind("<Enter>",    lambda _: browse_btn.configure(fg=ACTIVE))
        browse_btn.bind("<Leave>",    lambda _: browse_btn.configure(fg=ACCENT))

        tk.Frame(hdr, bg=BORDER, height=1).place(
            relx=0, rely=1.0, relwidth=1, anchor="sw"
        )

    def _build_file_list(self):
        # Count label
        self._count_frame = tk.Frame(self, bg=BG, pady=10, padx=20)
        self._count_frame.pack(fill="x")

        self._count_lbl = tk.Label(
            self._count_frame,
            text="No files selected",
            bg=BG, fg=MUTED,
            font=self._font_small, anchor="w",
        )
        self._count_lbl.pack(fill="x")

        # Scrollable list
        list_container = tk.Frame(self, bg=BG, padx=16)
        list_container.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(
            list_container, orient="vertical",
            bg=BORDER, troughcolor=BG,
            highlightthickness=0, bd=0, width=5,
        )
        scrollbar.pack(side="right", fill="y")

        self._list_canvas = tk.Canvas(
            list_container,
            bg=BG, highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        self._list_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self._list_canvas.yview)

        self._list_frame = tk.Frame(self._list_canvas, bg=BG)
        self._list_window = self._list_canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw"
        )

        self._list_frame.bind(
            "<Configure>",
            lambda _: self._list_canvas.configure(
                scrollregion=self._list_canvas.bbox("all")
            )
        )
        self._list_canvas.bind(
            "<Configure>",
            lambda e: self._list_canvas.itemconfig(
                self._list_window, width=e.width
            )
        )

        # Empty-state hint inside the list
        self._empty_lbl = tk.Label(
            self._list_frame,
            text="Click  + Browse  to pick audio files",
            bg=BG, fg=BORDER,
            font=self._font_small, pady=24,
        )
        self._empty_lbl.pack()

    def _build_footer(self):
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        footer = tk.Frame(self, bg=SURFACE, height=60)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        # Cancel
        cancel = tk.Label(
            footer, text="Cancel",
            bg=SURFACE, fg=MUTED,
            font=self._font_label, padx=20,
            cursor="hand2",
        )
        cancel.pack(side="left", fill="y")
        cancel.bind("<Button-1>", lambda _: self.destroy())
        cancel.bind("<Enter>",    lambda _: cancel.configure(fg=ACCENT))
        cancel.bind("<Leave>",    lambda _: cancel.configure(fg=MUTED))

        # Confirm button
        self._confirm_btn = tk.Label(
            footer, text="Add to Library",
            bg=SURFACE, fg=MUTED,
            font=self._font_btn, padx=20,
            cursor="hand2",
        )
        self._confirm_btn.pack(side="right", fill="y")
        self._confirm_btn.bind("<Button-1>", lambda _: self._confirm())

    # ── Browse & list management ──────────────

    def _browse(self):
        paths = filedialog.askopenfilenames(
            parent=self,
            title="Select audio files",
            filetypes=AUDIO_TYPES,
        )
        if not paths:
            return

        added = 0
        for p in paths:
            p = os.path.abspath(p)
            if p not in self._staged:
                self._staged.append(p)
                added += 1

        if added:
            self._render_list()

    def _render_list(self):
        # Clear current rows
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        if not self._staged:
            self._empty_lbl = tk.Label(
                self._list_frame,
                text="Click  + Browse  to pick audio files",
                bg=BG, fg=BORDER,
                font=self._font_small, pady=24,
            )
            self._empty_lbl.pack()
            self._count_lbl.configure(text="No files selected")
            self._confirm_btn.configure(fg=MUTED)
            return

        # Update count
        n = len(self._staged)
        self._count_lbl.configure(
            text=f"{n} file{'s' if n != 1 else ''} ready to import"
        )
        self._confirm_btn.configure(fg=ACTIVE)

        # File rows
        for i, path in enumerate(self._staged):
            self._add_file_row(i, path)

    def _add_file_row(self, index: int, path: str):
        bg = SURFACE2 if index % 2 == 0 else SURFACE

        row = tk.Frame(self._list_frame, bg=bg, height=40)
        row.pack(fill="x")
        row.pack_propagate(False)

        # Remove button
        rm = tk.Label(
            row, text="×",
            bg=bg, fg=MUTED,
            font=self._font_remove,
            padx=10, cursor="hand2",
        )
        rm.pack(side="right", fill="y")
        rm.bind("<Button-1>", lambda _, p=path: self._remove(p))
        rm.bind("<Enter>",    lambda _, w=rm: w.configure(fg=DANGER))
        rm.bind("<Leave>",    lambda _, w=rm: w.configure(fg=MUTED))

        # Filename
        filename = os.path.basename(path)
        tk.Label(
            row, text=filename,
            bg=bg, fg=ACCENT,
            font=self._font_small,
            anchor="w", padx=12,
        ).pack(side="left", fill="both", expand=True)

        # Bottom rule
        tk.Frame(row, bg=BORDER, height=1).place(
            relx=0, rely=1.0, relwidth=1, anchor="sw"
        )

    def _remove(self, path: str):
        if path in self._staged:
            self._staged.remove(path)
            self._render_list()

    # ── Confirm ───────────────────────────────

    def _confirm(self):
        if not self._staged:
            return
        paths = list(self._staged)
        self.destroy()
        if self._on_confirm:
            self._on_confirm(paths)
