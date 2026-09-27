"""
DriveAnalyzerScreen — TechGuardAI

KEY ARCHITECTURAL CHANGE (fixes window freeze / low-memory crash):
  The old design created one CTkFrame + 6 CTk widgets per file row.
  At 200 rows that is 1,400 CTk objects — each allocating internal Canvases,
  theme images, and font objects — consuming hundreds of MB of RAM.
  Windows shows "application may crash, low memory" and the screen breaks.

  New design: each file-list tab uses ONE _VirtualFileList (a tk.Canvas).
  Rows are drawn as canvas items (rectangles + text). There are ZERO real
  Tk/CTk widget objects per row. The canvas can hold 10,000 rows with the
  same memory as 10 rows. Scrolling re-draws only the visible ~20 rows.

  Interactive elements:
  • Checkbox: a drawn rectangle that toggles fill on click
  • Delete:    a drawn button that opens a confirm dialog on click
  All hit-testing is done from (x, y) coordinates — no real widgets needed.
"""

import os
import tkinter as tk
import logging
import subprocess
import threading
import customtkinter as ctk
from tkinter import messagebox
from ui.styles import THEME, FONTS
from core.disk_analyzer import DiskAnalyzer, get_available_drives, estimate_scan_time, _fmt_size

logger = logging.getLogger(__name__)


# ── Colour palette ────────────────────────────────────────────────────────────
ACCENT       = THEME["accent_color"]
DANGER       = THEME["danger_color"]
SUCCESS      = THEME["success_color"]
WARNING      = THEME["warning_color"]
CARD         = THEME["card_color"]
SECONDARY    = THEME.get("secondary_color", "#3b3b3b")
TAB_ACTIVE   = "#1f6aa5"
TAB_INACTIVE = "#2b2b2b"

# Size presets (label → bytes)
SIZE_PRESETS = {
    "10 MB  (~5 min, very thorough)":   10  * 1024 * 1024,
    "50 MB  (~2 min, thorough)":        50  * 1024 * 1024,
    "100 MB (~1 min, recommended)":    100  * 1024 * 1024,
    "500 MB (~30 sec, fast)":          500  * 1024 * 1024,
    "1 GB   (~15 sec, largest only)": 1024  * 1024 * 1024,
}
SIZE_MB_MAP = {
    "10 MB  (~5 min, very thorough)":   10,
    "50 MB  (~2 min, thorough)":        50,
    "100 MB (~1 min, recommended)":    100,
    "500 MB (~30 sec, fast)":          500,
    "1 GB   (~15 sec, largest only)": 1024,
}

# ─────────────────────────────────────────────────────────────────────────────
# Virtual file-list Canvas
# ─────────────────────────────────────────────────────────────────────────────

_FONT_NAME = ("Consolas", 10)
_FONT_SMALL = ("Consolas", 9)
_ROW_H = 36          # px per row
_CB_X1, _CB_Y1 = 8,  10   # checkbox top-left (relative to row top)
_CB_X2, _CB_Y2 = 22, 24   # checkbox bottom-right
_DEL_W = 32          # delete button width
_DEL_H = 22          # delete button height
_COL_NAME  = 36      # x-start of filename column
_COL_SIZE  = -230    # x from right: size column
_COL_DATE  = -130    # x from right: date column
_COL_DEL   = -8     # x from right: delete button right edge


class _VirtualFileList(tk.Frame):
    """
    A zero-overhead virtual file list backed by a single tk.Canvas.

    Memory:  O(1) widget objects regardless of row count.
    Visible: only the ~20 rows in the viewport are ever drawn.
    Interactive: checkbox toggle + per-row delete via canvas hit-testing.
    """

    def __init__(self, master, delete_cb, **kw):
        bg = CARD if CARD else "#2b2b2b"
        super().__init__(master, bg=bg, **kw)

        self._files: list = []
        self._checked: set = set()   # set of indices
        self._delete_cb = delete_cb  # callback(file_info: dict)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0,
                                 bd=0, cursor="arrow")
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._vsb = tk.Scrollbar(self, orient="vertical",
                                  command=self._canvas.yview)
        self._vsb.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._vsb.set)

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<MouseWheel>", self._on_wheel)
        self._canvas.bind("<Button-4>",   self._on_wheel)
        self._canvas.bind("<Button-5>",   self._on_wheel)
        self._canvas.bind("<Button-1>",   self._on_click)
        self._canvas.bind("<Motion>",     self._on_motion)

        self._hover_row = -1
        self._width = 800    # updated by <Configure>

    # ── Public API ────────────────────────────────────────────────────────────

    def set_files(self, files: list):
        """Replace the file list and redraw."""
        self._files   = files
        self._checked = set()
        self._hover_row = -1
        self._update_scroll_region()
        self._redraw()

    def clear(self):
        self._files   = []
        self._checked = set()
        self._canvas.delete("all")
        self._canvas.configure(scrollregion=(0, 0, 1, 1))

    def get_checked_files(self):
        """Return list of file_info dicts that are checked."""
        return [self._files[i] for i in sorted(self._checked)
                if i < len(self._files)]

    def remove_file(self, file_info: dict):
        """Remove a file from the display list (after deletion)."""
        for i, f in enumerate(self._files):
            if f["path"] == file_info["path"]:
                self._files.pop(i)
                self._checked.discard(i)
                # Renumber checked indices above i
                self._checked = {
                    idx if idx < i else idx - 1
                    for idx in self._checked
                }
                break
        self._update_scroll_region()
        self._redraw()

    # ── Geometry ─────────────────────────────────────────────────────────────

    def _update_scroll_region(self):
        total_h = max(len(self._files) * _ROW_H + 4, 1)
        self._canvas.configure(scrollregion=(0, 0,
                                             self._width or 800, total_h))

    def _visible_row_range(self):
        """Return (first_idx, last_idx_exclusive) of rows in viewport."""
        y0 = self._canvas.canvasy(0)
        y1 = self._canvas.canvasy(self._canvas.winfo_height())
        first = max(0, int(y0 / _ROW_H))
        last  = min(len(self._files), int(y1 / _ROW_H) + 2)
        return first, last

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _redraw(self, *_):
        c = self._canvas
        c.delete("row")
        if not self._files:
            c.create_text(
                self._width // 2, 80,
                text="No files found.\nTry a lower threshold.",
                fill="#666666", font=_FONT_NAME, justify="center",
                tags="row"
            )
            return
        first, last = self._visible_row_range()
        w = self._width
        for i in range(first, last):
            self._draw_row(i, w)

    def _draw_row(self, i: int, w: int):
        c = self._canvas
        f = self._files[i]
        y = i * _ROW_H
        tag = ("row", f"r{i}")

        # Row background
        if i == self._hover_row:
            bg = "#2d2d3a"
        elif i % 2 == 0:
            bg = "#1e1e1e"
        else:
            bg = "#222222"
        c.create_rectangle(0, y, w, y + _ROW_H,
                            fill=bg, outline="", tags=tag)

        # Separator line at bottom
        c.create_line(4, y + _ROW_H - 1, w - 4, y + _ROW_H - 1,
                      fill="#333333", tags=tag)

        # Checkbox
        cb_fill = ACCENT if i in self._checked else "#333333"
        cb_x1 = _CB_X1
        cb_y1 = y + _CB_Y1
        cb_x2 = _CB_X2
        cb_y2 = y + _CB_Y2
        c.create_rectangle(cb_x1, cb_y1, cb_x2, cb_y2,
                            fill=cb_fill, outline="#555555", width=1,
                            tags=tag)
        if i in self._checked:
            # tick mark
            mx = (cb_x1 + cb_x2) // 2
            my = (cb_y1 + cb_y2) // 2
            c.create_text(mx, my, text="✓", fill="white",
                          font=("Consolas", 8, "bold"), tags=tag)

        # File name (truncated)
        name = f.get("name", os.path.basename(f.get("path", "?")))
        name_max = max(20, (w - 280) // 7)  # adaptive truncation
        if len(name) > name_max:
            name = name[:name_max - 1] + "…"
        c.create_text(_COL_NAME, y + _ROW_H // 2,
                      text=name, fill="#e0e0e0", anchor="w",
                      font=_FONT_NAME, tags=tag)

        # Size
        size_x = w + _COL_SIZE
        days = f.get("days_unused")
        size_txt = f.get("size_str", "?")
        if days:
            size_txt += f" ({days}d)"
        c.create_text(size_x, y + _ROW_H // 2,
                      text=size_txt, fill="#aaaaaa", anchor="w",
                      font=_FONT_SMALL, tags=tag)

        # Date
        date_x = w + _COL_DATE
        c.create_text(date_x, y + _ROW_H // 2,
                      text=f.get("last_accessed_str", ""),
                      fill="#777777", anchor="w",
                      font=_FONT_SMALL, tags=tag)

        # Delete button
        del_x2 = w + _COL_DEL
        del_x1 = del_x2 - _DEL_W
        del_y1 = y + (_ROW_H - _DEL_H) // 2
        del_y2 = del_y1 + _DEL_H
        c.create_rectangle(del_x1, del_y1, del_x2, del_y2,
                            fill="#8B2020", outline="", tags=tag)
        c.create_text((del_x1 + del_x2) // 2, (del_y1 + del_y2) // 2,
                      text="🗑", fill="white",
                      font=("Segoe UI Emoji", 9), tags=tag)

    # ── Events ────────────────────────────────────────────────────────────────

    def _on_resize(self, event):
        self._width = event.width
        self._update_scroll_region()
        self._redraw()

    def _on_wheel(self, event):
        if event.num == 4:           # Linux scroll up
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:         # Linux scroll down
            self._canvas.yview_scroll(1, "units")
        else:                        # Windows
            self._canvas.yview_scroll(-1 * (event.delta // 120), "units")
        self._redraw()

    def _on_motion(self, event):
        cy = self._canvas.canvasy(event.y)
        hover = int(cy // _ROW_H)
        if hover < 0 or hover >= len(self._files):
            hover = -1
        if hover != self._hover_row:
            old = self._hover_row
            self._hover_row = hover
            w = self._width
            if 0 <= old < len(self._files):
                # Redraw old hover row to de-highlight
                self._canvas.delete(f"r{old}")
                self._draw_row(old, w)
            if hover >= 0:
                self._canvas.delete(f"r{hover}")
                self._draw_row(hover, w)

    def _on_click(self, event):
        cx = event.x
        cy = self._canvas.canvasy(event.y)
        row_i = int(cy // _ROW_H)
        if row_i < 0 or row_i >= len(self._files):
            return

        w = self._width
        # Checkbox hit zone
        if _CB_X1 <= cx <= _CB_X2 + 4:
            if row_i in self._checked:
                self._checked.discard(row_i)
            else:
                self._checked.add(row_i)
            self._canvas.delete(f"r{row_i}")
            self._draw_row(row_i, w)
            return

        # Delete button hit zone
        del_x2 = w + _COL_DEL
        del_x1 = del_x2 - _DEL_W
        if del_x1 <= cx <= del_x2:
            finfo = self._files[row_i]
            self._delete_cb(finfo)
            return

        # Anywhere else on the row → select the checkbox
        if row_i in self._checked:
            self._checked.discard(row_i)
        else:
            self._checked.add(row_i)
        self._canvas.delete(f"r{row_i}")
        self._draw_row(row_i, w)


# ─────────────────────────────────────────────────────────────────────────────
# Installed-apps tab rows (still CTk, but capped at 100)
# ─────────────────────────────────────────────────────────────────────────────

class _AppRow(ctk.CTkFrame):
    """A row in the Installed Apps tab."""

    def __init__(self, master, app_info: dict, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_info = app_info
        self.columnconfigure(1, weight=1)

        name = app_info["name"]
        display = name if len(name) <= 40 else name[:38] + "…"
        ctk.CTkLabel(self, text=display, font=FONTS["body"], anchor="w").grid(
            row=0, column=0, sticky="ew", padx=10)

        ctk.CTkLabel(self, text=app_info["size_str"], font=FONTS["small"],
                     text_color="#aaaaaa", width=120, anchor="e").grid(
            row=0, column=1, padx=6)

        pub = app_info.get("publisher", "")
        if len(pub) > 22:
            pub = pub[:20] + "…"
        ctk.CTkLabel(self, text=pub, font=FONTS["small"], text_color="#888888",
                     width=140, anchor="e").grid(row=0, column=2, padx=4)

        btn = ctk.CTkButton(self, text="Uninstall", width=80, height=26,
                             fg_color="#6c3483", hover_color="#9b59b6",
                             font=(FONTS["small"][0], 11),
                             command=self._uninstall)
        btn.grid(row=0, column=3, padx=(4, 8))

        sep = ctk.CTkFrame(self, height=1, fg_color="#3a3a3a")
        sep.grid(row=1, column=0, columnspan=4, sticky="ew", padx=4)

    def _uninstall(self):
        uninst = self.app_info.get("uninstall_string", "")
        if uninst:
            try:
                subprocess.Popen(uninst, shell=True)
            except Exception as exc:
                messagebox.showerror("Uninstall Error", str(exc))
        else:
            subprocess.Popen("control appwiz.cpl", shell=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main Screen
# ─────────────────────────────────────────────────────────────────────────────

class DriveAnalyzerScreen(ctk.CTkFrame):
    """Main Drive Analyzer screen."""

    def __init__(self, master, navigate_cb=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.navigate_cb = navigate_cb
        self._all_results: dict = {}
        self._scanning = False
        self.analyzer = None

        # Virtual list widgets — keyed by tab name
        self._vlists: dict[str, _VirtualFileList] = {}

        self._available_drives = get_available_drives()
        self._selected_drive = ctk.StringVar(value=self._available_drives[0])
        _default_size = "100 MB (~1 min, recommended)"
        self._selected_size_label = ctk.StringVar(value=_default_size)

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 6))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="💾 Drive Space Analyzer",
                     font=("Roboto Medium", 22, "bold")).grid(
            row=0, column=0, padx=20, pady=(14, 2), sticky="w")
        ctk.CTkLabel(header,
                     text="Select a drive and minimum file size, then scan to find space hogs.",
                     font=FONTS["body"], text_color="gray").grid(
            row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        self.btn_scan = ctk.CTkButton(
            header, text="🔍  Scan Drive", width=160, height=38,
            fg_color=ACCENT, hover_color="#145a8a",
            font=("Roboto Medium", 13, "bold"),
            command=self.start_scan)
        self.btn_scan.grid(row=0, column=2, rowspan=2, padx=20, pady=14, sticky="e")

        # Options bar
        opts = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        opts.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        opts.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(opts, text="📂  Drive:", font=FONTS["body"]).grid(
            row=0, column=0, padx=(16, 4), pady=12, sticky="w")
        self.drive_menu = ctk.CTkOptionMenu(
            opts, values=self._available_drives,
            variable=self._selected_drive,
            width=120, height=30,
            fg_color="#1a3a5c", button_color="#1f6aa5",
            font=FONTS["body"],
            command=self._on_drive_changed)
        self.drive_menu.grid(row=0, column=1, padx=(0, 20), pady=12, sticky="w")

        ctk.CTkLabel(opts, text="📏  Show files larger than:",
                     font=FONTS["body"]).grid(row=0, column=2, padx=(8, 4), pady=12, sticky="w")
        self.size_menu = ctk.CTkOptionMenu(
            opts, values=list(SIZE_PRESETS.keys()),
            variable=self._selected_size_label,
            width=270, height=30,
            fg_color="#1a3a5c", button_color="#1f6aa5",
            font=FONTS["body"],
            command=self._on_size_changed)
        self.size_menu.grid(row=0, column=3, padx=(0, 12), pady=12, sticky="w")

        self.lbl_estimate = ctk.CTkLabel(
            opts, text="⏱  Estimated scan time: ~1 minute",
            font=FONTS["small"], text_color="#888888")
        self.lbl_estimate.grid(row=0, column=4, padx=(0, 16), pady=12, sticky="e")
        self._on_size_changed("100 MB (~1 min, recommended)")

        # Drive usage bar
        usage = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        usage.grid(row=2, column=0, sticky="ew", padx=16, pady=4)
        usage.grid_columnconfigure(0, weight=1)

        self.usage_bar_canvas = ctk.CTkProgressBar(usage, height=18, corner_radius=9)
        self.usage_bar_canvas.set(0)
        self.usage_bar_canvas.grid(row=0, column=0, padx=20, pady=(14, 6), sticky="ew")

        stats = ctk.CTkFrame(usage, fg_color="transparent")
        stats.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_used  = ctk.CTkLabel(stats, text="Used: —",  font=FONTS["body"], text_color="#e74c3c")
        self.lbl_free  = ctk.CTkLabel(stats, text="Free: —",  font=FONTS["body"], text_color="#2ecc71")
        self.lbl_total = ctk.CTkLabel(stats, text="Total: —", font=FONTS["body"], text_color="#aaaaaa")
        self.lbl_pct   = ctk.CTkLabel(stats, text="— % used", font=("Roboto Medium", 13, "bold"))
        self.lbl_used.grid(row=0, column=0, sticky="w")
        self.lbl_free.grid(row=0, column=1)
        self.lbl_total.grid(row=0, column=2)
        self.lbl_pct.grid(row=0, column=3, sticky="e")

        # Progress bar (hidden until scan)
        self.progress_bar = ctk.CTkProgressBar(self, height=6, corner_radius=3,
                                               progress_color=ACCENT)
        self.progress_bar.set(0)
        self.progress_lbl = ctk.CTkLabel(self, text="", font=FONTS["small"], text_color=ACCENT)

        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0)
        tab_bar.grid(row=4, column=0, sticky="ew", padx=16, pady=(6, 0))

        self._tab_tabs: dict   = {}
        self._tab_frames: dict = {}
        self._active_tab: str  = ""

        tab_names = ["📄 Large Files", "🕰 Old & Unused", "📥 Downloads",
                     "🗂 By Type", "📦 Installed Apps"]

        for i, tname in enumerate(tab_names):
            btn = ctk.CTkButton(
                tab_bar, text=tname, width=140, height=34, corner_radius=0,
                fg_color=TAB_INACTIVE, hover_color="#3e3e3e",
                font=FONTS["body"],
                command=lambda t=tname: self._switch_tab(t))
            btn.grid(row=0, column=i, padx=(0, 1))
            self._tab_tabs[tname] = btn

        # Content area
        self.content_area = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        self.content_area.grid(row=5, column=0, sticky="nsew", padx=16, pady=(0, 6))
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        self._build_tab_frames()

        # Status bar
        status_bar = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        status_bar.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 16))
        status_bar.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            status_bar,
            text="Select a drive & size threshold above, then click 'Scan Drive'.",
            font=FONTS["body"], text_color="gray")
        self.status_lbl.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.btn_delete_sel = ctk.CTkButton(
            status_bar, text="🗑  Delete Selected", width=160, height=34,
            fg_color=DANGER, hover_color="#a02020",
            font=("Roboto Medium", 12, "bold"),
            state="disabled",
            command=self.delete_selected)
        self.btn_delete_sel.grid(row=0, column=1, padx=20, pady=10)

        self._switch_tab("📄 Large Files")

    # ── Options callbacks ─────────────────────────────────────────────────────

    def _on_drive_changed(self, value):
        self.status_lbl.configure(
            text=f"Drive {value} selected. Click 'Scan Drive' to analyze.",
            text_color="gray")

    def _on_size_changed(self, value):
        mb = SIZE_MB_MAP.get(value, 100)
        est = estimate_scan_time(mb)
        size_part = value.split("(")[0].strip()
        self.lbl_estimate.configure(
            text=f"⏱  {size_part} threshold  →  {est}",
            text_color="#22aa55")

    # ── Tab construction ──────────────────────────────────────────────────────

    def _build_tab_frames(self):
        """
        File-list tabs get a _VirtualFileList (canvas-based, zero-widget-per-row).
        Non-file tabs get a CTkScrollableFrame for their card/widget content.
        """
        file_tabs = ["📄 Large Files", "🕰 Old & Unused", "📥 Downloads"]
        other_tabs = ["🗂 By Type", "📦 Installed Apps"]

        for tname in file_tabs:
            vl = _VirtualFileList(self.content_area,
                                  delete_cb=self._delete_file_entry)
            vl.grid(row=0, column=0, sticky="nsew")
            vl.grid_remove()
            self._tab_frames[tname] = vl
            self._vlists[tname] = vl

        for tname in other_tabs:
            sf = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
            sf.grid(row=0, column=0, sticky="nsew")
            sf.grid_remove()
            self._tab_frames[tname] = sf

    # ── Tab switching ─────────────────────────────────────────────────────────

    def _switch_tab(self, tab_name: str):
        if self._active_tab:
            self._tab_tabs[self._active_tab].configure(fg_color=TAB_INACTIVE)
            self._tab_frames[self._active_tab].grid_remove()
        self._active_tab = tab_name
        self._tab_tabs[tab_name].configure(fg_color=TAB_ACTIVE)
        self._tab_frames[tab_name].grid()

    # ── Scan ──────────────────────────────────────────────────────────────────

    def start_scan(self):
        if self._scanning:
            return

        chosen_drive = self._selected_drive.get()
        size_label   = self._selected_size_label.get()
        min_bytes    = SIZE_PRESETS.get(size_label, 100 * 1024 * 1024)

        self.analyzer   = DiskAnalyzer(chosen_drive)
        self._scanning  = True

        self.btn_scan.configure(state="disabled", text="⏳  Scanning…")
        self.btn_delete_sel.configure(state="disabled")
        self._clear_all_tabs()

        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 0))
        self.progress_lbl.grid(row=3, column=0, sticky="e", padx=16)
        self.progress_bar.set(0)
        self.status_lbl.configure(text="Scanning…", text_color=ACCENT)

        self.analyzer.run_full_scan(
            progress_cb=self._on_progress,
            done_cb=self._on_scan_done,
            min_size_bytes=min_bytes,
        )

    def _on_progress(self, pct: int, text: str):
        self.after(0, self._apply_progress, pct, text)

    def _apply_progress(self, pct: int, text: str):
        try:
            self.progress_bar.set(pct / 100)
            self.progress_lbl.configure(text=text)
            self.status_lbl.configure(text=text)
        except Exception:
            pass

    def _on_scan_done(self, results: dict):
        self._all_results = results
        self.after(0, self._populate_start, results)

    # ── Populate ──────────────────────────────────────────────────────────────

    def _populate_start(self, results: dict):
        """Update drive bar and populate all tabs. Virtual lists are instant."""
        summary = results.get("summary", {})
        pct = summary.get("percent", 0) / 100
        bar_color = SUCCESS if pct < 0.7 else (WARNING if pct < 0.85 else DANGER)
        self.usage_bar_canvas.configure(progress_color=bar_color)
        self.usage_bar_canvas.set(pct)
        self.lbl_used.configure(text="Used: {}".format(summary.get("used_str", "—")))
        self.lbl_free.configure(text="Free: {}".format(summary.get("free_str", "—")))
        self.lbl_total.configure(text="Total: {}".format(summary.get("total_str", "—")))
        self.lbl_pct.configure(text="{:.1f}% used".format(summary.get("percent", 0)))

        # Virtual lists: set_files() is O(1) — no widgets created
        self._vlists["📄 Large Files"].set_files(results.get("large_files", []))
        self._vlists["🕰 Old & Unused"].set_files(results.get("old_files",   []))
        self._vlists["📥 Downloads"].set_files(results.get("downloads",   []))

        # CTk tabs: populate with short delay between each to avoid starvation
        def _step_apps(on_done):
            self._populate_apps_tab(results.get("apps", []))
            self.after(10, on_done)

        def _step_cat(on_done):
            self._populate_category_tab(results.get("by_category", {}))
            self.after(10, on_done)

        self.after(20, lambda: _step_cat(lambda: _step_apps(
            lambda: self._populate_finish(results))))

    def _populate_finish(self, results: dict):
        total_large = sum(f["size_bytes"] for f in results.get("large_files", []))
        total_old   = sum(f["size_bytes"] for f in results.get("old_files",   []))
        if results.get("error"):
            status = "Scan finished (partial): {}".format(results["error"])
            color  = WARNING
        else:
            status = ("Scan complete!  {} in large files  •  {} in old/unused files  "
                      "•  {} files found").format(
                _fmt_size(total_large), _fmt_size(total_old),
                len(results.get("large_files", [])))
            color  = SUCCESS
        self.status_lbl.configure(text=status, text_color=color)
        self.btn_scan.configure(state="normal", text="🔍  Scan Drive")
        self.btn_delete_sel.configure(state="normal")
        self.progress_bar.grid_remove()
        self.progress_lbl.grid_remove()
        self._scanning = False

    # ── Non-file tab population ───────────────────────────────────────────────

    def _populate_category_tab(self, by_cat: dict):
        frame = self._tab_frames["🗂 By Type"]
        if not by_cat:
            ctk.CTkLabel(frame, text="Run a scan to see file category breakdown.",
                         font=FONTS["body"], text_color="gray").pack(pady=30)
            return

        sorted_cats = sorted(by_cat.items(), key=lambda x: x[1]["size_bytes"], reverse=True)
        total_bytes = sum(v["size_bytes"] for _, v in sorted_cats) or 1

        EMOJI = {"Videos": "🎬", "Images": "🖼", "Documents": "📄",
                 "Installers": "📦", "Audio": "🎵", "Code": "💻", "Others": "📁"}

        for cat, data in sorted_cats:
            if data["file_count"] == 0:
                continue
            pct = data["size_bytes"] / total_bytes
            card = ctk.CTkFrame(frame, fg_color=SECONDARY, corner_radius=10)
            card.pack(fill="x", padx=10, pady=5)
            card.grid_columnconfigure(1, weight=1)

            icon = EMOJI.get(cat, "📁")
            ctk.CTkLabel(card, text=f"{icon}  {cat}",
                         font=FONTS["subheader"], anchor="w"
                         ).grid(row=0, column=0, padx=16, pady=(10, 2), sticky="w")
            ctk.CTkLabel(card,
                         text="{} • {:,} files".format(data["size_str"], data["file_count"]),
                         font=FONTS["body"], text_color="#aaaaaa", anchor="e"
                         ).grid(row=0, column=2, padx=16, pady=(10, 2), sticky="e")
            bar = ctk.CTkProgressBar(card, height=10, corner_radius=5,
                                     progress_color=ACCENT)
            bar.set(pct)
            bar.grid(row=1, column=0, columnspan=3, padx=16, pady=(2, 12), sticky="ew")

    def _populate_apps_tab(self, apps: list):
        frame = self._tab_frames["📦 Installed Apps"]
        if not apps:
            ctk.CTkLabel(frame, text="No applications found.",
                         font=FONTS["body"], text_color="gray").pack(pady=30)
            return

        # Cap at 100 app rows (registry gives 100-300 apps — 100 is plenty)
        display = apps[:100]
        hdr = ctk.CTkFrame(frame, fg_color="#222222", corner_radius=6)
        hdr.pack(fill="x", padx=4, pady=(4, 0))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="App Name",  font=FONTS["small"], anchor="w").grid(
            row=0, column=0, sticky="ew", padx=10)
        ctk.CTkLabel(hdr, text="Size",      font=FONTS["small"], width=120, anchor="e").grid(
            row=0, column=1, padx=6)
        ctk.CTkLabel(hdr, text="Publisher", font=FONTS["small"], width=140, anchor="e").grid(
            row=0, column=2, padx=4)
        ctk.CTkLabel(hdr, text="",          font=FONTS["small"], width=88).grid(
            row=0, column=3)

        for app in display:
            _AppRow(frame, app).pack(fill="x", padx=4, pady=1)

        if len(apps) > 100:
            ctk.CTkLabel(frame,
                         text="… {} more apps installed".format(len(apps) - 100),
                         font=FONTS["small"], text_color="#666666").pack(pady=4)

    # ── Clear ─────────────────────────────────────────────────────────────────

    def _clear_all_tabs(self):
        # Virtual lists
        for vl in self._vlists.values():
            vl.clear()
        # CTk scrollable frames (By Type, Installed Apps)
        for tname in ["🗂 By Type", "📦 Installed Apps"]:
            frame = self._tab_frames[tname]
            for w in frame.winfo_children():
                w.destroy()

    # ── Delete ────────────────────────────────────────────────────────────────

    def _delete_file_entry(self, file_info: dict):
        """Called when user clicks 🗑 on a canvas row."""
        fname = file_info.get("name", os.path.basename(file_info.get("path", "?")))
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Permanently delete:\n\n{fname}\n({file_info.get('size_str', '?')})?\n\n"
            "This cannot be undone.",
            icon="warning")
        if not confirm:
            return
        threading.Thread(
            target=self._do_delete_entry,
            args=(file_info,), daemon=True).start()

    def _do_delete_entry(self, file_info: dict):
        if self.analyzer is None:
            return
        ok, msg = self.analyzer.delete_file(file_info["path"])
        if ok:
            # Remove from all virtual lists that contain this file
            def _remove():
                for vl in self._vlists.values():
                    vl.remove_file(file_info)
                self.status_lbl.configure(
                    text="✅ " + msg, text_color=SUCCESS)
            self.after(0, _remove)
            self.after(500, self._refresh_usage_bar)
        else:
            self.after(0, lambda: messagebox.showerror(
                "Delete Failed",
                f"Could not delete {file_info.get('name', '?')}.\n\n{msg}"))

    def delete_selected(self):
        """Delete all checked rows across all virtual file-list tabs."""
        checked = []
        for vl in self._vlists.values():
            checked.extend(vl.get_checked_files())
        # Deduplicate by path
        seen = set()
        unique = [f for f in checked
                  if f["path"] not in seen and not seen.add(f["path"])]
        if not unique:
            self.status_lbl.configure(
                text="No files selected. Click a row or its checkbox to select.",
                text_color=WARNING)
            return
        total_size = sum(f["size_bytes"] for f in unique)
        confirm = messagebox.askyesno(
            "Confirm Bulk Delete",
            f"Delete {len(unique)} file(s) totalling {_fmt_size(total_size)}?\n"
            "This cannot be undone.",
            icon="warning")
        if not confirm:
            return
        threading.Thread(
            target=self._do_bulk_delete, args=(unique,), daemon=True).start()

    def _do_bulk_delete(self, files: list):
        if self.analyzer is None:
            return
        freed = 0
        failed = []
        for finfo in files:
            ok, msg = self.analyzer.delete_file(finfo["path"])
            if ok:
                freed += finfo["size_bytes"]
                fi = finfo  # capture
                self.after(0, lambda f=fi: [vl.remove_file(f)
                                            for vl in self._vlists.values()])
            else:
                failed.append(f"{finfo.get('name', '?')}: {msg}")

        result = "✅ Freed {}".format(_fmt_size(freed))
        if failed:
            result += "  ({} failed)".format(len(failed))
            self.after(0, lambda: messagebox.showerror(
                "Deletion Errors",
                "Some files could not be deleted:\n\n" + "\n".join(failed[:8])))

        color = SUCCESS if not failed else WARNING
        self.after(0, lambda: self.status_lbl.configure(text=result, text_color=color))
        self.after(500, self._refresh_usage_bar)

    def _refresh_usage_bar(self):
        if self.analyzer is None:
            return
        s = self.analyzer.get_drive_summary()
        pct = s.get("percent", 0) / 100
        bar_color = SUCCESS if pct < 0.7 else (WARNING if pct < 0.85 else DANGER)
        self.usage_bar_canvas.configure(progress_color=bar_color)
        self.usage_bar_canvas.set(pct)
        self.lbl_used.configure(text="Used: {}".format(s.get("used_str", "—")))
        self.lbl_free.configure(text="Free: {}".format(s.get("free_str", "—")))
        self.lbl_pct.configure(text="{:.1f}% used".format(s.get("percent", 0)))
