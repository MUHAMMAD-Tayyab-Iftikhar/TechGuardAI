import customtkinter as ctk
import threading
from ui.styles import THEME, FONTS
from core.thermal_monitor import ThermalMonitor
from core.event_log_miner import EventLogMiner
from core.drive_health import DriveHealthMonitor
from core.sfc_scanner import run_sfc, is_admin
from core.fix_library import get_fix_for_event
from core import diagnostics_cache
from utils import mode_manager


class DiagnosticsScreen(ctk.CTkFrame):
    """
    A dedicated screen with 3 advanced diagnostic panels:
      1. Thermal Throttle Detector
      2. Windows Event Log Miner
      3. SMART Drive Health Monitor
    """

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.thermal = ThermalMonitor()
        self.event_miner = EventLogMiner()
        self.drive_monitor = DriveHealthMonitor()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # header
        self.grid_rowconfigure(1, weight=1)  # scrollable content

        # ── Page Header ──
        header = ctk.CTkFrame(self, fg_color=THEME["card_color"], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text="🔬  Advanced Diagnostics",
            font=("Roboto Medium", 22),
        ).pack(side="left", padx=20, pady=14)

        ctk.CTkLabel(
            header,
            text="Deep system analysis — detecting problems hidden from Windows",
            font=FONTS["body"],
            text_color="#888888",
        ).pack(side="left", padx=0, pady=14)

        # ── Scrollable Body ──
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.scroll.grid_columnconfigure(0, weight=1)

        # Build 3 panels
        self._thermal_panel = self._build_panel(
            row=0,
            icon="🌡️",
            title="Thermal Throttle Detector",
            description="Checks if your CPU is secretly running slower than its rated speed due to overheating.",
            scan_fn=self._scan_thermal,
        )
        self._event_panel = self._build_panel(
            row=1,
            icon="📋",
            title="Windows Event Log Miner",
            description="Scans the last 24 hours of system logs for crashes, driver failures & unexpected shutdowns.",
            scan_fn=self._scan_events,
        )
        self._drive_panel = self._build_panel(
            row=2,
            icon="💾",
            title="SMART Drive Health Monitor",
            description="Reads drive firmware health data to predict failures before they happen.",
            scan_fn=self._scan_drives,
        )

        # 4th panel — System File Checker
        self._sfc_panel = self._build_sfc_panel(row=3)

    # ──────────────────────────────────────────────────
    # Panel builder
    # ──────────────────────────────────────────────────

    def _build_panel(self, row, icon, title, description, scan_fn):
        """Creates a card panel with a header and a results area."""
        outer = ctk.CTkFrame(self.scroll, fg_color=THEME["card_color"], corner_radius=12)
        outer.grid(row=row, column=0, sticky="ew", padx=4, pady=6)
        outer.grid_columnconfigure(0, weight=1)

        # Header row
        hdr = ctk.CTkFrame(outer, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 4))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text=icon, font=("Roboto", 22), width=36).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr, text=title, font=("Roboto Medium", 16)).grid(row=0, column=1, sticky="w", padx=8)
        ctk.CTkLabel(hdr, text=description, font=FONTS["small"], text_color="#888888",
                     wraplength=560, justify="left").grid(row=1, column=1, sticky="w", padx=8)

        scan_btn = ctk.CTkButton(
            hdr,
            text="⚡ Scan Now",
            width=110,
            height=32,
            fg_color=THEME["accent_color"],
        )
        scan_btn.grid(row=0, column=2, sticky="e")

        # Separator
        ctk.CTkFrame(outer, height=1, fg_color="#3d3d3d").grid(row=1, column=0, sticky="ew", padx=15)

        # Results container
        results_frame = ctk.CTkFrame(outer, fg_color="transparent")
        results_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(6, 12))
        results_frame.grid_columnconfigure(0, weight=1)

        # Placeholder label
        placeholder = ctk.CTkLabel(
            results_frame,
            text="Click ⚡ Scan Now to run this diagnostic.",
            font=FONTS["body"],
            text_color="#555555",
        )
        placeholder.grid(row=0, column=0, pady=10)

        # Wire button — closure captures results_frame and scan_fn
        def on_scan(btn=scan_btn, rf=results_frame, fn=scan_fn):
            btn.configure(state="disabled", text="Scanning...")
            threading.Thread(
                target=lambda: fn(rf, btn),
                daemon=True,
            ).start()

        scan_btn.configure(command=on_scan)

        return {"outer": outer, "results": results_frame, "btn": scan_btn}

    # ──────────────────────────────────────────────────
    # Card helpers
    # ──────────────────────────────────────────────────

    def _clear_results(self, results_frame):
        for w in results_frame.winfo_children():
            w.destroy()

    def _add_card(self, parent, severity, title, detail=None, row=0, fix_steps=None):
        """Adds a single styled result card. Pass fix_steps to add an expandable fix section."""
        colors = {
            "Critical": (THEME["danger_color"],  "#3d1f1f", "🚨"),
            "Warning":  (THEME["warning_color"], "#3a3010", "⚠️"),
            "OK":       (THEME["success_color"], "#1a3325", "✅"),
            "Info":     ("#5dade2",              "#1a2535", "ℹ️"),
        }
        accent, bg, icon = colors.get(severity, colors["Info"])

        card = ctk.CTkFrame(parent, fg_color=bg, corner_radius=8)
        card.grid(row=row, column=0, sticky="ew", pady=3)
        card.grid_columnconfigure(2, weight=1)

        n_rows = 1 + (1 if detail else 0)

        # Left bar
        ctk.CTkFrame(card, width=4, fg_color=accent, corner_radius=4).grid(
            row=0, column=0, rowspan=n_rows, sticky="ns", padx=(6, 0), pady=5
        )
        # Icon
        ctk.CTkLabel(card, text=icon, font=("Roboto", 13), width=24).grid(
            row=0, column=1, sticky="w", padx=(6, 2), pady=(5, 0)
        )
        # Title
        ctk.CTkLabel(card, text=title, font=("Roboto Medium", 13), text_color="#eeeeee",
                     anchor="w", justify="left", wraplength=520).grid(
            row=0, column=2, sticky="w", padx=(0, 8), pady=(5, 0)
        )
        if detail:
            ctk.CTkLabel(card, text=f"  🔧  {detail}", font=("Roboto", 10),
                         text_color="#aaaaaa", anchor="w", justify="left", wraplength=520).grid(
                row=1, column=2, sticky="w", padx=(0, 8), pady=(0, 4)
            )

        # ── Optional inline fix steps ──────────────────────────────────────────────
        if fix_steps:
            # The expandable steps frame (hidden by default)
            steps_frame = ctk.CTkFrame(card, fg_color="#111820", corner_radius=6)

            def _toggle(btn=None, sf=steps_frame):
                if sf.winfo_ismapped():
                    sf.grid_remove()
                    if btn:
                        btn.configure(text="🔧  Show Fix Steps")
                else:
                    sf.grid()
                    if btn:
                        btn.configure(text="🔼  Hide Fix Steps")

            toggle_btn = ctk.CTkButton(
                card,
                text="🔧  Show Fix Steps",
                width=140,
                height=24,
                fg_color="#1a3a5c",
                hover_color="#1f6aa5",
                font=("Roboto", 10, "bold"),
                command=lambda: _toggle(toggle_btn),
            )
            toggle_btn.grid(
                row=n_rows, column=2, sticky="w",
                padx=(0, 8), pady=(2, 6)
            )

            # Build steps in the hidden frame
            for j, step in enumerate(fix_steps, start=1):
                srow = ctk.CTkFrame(steps_frame, fg_color="transparent")
                srow.grid(row=j, column=0, sticky="ew", padx=8, pady=2)
                srow.grid_columnconfigure(1, weight=1)

                ctk.CTkLabel(
                    srow, text=f"{j}",
                    width=24, height=24,
                    fg_color=THEME["accent_color"],
                    font=("Roboto Medium", 10, "bold"),
                    corner_radius=12, text_color="white",
                ).grid(row=0, column=0, sticky="nw", pady=(2, 0))

                ctk.CTkLabel(
                    srow, text=step,
                    font=("Roboto", 10),
                    text_color="#cccccc",
                    anchor="w", justify="left", wraplength=490,
                ).grid(row=0, column=1, sticky="w", padx=(8, 0))

            steps_frame.grid_columnconfigure(0, weight=1)
            steps_frame.grid(
                row=n_rows + 1, column=0, columnspan=4,
                sticky="ew", padx=8, pady=(0, 6)
            )
            steps_frame.grid_remove()   # Start hidden


    def _set_scanning(self, results_frame, btn):
        """Clears results and shows a loading indicator."""
        self.after(0, lambda: self._clear_results(results_frame))
        loading = ctk.CTkLabel(results_frame, text="⏳ Scanning…", font=FONTS["body"], text_color="#888888")
        self.after(0, lambda: loading.grid(row=0, column=0, pady=10))

    # ──────────────────────────────────────────────────
    # Thermal Scan
    # ──────────────────────────────────────────────────

    def _scan_thermal(self, results_frame, btn):
        def _show_loading():
            self._clear_results(results_frame)
            ctk.CTkLabel(results_frame, text="⏳ Scanning CPU…",
                         font=FONTS["body"], text_color="#888888").grid(row=0, column=0, pady=10)
        self.after(0, _show_loading)

        try:
            data = self.thermal.get_throttle_status()
            temp = self.thermal.get_cpu_temperature()

            def render():
                self._clear_results(results_frame)
                results_frame.grid_columnconfigure(0, weight=1)

                row = 0
                freq_detail = (
                    f"Current: {data['current_mhz']} MHz  |  Max Rated: {data['max_mhz']} MHz  |  "
                    f"Running at {data['percent']}% of full speed"
                )
                sev = "Critical" if data["percent"] < 60 else ("Warning" if data["throttled"] else "OK")
                self._add_card(results_frame, sev, f"CPU Speed — {data['verdict']}", freq_detail, row=row)
                row += 1

                if temp is not None:
                    t_sev = "Critical" if temp > 90 else ("Warning" if temp > 75 else "OK")
                    self._add_card(results_frame, t_sev, f"CPU Temperature: {temp}°C",
                                   "Above 85°C under load = thermal paste likely needs replacing." if temp > 85 else None,
                                   row=row)
                    row += 1
                else:
                    self._add_card(results_frame, "Info",
                                   "CPU Temperature: Not available on this system",
                                   "Install HWiNFO64 and enable its WMI sensor support for temperature data.",
                                   row=row)
                    row += 1

                for tip in data.get("tips", []):
                    self._add_card(results_frame, "Info", tip, row=row)
                    row += 1

                diagnostics_cache.update("thermal", data)
                btn.configure(state="normal", text="⚡ Scan Now")

            self.after(0, render)
        except Exception as e:
            err = str(e)
            def _show_err():
                self._clear_results(results_frame)
                self._add_card(results_frame, "Critical", f"Thermal scan failed: {err}", row=0)
                btn.configure(state="normal", text="⚡ Scan Now")
            self.after(0, _show_err)

    # ──────────────────────────────────────────────────
    # Event Log Scan
    # ──────────────────────────────────────────────────

    def _scan_events(self, results_frame, btn):
        def _show_loading():
            self._clear_results(results_frame)
            ctk.CTkLabel(results_frame, text="⏳ Reading Event Log (last 24h)…",
                         font=FONTS["body"], text_color="#888888").grid(row=0, column=0, pady=10)
        self.after(0, _show_loading)

        try:
            events = self.event_miner.get_critical_events(hours=24)

            def render():
                self._clear_results(results_frame)
                results_frame.grid_columnconfigure(0, weight=1)

                if not events:
                    self._add_card(results_frame, "OK",
                                   "No critical errors found in the last 24 hours.", row=0)
                else:
                    for i, ev in enumerate(events):
                        title = f"[{ev['time']}]  {ev['title']}   (ID {ev['event_id']} · {ev['log']})"
                        # Look up fix steps from our local library
                        fix_data  = get_fix_for_event(ev.get("source", ""), ev.get("event_id", 0))
                        fix_steps = fix_data[1] if fix_data else None
                        self._add_card(
                            results_frame, ev["severity"], title,
                            ev["explanation"], row=i,
                            fix_steps=fix_steps,
                        )

                diagnostics_cache.update("events", events)
                btn.configure(state="normal", text="⚡ Scan Now")

            self.after(0, render)
        except Exception as e:
            err = str(e)
            def _show_err():
                self._clear_results(results_frame)
                self._add_card(results_frame, "Critical", f"Event log scan failed: {err}", row=0)
                btn.configure(state="normal", text="⚡ Scan Now")
            self.after(0, _show_err)

    # ──────────────────────────────────────────────────
    # Drive Health Scan
    # ──────────────────────────────────────────────────

    def _scan_drives(self, results_frame, btn):
        def _show_loading():
            self._clear_results(results_frame)
            ctk.CTkLabel(results_frame, text="⏳ Reading drive SMART data…",
                         font=FONTS["body"], text_color="#888888").grid(row=0, column=0, pady=10)
        self.after(0, _show_loading)

        try:
            drives = self.drive_monitor.get_all_drives_health()

            def render():
                self._clear_results(results_frame)
                results_frame.grid_columnconfigure(0, weight=1)

                if not drives:
                    self._add_card(results_frame, "Warning",
                                   "No drives detected. Try running TechGuardAI as Administrator.", row=0)
                else:
                    row = 0
                    for drive in drives:
                        size_str = f"{drive['size_gb']} GB" if drive['size_gb'] else "Size Unknown"
                        drive_title = f"{drive['grade_display']}   {drive['model']}  ({drive['type']} · {size_str})"
                        sev = drive["health_grade"]
                        self._add_card(results_frame, sev, drive_title,
                                       f"Serial: {drive['serial']}  |  Status: {drive['status']}", row=row)
                        row += 1

                        for issue in drive["issues"]:
                            issue_sev = "OK" if "No" in issue and "issue" in issue.lower() else sev
                            self._add_card(results_frame, issue_sev, issue, row=row)
                            row += 1

                diagnostics_cache.update("drives", drives)
                btn.configure(state="normal", text="⚡ Scan Now")

            self.after(0, render)
        except Exception as e:
            err = str(e)
            def _show_err():
                self._clear_results(results_frame)
                self._add_card(results_frame, "Critical", f"Drive scan failed: {err}", row=0)
                btn.configure(state="normal", text="⚡ Scan Now")
            self.after(0, _show_err)

    # ──────────────────────────────────────────────────
    # System File Checker (SFC) Panel
    # ──────────────────────────────────────────────────

    def _build_sfc_panel(self, row: int) -> dict:
        """Builds the System File Checker panel with progress bar support."""
        outer = ctk.CTkFrame(self.scroll, fg_color=THEME["card_color"], corner_radius=12)
        outer.grid(row=row, column=0, sticky="ew", padx=4, pady=6)
        outer.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(outer, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 4))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="🛡️", font=("Segoe UI Emoji", 20), width=36).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr, text="Windows System File Checker",
                     font=("Roboto Medium", 16)).grid(row=0, column=1, sticky="w", padx=8)
        ctk.CTkLabel(
            hdr,
            text="Scans all protected Windows files for corruption or damage and repairs them automatically.",
            font=FONTS["small"], text_color="#888888", wraplength=540, justify="left",
        ).grid(row=1, column=1, sticky="w", padx=8)

        scan_btn = ctk.CTkButton(
            hdr, text="⚡ Scan Now", width=110, height=32, fg_color=THEME["accent_color"]
        )
        scan_btn.grid(row=0, column=2, sticky="e")

        # Warning note
        ctk.CTkLabel(
            outer,
            text="⚠️  Requires Administrator rights  •  Estimated time: 2–5 minutes",
            font=FONTS["small"], text_color="#888888",
        ).grid(row=1, column=0, padx=20, pady=(0, 4), sticky="w")

        # Separator
        ctk.CTkFrame(outer, height=1, fg_color="#3d3d3d").grid(
            row=2, column=0, sticky="ew", padx=15)

        # Progress bar + label (hidden until scan starts)
        progress_bar = ctk.CTkProgressBar(
            outer, height=8, corner_radius=4,
            progress_color=THEME["accent_color"]
        )
        progress_bar.set(0)
        progress_lbl = ctk.CTkLabel(
            outer, text="", font=FONTS["small"], text_color=THEME["accent_color"]
        )

        # Results area
        results_frame = ctk.CTkFrame(outer, fg_color="transparent")
        results_frame.grid(row=5, column=0, sticky="ew", padx=15, pady=(6, 12))
        results_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            results_frame,
            text="Click ⚡ Scan Now to check your Windows system files.",
            font=FONTS["body"], text_color="#555555",
        ).grid(row=0, column=0, pady=10)

        # Wire scan button
        def on_scan(
            btn=scan_btn, rf=results_frame,
            pb=progress_bar, pl=progress_lbl, out=outer
        ):
            btn.configure(state="disabled", text="Scanning…")
            pb.set(0)
            pb.grid(row=3, column=0, sticky="ew", padx=15, pady=(6, 0))
            pl.grid(row=4, column=0, padx=15, pady=(2, 0), sticky="w")
            threading.Thread(
                target=lambda: self._scan_sfc(rf, btn, pb, pl),
                daemon=True,
            ).start()

        scan_btn.configure(command=on_scan)
        return {"outer": outer, "results": results_frame,
                "btn": scan_btn, "pb": progress_bar, "pl": progress_lbl}

    def _scan_sfc(self, results_frame, btn, progress_bar, progress_lbl):
        """Background: starts sfc scanner, wires callbacks back to main thread."""
        # Clear old results + show loading
        def _show_loading():
            self._clear_results(results_frame)
            ctk.CTkLabel(
                results_frame,
                text="⏳ Scanning Windows files — this may take 2–5 minutes…",
                font=FONTS["body"], text_color="#888888",
            ).grid(row=0, column=0, pady=10)
        self.after(0, _show_loading)

        def _progress(pct, msg):
            self.after(0, lambda: progress_bar.set(pct / 100))
            self.after(0, lambda: progress_lbl.configure(text=msg))

        def _done(result):
            self.after(0, lambda: self._show_sfc_result(
                result, results_frame, btn, progress_bar, progress_lbl
            ))

        run_sfc(progress_cb=_progress, done_cb=_done)

    def _show_sfc_result(self, result, results_frame, btn, pb, pl):
        """Renders SFC result cards (mode-aware)."""
        self._clear_results(results_frame)
        results_frame.grid_columnconfigure(0, weight=1)
        btn.configure(state="normal", text="⚡ Scan Now")
        pb.grid_remove()
        pl.grid_remove()

        status  = result["status"]
        beginner = mode_manager.is_beginner()

        # Severity
        sev_map = {
            "clean":     "OK",
            "fixed":     "Warning",
            "unfixable": "Critical",
            "no_admin":  "Warning",
            "error":     "Critical",
            "unknown":   "Info",
        }
        sev = sev_map.get(status, "Info")

        # Beginner-friendly overrides
        if beginner:
            beg_titles = {
                "clean":     "✅ Great news! All your Windows files are healthy",
                "fixed":     "🟡 Windows found and fixed some broken files",
                "unfixable": "🔴 Windows found broken files it couldn't fix automatically",
                "no_admin":  "⚠️ This scan needs Administrator access to run",
                "error":     "❌ The scan couldn't start",
                "unknown":   "ℹ️ Scan completed",
            }
            beg_details = {
                "clean":     "No action needed — your Windows system is in good shape.",
                "fixed":     "Please restart your PC to finish the repair.",
                "unfixable": "Don't worry — there's a deeper repair tool called DISM that can fix this.",
                "no_admin":  "Right-click TechGuardAI and choose 'Run as administrator', then try again.",
                "error":     "Try restarting your PC and running the scan again.",
                "unknown":   "Results could not be read. Check the scan log for details.",
            }
            title  = beg_titles.get(status,  result["title"])
            detail = beg_details.get(status, result["detail"])
        else:
            title  = result["title"]
            detail = result["detail"]

        self._add_card(results_frame, sev, title, detail, row=0)

        # Next steps
        for i, step in enumerate(result.get("steps", []), start=1):
            step_sev = "Info" if not beginner else "Warning"
            self._add_card(results_frame, step_sev, step, row=i)

        # CBS log path (expert mode only)
        if not beginner and result.get("log_path"):
            next_row = 1 + len(result.get("steps", []))
            self._add_card(
                results_frame, "Info",
                f"📂 Full scan log: {result['log_path']}",
                detail="Open this file in Notepad to see detailed scan output",
                row=next_row,
            )
