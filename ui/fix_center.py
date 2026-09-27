"""
fix_center.py
-------------
Fix Center screen — browse and search step-by-step fixes for common
Windows problems. Replaces Googling error messages.
"""

import customtkinter as ctk
from ui.styles import THEME, FONTS
from core.fix_library import get_all_symptom_fixes, get_fix_for_symptom, search_fixes


class FixCenterScreen(ctk.CTkFrame):
    """Browse and search common Windows problem fix steps."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=THEME["card_color"], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="🔧  Fix Center",
            font=("Roboto Medium", 22),
        ).grid(row=0, column=0, padx=20, pady=(14, 2), sticky="w")

        ctk.CTkLabel(
            header,
            text="Step-by-step fixes for common Windows problems — no Googling required.",
            font=FONTS["body"],
            text_color="#888888",
        ).grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        # Search bar
        search_frame = ctk.CTkFrame(self, fg_color=THEME["card_color"], corner_radius=12)
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        search_frame.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        inner.grid(row=0, column=0, padx=16, pady=12, sticky="ew")
        inner.grid_columnconfigure(0, weight=1)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            inner,
            textvariable=self.search_var,
            placeholder_text="🔍  Search: 'blue screen', 'printer', 'slow', 'no sound', 'WiFi'…",
            height=38,
            font=FONTS["body"],
        )
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self._do_search())

        ctk.CTkButton(
            inner,
            text="Search",
            width=90,
            height=38,
            fg_color=THEME["accent_color"],
            hover_color="#145a8a",
            command=self._do_search,
        ).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(
            inner,
            text="Clear",
            width=60,
            height=38,
            fg_color="#3b3b3b",
            hover_color="#444444",
            command=self._clear_search,
        ).grid(row=0, column=2, padx=(6, 0))

        # Scrollable content
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.scroll.grid_columnconfigure(0, weight=1)

        # Default view: category browse
        self._show_categories()

    # ── Category Browse ───────────────────────────────────────────────────────

    def _show_categories(self):
        self._clear()
        categories = get_all_symptom_fixes()
        row = 0
        for category, items in categories.items():
            # Category label
            hdr = ctk.CTkFrame(self.scroll, fg_color="#1a2535", corner_radius=8)
            hdr.grid(row=row, column=0, sticky="ew", padx=4, pady=(12, 3))
            ctk.CTkLabel(
                hdr,
                text=f"  {category}",
                font=("Roboto Medium", 14),
                text_color="#5dade2",
                anchor="w",
            ).pack(fill="x", padx=10, pady=6)
            row += 1

            for key, label in items:
                self._add_browse_button(key, label, row)
                row += 1

        # Footer note
        ctk.CTkLabel(
            self.scroll,
            text="ℹ️  More fixes are available through the AI Chatbot for complex or unusual problems.",
            font=FONTS["small"],
            text_color="#444444",
            wraplength=680,
            justify="left",
        ).grid(row=row, column=0, padx=10, pady=(16, 4), sticky="w")

    def _add_browse_button(self, key: str, label: str, row: int):
        frame = ctk.CTkFrame(self.scroll, fg_color=THEME["card_color"], corner_radius=8)
        frame.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            frame,
            text=f"  🔧  {label}",
            fg_color="transparent",
            hover_color="#2d2d3a",
            font=FONTS["body"],
            anchor="w",
            height=40,
            command=lambda k=key, l=label: self._show_fix_detail(k),
        ).grid(row=0, column=0, sticky="ew", padx=4, pady=2)

        ctk.CTkLabel(
            frame,
            text="▶",
            font=FONTS["small"],
            text_color="#555555",
        ).grid(row=0, column=1, padx=(0, 14))

    # ── Detail View ───────────────────────────────────────────────────────────

    def _show_fix_detail(self, key: str):
        result = get_fix_for_symptom(key)
        if not result:
            return
        title, steps = result
        self._clear()
        self._add_back_button()
        self._render_fix_card(title, steps, row=1)

    # ── Search ────────────────────────────────────────────────────────────────

    def _do_search(self):
        query = self.search_var.get().strip()
        if not query:
            self._show_categories()
            return
        results = search_fixes(query)
        self._clear()

        if not results:
            ctk.CTkLabel(
                self.scroll,
                text=f"❌  No fix found for '{query}'.\n\nTry the AI Chatbot for more specific or unusual problems.",
                font=FONTS["body"],
                text_color="#666666",
                justify="center",
            ).grid(row=0, column=0, pady=40)
            self._add_back_button(row=1)
            return

        ctk.CTkLabel(
            self.scroll,
            text=f"🔍  Found {len(results)} result(s) for '{query}':",
            font=("Roboto Medium", 13),
            text_color="#aaaaaa",
            anchor="w",
        ).grid(row=0, column=0, padx=8, pady=(6, 4), sticky="w")

        for i, (title, steps) in enumerate(results):
            self._render_fix_card(title, steps, row=i + 1)

        self._add_back_button(row=len(results) + 2)

    def _clear_search(self):
        self.search_var.set("")
        self._show_categories()

    # ── Fix Card Renderer ─────────────────────────────────────────────────────

    def _render_fix_card(self, title: str, steps: list, row: int):
        """Renders a complete numbered-steps card."""
        card = ctk.CTkFrame(self.scroll, fg_color=THEME["card_color"], corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=4, pady=6)
        card.grid_columnconfigure(0, weight=1)

        # Title bar
        title_bar = ctk.CTkFrame(card, fg_color="#1a2d40", corner_radius=8)
        title_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            title_bar,
            text=f"🔧  {title}",
            font=("Roboto Medium", 14),
            anchor="w",
            wraplength=680,
        ).pack(fill="x", padx=14, pady=(10, 8))

        # Numbered steps
        for i, step in enumerate(steps, start=1):
            step_row = ctk.CTkFrame(card, fg_color="transparent")
            step_row.grid(row=i, column=0, sticky="ew", padx=12, pady=(2, 2))
            step_row.grid_columnconfigure(1, weight=1)

            # Number badge
            ctk.CTkLabel(
                step_row,
                text=f"{i}",
                width=28,
                height=28,
                fg_color=THEME["accent_color"],
                font=("Roboto Medium", 11, "bold"),
                corner_radius=14,
                text_color="white",
            ).grid(row=0, column=0, sticky="nw", pady=(3, 0))

            # Step text
            ctk.CTkLabel(
                step_row,
                text=step,
                font=FONTS["body"],
                text_color="#dddddd",
                anchor="w",
                justify="left",
                wraplength=620,
            ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        # Bottom actions
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=len(steps) + 1, column=0, sticky="e",
                     padx=12, pady=(4, 10))

        copy_btn = ctk.CTkButton(
            actions,
            text="📋  Copy All Steps",
            width=140,
            height=28,
            fg_color="#2d2d3a",
            hover_color="#3d3d4a",
            font=FONTS["small"],
            command=lambda t=title, s=steps: self._copy_steps(t, s, copy_btn),
        )
        copy_btn.pack(side="right")

    def _copy_steps(self, title: str, steps: list, btn):
        text = f"{title}\n\n" + "\n".join(
            f"Step {i}: {s}" for i, s in enumerate(steps, 1)
        )
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            btn.configure(text="✅  Copied!")
            self.after(2000, lambda: btn.configure(text="📋  Copy All Steps"))
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _add_back_button(self, row: int = 0):
        ctk.CTkButton(
            self.scroll,
            text="←  Back to all fixes",
            fg_color="transparent",
            hover_color="#2d2d3a",
            font=FONTS["body"],
            anchor="w",
            width=180,
            command=self._show_categories,
        ).grid(row=row, column=0, padx=4, pady=(4, 8), sticky="w")

    def _clear(self):
        for w in self.scroll.winfo_children():
            w.destroy()
