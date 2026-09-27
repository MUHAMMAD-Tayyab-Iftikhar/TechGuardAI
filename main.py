import customtkinter as ctk
from ui.auth_screen import AuthScreen
from ui.home_screen import HomeScreen
from ui.dashboard import DashboardFrame
from ui.chatbot_ui import ChatbotFrame
from ui.cleanup_center import CleanupCenter
from ui.performance_center import PerformanceCenter
from ui.security_center import SecurityCenter
from ui.fixes_center import FixesCenter
from core.system_monitor import SystemMonitor
from core.event_tracker import EventTracker
from ai.health_analyzer import HealthAnalyzer
from ai.chatbot_engine import ChatbotEngine
from ai.bot_brain import TechGuardBrain
from utils import mode_manager

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class TechGuardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TechGuardAI")
        self.geometry("1200x800")

        # Single full-window column — used by both auth & home screens
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Logged-in user (set after auth succeeds)
        self.current_user: str | None = None

        # ── Initialize backend ────────────────────────────────────────────
        self.monitor    = SystemMonitor()
        self.analyzer   = HealthAnalyzer()
        self.bot_brain  = TechGuardBrain()
        self.bot_engine = ChatbotEngine(self.monitor)

        self.event_tracker = EventTracker(db=self.bot_brain.db)
        self.event_tracker.start()

        # ── Show AuthScreen first (fullscreen, no sidebar/chatbot) ────────
        self._auth_screen = AuthScreen(self, on_success=self._on_auth_success)
        self._auth_screen.grid(row=0, column=0, sticky="nsew")

        # ── Pre-build home + main layout silently in background ───────────
        # Built now so there is zero lag when auth completes.
        self.home = HomeScreen(self, navigate_cb=self._enter_app)
        # (not gridded yet)
        self._build_main_layout()
        # (no content frames gridded yet)

    # ─────────────────────────────────────────────────────────────────────────
    # Build the full sidebar + content + chatbot layout (all hidden at start)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_main_layout(self):
        # ── Sidebar ───────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=210, fg_color="#0d1b2a", corner_radius=0)
        self.sidebar.grid_propagate(False)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="#16213e", corner_radius=0)
        logo_frame.pack(fill="x")
        ctk.CTkLabel(
            logo_frame,
            text="\u26a1 TechGuard",
            font=("Roboto Medium", 18, "bold"),
            text_color="#5dade2",
        ).pack(pady=(18, 2))


        ctk.CTkFrame(self.sidebar, height=1, fg_color="#1a2f45").pack(fill="x")

        _NAV = dict(
            fg_color="transparent",
            hover_color="#1a2f45",
            anchor="w",
            font=("Roboto Medium", 13),
            text_color="#90b4ce",
            height=44,
            corner_radius=8,
        )
        self._nav_btns = {}

        self._nav_btns["home"] = ctk.CTkButton(
            self.sidebar, text="  \U0001f3e0   Home",
            command=self._go_home, **_NAV)
        self._nav_btns["home"].pack(fill="x", padx=10, pady=(12, 2))

        ctk.CTkFrame(self.sidebar, height=1, fg_color="#1a2f45").pack(fill="x", padx=10, pady=4)

        nav_items = [
            ("dashboard",   "  \U0001f4ca   Dashboard"),
            ("cleanup",     "  \U0001f9f9   Cleanup Center"),
            ("performance", "  \U0001f680   Performance"),
            ("security",    "  \U0001f6e1\ufe0f   Security"),
            ("fixes",       "  \U0001f6e0\ufe0f   Fixes & Updates"),
        ]
        for key, label in nav_items:
            self._nav_btns[key] = ctk.CTkButton(
                self.sidebar, text=label,
                command=lambda k=key: self.show_frame(k), **_NAV)
            self._nav_btns[key].pack(fill="x", padx=10, pady=2)

        # Bottom section separator
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#1a2f45").pack(
            side="bottom", fill="x", padx=10, pady=(0, 4))

        # ── Logout button (danger red, very bottom) ───────────────────────
        ctk.CTkButton(
            self.sidebar,
            text="  🔐   Logout",
            fg_color="#3b1010",
            hover_color="#5c1a1a",
            text_color="#f87171",
            font=("Roboto Medium", 13),
            height=40,
            corner_radius=8,
            anchor="w",
            command=self.logout,
        ).pack(side="bottom", fill="x", padx=10, pady=(0, 8))

        # ── Mode toggle ───────────────────────────────────────────────────
        self.mode_btn = ctk.CTkButton(
            self.sidebar,
            text=self._mode_btn_text(),
            fg_color=self._mode_btn_color(),
            hover_color=self._mode_btn_hover(),
            font=("Roboto Medium", 12),
            height=38,
            corner_radius=8,
            command=self._toggle_mode,
        )
        self.mode_btn.pack(side="bottom", pady=(0, 6), padx=12, fill="x")



        # ── Chatbot ───────────────────────────────────────────────────────
        self.chatbot = ChatbotFrame(
            self, self.bot_engine, self.bot_brain, self.monitor,
            navigate_cb=self.show_frame,
        )
        # Prevent chatbot's internal content from pushing its grid column wider
        self.chatbot.grid_propagate(False)
        # (not gridded yet)

        # ── Content screens ───────────────────────────────────────────────
        self.frames = {}
        self.frames["dashboard"]   = DashboardFrame(self, self.monitor, self.analyzer, self.chatbot)
        self.frames["cleanup"]     = CleanupCenter(self)
        self.frames["performance"] = PerformanceCenter(self)
        self.frames["security"]    = SecurityCenter(self)
        self.frames["fixes"]       = FixesCenter(self)
        # Prevent each content frame from resizing its grid column
        for frame in self.frames.values():
            frame.grid_propagate(False)
        # (none gridded yet)

    # ─────────────────────────────────────────────────────────────────────────
    # Authentication gate
    # ─────────────────────────────────────────────────────────────────────────

    def _on_auth_success(self, email: str):
        """Called by AuthScreen after a confirmed login."""
        self.current_user = email
        print(f"[TechGuardAI] Logged in as: {email}")

        # Destroy the auth screen cleanly
        self._auth_screen.grid_forget()
        self._auth_screen.destroy()

        # Restore single-column grid (may have been changed if logging in again)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)

        # Show the home screen fullscreen
        self.home.grid(row=0, column=0, sticky="nsew")

    # ─────────────────────────────────────────────────────────────────────────
    # Logout
    # ─────────────────────────────────────────────────────────────────────────

    def logout(self):
        """Confirm, tear down the entire session, and return to AuthScreen."""
        import tkinter.messagebox as mb
        if not mb.askyesno(
            "Logout",
            "Are you sure you want to logout?",
            icon="warning",
        ):
            return

        print(f"[TechGuardAI] Logged out: {self.current_user}")
        self.current_user = None

        # ── 1. Hide & destroy ALL main-layout widgets ─────────────────────
        # Content frames
        for frame in self.frames.values():
            frame.grid_forget()
            frame.destroy()
        self.frames.clear()

        # Sidebar
        self.sidebar.grid_forget()
        self.sidebar.destroy()

        # Chatbot
        self.chatbot.grid_forget()
        self.chatbot.destroy()

        # Home screen
        self.home.grid_forget()
        self.home.destroy()

        # ── 2. Reset grid to single full-window column ────────────────────
        self.grid_columnconfigure(0, weight=1, minsize=0)
        self.grid_columnconfigure(1, weight=0, minsize=0)
        self.grid_columnconfigure(2, weight=0, minsize=0)

        # ── 3. Rebuild home + main layout fresh (for next login) ──────────
        self.home = HomeScreen(self, navigate_cb=self._enter_app)
        self._build_main_layout()

        # ── 4. Show a fresh AuthScreen ────────────────────────────────────
        self._auth_screen = AuthScreen(self, on_success=self._on_auth_success)
        self._auth_screen.grid(row=0, column=0, sticky="nsew")

    # ─────────────────────────────────────────────────────────────────────────
    # Called when user picks a section from the home screen
    # ─────────────────────────────────────────────────────────────────────────

    def _enter_app(self, section: str):
        """Hide home screen and reveal the pre-built main layout all at once."""
        # Remove home screen
        self.home.grid_forget()

        # ── Pin all three columns to fixed roles so nothing shifts on swap ──
        # col 0: sidebar — fixed width, never grows
        self.grid_columnconfigure(0, weight=0, minsize=210)
        # col 1: content area — takes ALL remaining space
        self.grid_columnconfigure(1, weight=1, minsize=0)
        # col 2: chatbot — fixed width, NEVER changes regardless of content
        self.grid_columnconfigure(2, weight=0, minsize=310)

        # Place sidebar, chatbot and content in one pass — all pre-built so instant
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.chatbot.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)
        self.frames[section].grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Highlight the active nav button
        _ACTIVE   = {"fg_color": "#1a3a5c", "text_color": "#ffffff"}
        _INACTIVE = {"fg_color": "transparent", "text_color": "#90b4ce"}
        for key, btn in self._nav_btns.items():
            btn.configure(**(_ACTIVE if key == section else _INACTIVE))

    # ─────────────────────────────────────────────────────────────────────────
    # Go back to the fullscreen home screen
    # ─────────────────────────────────────────────────────────────────────────

    def _go_home(self):
        for frame in self.frames.values():
            frame.grid_forget()
        self.sidebar.grid_forget()
        self.chatbot.grid_forget()

        # Clear ALL column constraints so home screen fills the full window
        self.grid_columnconfigure(0, weight=1, minsize=0)
        self.grid_columnconfigure(1, weight=0, minsize=0)
        self.grid_columnconfigure(2, weight=0, minsize=0)

        self.home.grid(row=0, column=0, sticky="nsew")

    # ─────────────────────────────────────────────────────────────────────────
    # Navigate between main-layout screens
    # ─────────────────────────────────────────────────────────────────────────

    def show_frame(self, name: str):
        # Hide all content frames
        for frame in self.frames.values():
            frame.grid_forget()

        # Re-affirm stable column sizes before placing the new frame
        # (guards against any geometry recalc that could shift the chatbot)
        self.grid_columnconfigure(0, weight=0, minsize=210)
        self.grid_columnconfigure(1, weight=1, minsize=0)
        self.grid_columnconfigure(2, weight=0, minsize=310)

        # Show the requested frame
        self.frames[name].grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Highlight active nav button
        _ACTIVE   = {"fg_color": "#1a3a5c", "text_color": "#ffffff"}
        _INACTIVE = {"fg_color": "transparent", "text_color": "#90b4ce"}
        for key, btn in self._nav_btns.items():
            btn.configure(**(_ACTIVE if key == name else _INACTIVE))

    # ─────────────────────────────────────────────────────────────────────────
    # Mode helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _mode_btn_text(self) -> str:
        return "\U0001f393  Beginner Mode" if mode_manager.is_beginner() else "\u2699\ufe0f  Expert Mode"

    def _mode_btn_color(self) -> str:
        return "#2d5a27" if mode_manager.is_beginner() else "#1a3a5c"

    def _mode_btn_hover(self) -> str:
        return "#3d7a37" if mode_manager.is_beginner() else "#2a4a7c"

    def _toggle_mode(self):
        mode_manager.toggle()
        self.mode_btn.configure(
            text=self._mode_btn_text(),
            fg_color=self._mode_btn_color(),
            hover_color=self._mode_btn_hover(),
        )


if __name__ == "__main__":
    app = TechGuardApp()
    app.mainloop()