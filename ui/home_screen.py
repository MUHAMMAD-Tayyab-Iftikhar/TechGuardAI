"""
home_screen.py
--------------
Welcome / Landing screen for TechGuardAI.
Shows five main feature cards so the user can jump straight into any section.
"""

import customtkinter as ctk

# ── Palette ────────────────────────────────────────────────────────────────────
_BG        = "#0f172a"
_CARD_BG   = "#1e293b"
_CARD_BORD = "#334155"

_ACCENTS = {
    "dashboard":   {"color": "#38bdf8", "btn": "#0369a1", "btn_hover": "#0284c7"},
    "cleanup":     {"color": "#34d399", "btn": "#047857", "btn_hover": "#059669"},
    "performance": {"color": "#fbbf24", "btn": "#92400e", "btn_hover": "#b45309"},
    "security":    {"color": "#f87171", "btn": "#991b1b", "btn_hover": "#b91c1c"},
    "fixes":       {"color": "#a78bfa", "btn": "#5b21b6", "btn_hover": "#6d28d9"},
}

_CARDS = [
    {
        "key":   "dashboard",
        "icon":  "📊",
        "title": "Dashboard",
        "desc":  "Live CPU, RAM, disk & network stats with AI-powered health insights.",
    },
    {
        "key":   "cleanup",
        "icon":  "🧹",
        "title": "Cleanup Center",
        "desc":  "Remove junk files & temp data. Reclaim gigabytes of storage in seconds.",
    },
    {
        "key":   "performance",
        "icon":  "🚀",
        "title": "Performance",
        "desc":  "See which apps drain your RAM and control what launches at startup.",
    },
    {
        "key":   "security",
        "icon":  "🛡️",
        "title": "Security",
        "desc":  "Scan for suspicious processes and control network telemetry settings.",
    },
    {
        "key":   "fixes",
        "icon":  "🛠️",
        "title": "Fixes & Updates",
        "desc":  "Health diagnostics, step-by-step Windows fixes, and app updates.",
    },
]


class HomeScreen(ctk.CTkFrame):
    """Fullscreen welcome screen — no sidebar, no chatbot."""

    def __init__(self, master, navigate_cb):
        super().__init__(master, fg_color=_BG)
        self._navigate = navigate_cb

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_cards()

    # ── Header ─────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=80, pady=(26, 4))

        ctk.CTkLabel(
            hdr,
            text="⚡  TechGuard AI",
            font=("Roboto Medium", 30, "bold"),
            text_color="#e2e8f0",
        ).pack()

        ctk.CTkLabel(
            hdr,
            text="Your intelligent PC health companion — pick a section to get started",
            font=("Roboto", 12),
            text_color="#64748b",
        ).pack(pady=(4, 0))

        ctk.CTkFrame(hdr, height=1, fg_color="#1e293b").pack(fill="x", pady=(12, 0))

    # ── Cards ─────────────────────────────────────────────────────────────────

    def _build_cards(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=1, column=0, sticky="nsew", padx=80, pady=(6, 22))

        # Top row: 3 cards
        top = ctk.CTkFrame(outer, fg_color="transparent")
        top.pack(fill="both", expand=True, pady=(0, 10))
        top.grid_columnconfigure((0, 1, 2), weight=1)
        top.grid_rowconfigure(0, weight=1)

        for col_idx, card_def in enumerate(_CARDS[:3]):
            self._make_card(top, card_def, row=0, col=col_idx)

        # Bottom row: 2 cards
        bot = ctk.CTkFrame(outer, fg_color="transparent")
        bot.pack(fill="both", expand=True)
        bot.grid_columnconfigure((0, 1), weight=1)
        bot.grid_rowconfigure(0, weight=1)

        for col_idx, card_def in enumerate(_CARDS[3:]):
            self._make_card(bot, card_def, row=0, col=col_idx)

    def _make_card(self, parent, card_def, row, col):
        key   = card_def["key"]
        icon  = card_def["icon"]
        title = card_def["title"]
        desc  = card_def["desc"]
        ac    = _ACCENTS[key]

        card = ctk.CTkFrame(
            parent,
            fg_color=_CARD_BG,
            corner_radius=14,
            border_width=1,
            border_color=_CARD_BORD,
            cursor="hand2",
        )
        card.grid(row=row, column=col, padx=10, pady=6, sticky="nsew")

        # Coloured top stripe
        ctk.CTkFrame(
            card, height=4, fg_color=ac["color"], corner_radius=0
        ).pack(fill="x")

        # Large centred icon
        ctk.CTkLabel(
            card,
            text=icon,
            font=("Segoe UI Emoji", 42),
        ).pack(pady=(20, 8))

        # Large title
        ctk.CTkLabel(
            card,
            text=title,
            font=("Roboto Medium", 22, "bold"),
            text_color=ac["color"],
        ).pack()

        # Description
        ctk.CTkLabel(
            card,
            text=desc,
            font=("Roboto", 12),
            text_color="#94a3b8",
            wraplength=240,
            justify="center",
        ).pack(pady=(8, 0))

        # Open button
        ctk.CTkButton(
            card,
            text="Open  →",
            fg_color=ac["btn"],
            hover_color=ac["btn_hover"],
            font=("Roboto Medium", 13, "bold"),
            height=36,
            corner_radius=9,
            command=lambda k=key: self._navigate(k),
        ).pack(pady=(16, 22), padx=24, fill="x")

        # Whole-card click
        card.bind("<Button-1>", lambda e, k=key: self._navigate(k))
