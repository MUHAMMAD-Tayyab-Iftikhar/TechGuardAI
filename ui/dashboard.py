import customtkinter as ctk
import threading

from ui.styles import THEME, FONTS
from core import diagnostics_cache
from utils import mode_manager
from core.cleaner import SystemCleaner

# ---------------------------------------------------------------------------
# Beginner-mode translation helpers (pure functions, no UI dependency)
# ---------------------------------------------------------------------------

def _fmt_beg_cpu(usage: float) -> str:
    if usage > 85: return "🔴 Overloaded!"
    if usage > 60: return "🟡 Working Hard"
    return "🟢 Relaxed"

def _fmt_beg_ram(percent: float) -> str:
    if percent > 85: return "🔴 Almost Full!"
    if percent > 70: return "🟡 Getting Full"
    return "🟢 Plenty Free"

def _fmt_beg_disk(percent: float) -> str:
    if percent > 90: return "🔴 Out of Space!"
    if percent > 75: return "🟡 Getting Low"
    return "🟢 Good Space Left"

def _fmt_beg_net(down_str: str) -> str:
    try:
        val = float(down_str.replace(" KB/s", ""))
        if val > 100: return "🟢 Fast"
        if val > 5:   return "🟡 Slow"
        return "⚪ No Activity"
    except Exception:
        return "⚪ Unknown"

def _fmt_beg_battery(bat_str: str) -> str:
    if any(k in bat_str for k in ("Desktop", "No Battery", "AC Power")):
        return "🔌 Desktop PC"
    if "Charging" in bat_str:
        return "🔌 Charging"
    try:
        pct = int(bat_str.split("%")[0])
        if pct > 50: return "🟢 Battery OK"
        if pct > 20: return "🟡 Battery Low"
        return "🔴 Charge Now!"
    except Exception:
        return bat_str

def _fmt_beg_bloat(rating: str) -> str:
    return {
        "Clean":      "🟢 Running Smoothly",
        "Normal":     "🟡 Normal",
        "Bloated":    "🟡 Many Apps Open",
        "Overloaded": "🔴 Too Many Apps!",
    }.get(rating, "🟡 Normal")

def _fmt_beg_uptime(uptime_str: str) -> str:
    if "d" in uptime_str:
        try:
            days = int(uptime_str.split("d")[0])
            if days >= 7: return "🔴 Needs Restart!"
            return f"🟡 {days} Day(s) Running"
        except Exception:
            return "🟡 A Few Days"
    return "🟢 Recently Restarted"

def _fmt_beg_process(proc_str: str) -> str:
    """Strip the (XX%) or (XX MB) suffix to show just the app name."""
    name = proc_str.split("(")[0].strip() if "(" in proc_str else proc_str
    return name if name not in ("Scanning...", "Unknown") else "Checking…"

# Mapping of HealthAnalyzer insight types → friendly Beginner text
_BEGINNER_INSIGHT = {
    "Performance": (
        "Your computer processor is working too hard",
        "Close apps you're not using right now",
    ),
    "Memory": (
        "Your computer is running low on memory",
        "Close browser tabs and unused programs",
    ),
    "Storage": (
        "Your storage drive is almost full",
        "Run the System Cleaner to free up space",
    ),
    "Power": (
        "Your battery is very low",
        "Plug in your charger now",
    ),
    "Security": (
        "High activity detected with no internet",
        "Check if something unexpected is running",
    ),
    "Maintenance": (
        "Your PC hasn't been restarted in a while",
        "Click Start → Power → Restart to refresh your PC",
    ),
    "System": (
        "Everything looks great!",
        "No action needed — your PC is healthy",
    ),
    "OK":    ("No problems found",   "Keep it up!"),
    "Boost": ("PC Boost complete!",  "Your PC has been tuned up"),
    "Error": ("Something went wrong", "Try again or restart the app"),
}


class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, monitor, ai_analyzer, chatbot):
        super().__init__(master, fg_color="transparent")
        self.monitor = monitor
        self.ai = ai_analyzer
        self.chatbot = chatbot
        
        # Grid Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Rows: Header, Metrics 1, Metrics 2, Metrics 3, AI Panel
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0) 
        self.grid_rowconfigure(2, weight=0) 
        self.grid_rowconfigure(3, weight=0) # Row 3
        self.grid_rowconfigure(4, weight=1) # AI Panel

        self._init_ui()

    def _init_ui(self):
        self.header_frame = ctk.CTkFrame(self, fg_color=THEME["card_color"])
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        
        self.status_label = ctk.CTkLabel(self.header_frame, text="System Status: Analyzing...", font=FONTS["header"])
        self.status_label.pack(side="left", padx=20, pady=15)

        self.refresh_btn = ctk.CTkButton(self.header_frame, text="Force Refresh", command=self.update_data)
        self.refresh_btn.pack(side="right", padx=(10, 20), pady=15)

        # 1-Click Optimize Master Button
        self.opt_btn = ctk.CTkButton(
            self.header_frame, text="⚡ 1-Click Optimize", 
            fg_color="#b66504", hover_color="#ce7d1d",
            font=("Roboto Medium", 14, "bold"),
            command=self._run_1_click_optimize
        )
        self.opt_btn.pack(side="right", padx=(10, 10), pady=15)

        # Row 1: Core Metrics
        self.row1_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.row1_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.row1_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.cpu_title,   self.cpu_card   = self._create_metric_card(self.row1_frame, "CPU Load",      "0%",          0)
        self.ram_title,   self.ram_card   = self._create_metric_card(self.row1_frame, "Memory Usage",  "0%",          1)
        self.disk_title,  self.disk_card  = self._create_metric_card(self.row1_frame, "Disk (C:)",     "0%",          2)

        # Row 2: Context Metrics
        self.row2_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.row2_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.row2_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.net_title,   self.net_card   = self._create_metric_card(self.row2_frame, "Network Activity", "↓ 0 KB/s",     0)
        self.pwr_title,   self.pwr_card   = self._create_metric_card(self.row2_frame, "Power Context",    "AC Power",     1)
        self.bloat_title, self.bloat_card = self._create_metric_card(self.row2_frame, "Background Noise", "Scanning...",  2)

        # Row 3: Deep Insights
        self.row3_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.row3_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.row3_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.uptime_title,  self.uptime_card  = self._create_metric_card(self.row3_frame, "System Uptime",   "0h 0m",       0)
        self.top_cpu_title, self.top_cpu_card = self._create_metric_card(self.row3_frame, "Top CPU Hog",     "Scanning...", 1)
        self.top_mem_title, self.top_mem_card = self._create_metric_card(self.row3_frame, "Top Memory Hog",  "Scanning...", 2)

        # AI Insights Panel
        self.ai_frame = ctk.CTkFrame(self, fg_color=THEME["card_color"])
        self.ai_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        self.ai_header = ctk.CTkFrame(self.ai_frame, fg_color="transparent")
        self.ai_header.pack(fill="x")
        
        ctk.CTkLabel(self.ai_header, text="🧠 AI Diagnostic Insights", font=FONTS["subheader"]).pack(side="left", padx=15, pady=(10, 5))
        
        self.audit_btn = ctk.CTkButton(self.ai_header, text="🛡 Security Audit", 
                                       width=130, height=28, 
                                       command=self.chatbot.run_security_scan)
        self.audit_btn.pack(side="right", padx=15, pady=(10, 5))
        

        
        # Separator Line
        sep = ctk.CTkFrame(self.ai_frame, height=1, fg_color="#3d3d3d")
        sep.pack(fill="x", padx=15)
        
        # Scrollable card container
        self.insight_container = ctk.CTkScrollableFrame(self.ai_frame, fg_color="transparent")
        self.insight_container.pack(fill="both", expand=True, padx=10, pady=8)

        # Fast scroll
        def _fast_scroll(event):
            self.insight_container._parent_canvas.yview_scroll(int(-1 * (event.delta / 40)), "units")
        self.insight_container.bind("<MouseWheel>", _fast_scroll)
        self.insight_container._parent_canvas.bind("<MouseWheel>", _fast_scroll)

        # Register mode-change callback so the dashboard re-renders automatically
        mode_manager.register_callback(lambda _: self.update_data())

        self.after(2000, self.auto_refresh)

    def _clear_insights(self):
        """Removes all child widgets from the insight container."""
        for widget in self.insight_container.winfo_children():
            widget.destroy()

    def _add_insight_card(self, insight_type, message, fix=None, color=None):
        """Creates a single styled insight card inside the container."""
        type_styles = {
            "Critical": {"color": THEME["danger_color"],  "icon": "🚨", "bg": "#3d1f1f"},
            "Warning":  {"color": THEME["warning_color"], "icon": "⚠️",  "bg": "#3a3010"},
            "OK":       {"color": THEME["success_color"], "icon": "✅",  "bg": "#1a3325"},
            "System":   {"color": "#5dade2",             "icon": "ℹ️",  "bg": "#1a2535"},
            "Boost":    {"color": THEME["success_color"], "icon": "⚡",  "bg": "#1a3325"},
            "Error":    {"color": THEME["danger_color"],  "icon": "❌",  "bg": "#3d1f1f"},
        }
        style = type_styles.get(insight_type, type_styles["System"])
        if color:
            style["color"] = color

        card = ctk.CTkFrame(self.insight_container, fg_color=style["bg"], corner_radius=8)
        card.pack(anchor="w", padx=4, pady=2)
        card.grid_columnconfigure(1, weight=1)

        bar = ctk.CTkFrame(card, width=4, fg_color=style["color"], corner_radius=4)
        bar.grid(row=0, column=0, rowspan=2 if fix else 1, sticky="ns", padx=(5, 0), pady=4)

        ctk.CTkLabel(card, text=style["icon"], font=("Roboto", 13), width=24).grid(
            row=0, column=1, sticky="w", padx=(6, 2), pady=(4, 0))

        ctk.CTkLabel(card, text=message, font=("Roboto Medium", 13), text_color="#eeeeee",
                     anchor="w", justify="left", wraplength=480).grid(
            row=0, column=2, sticky="w", padx=(0, 8), pady=(4, 0))

        if fix:
            fix_label = ctk.CTkLabel(card, text=f"  🔧  {fix}", font=("Roboto", 10),
                                     text_color="#aaaaaa", anchor="w", justify="left", wraplength=460)
            fix_label.grid(row=1, column=2, sticky="w", padx=(0, 8), pady=(0, 4))
        else:
            card.winfo_children()[-1].grid_configure(pady=(4, 6))


    def _on_optimize_complete(self, summary):
        self._clear_insights()
        if summary.get("success"):
            self._add_insight_card("Boost", "✅ Optimize Complete!",
                                   fix=f"Cleaned {summary.get('mb_cleaned', 0):.2f} MB of junk files")
            dns_msg = "DNS Resolver Cache Flushed (Improves connectivity)" if summary.get("dns_flushed") else "DNS flush failed or skipped."
            self._add_insight_card("System", "Network", fix=dns_msg)
        else:
            for err in summary.get("errors", ["Unknown error"]):
                self._add_insight_card("Error", err)
        self.update_data()


    def _create_metric_card(self, parent, title, value, col):
        """Returns (title_label, value_label) for a metric card."""
        card = ctk.CTkFrame(parent, fg_color=THEME["card_color"])
        card.grid(row=0, column=col, padx=5, sticky="ew")
        title_label = ctk.CTkLabel(card, text=title, font=FONTS["subheader"], text_color="gray")
        title_label.pack(pady=(10, 0))
        val_label = ctk.CTkLabel(card, text=value, font=("Roboto", 14, "bold"), wraplength=160)
        val_label.pack(pady=(0, 10))
        return title_label, val_label

    def update_data(self):
        """Fetch metrics in a background thread to keep the UI responsive."""
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _fetch_and_update(self):
        """Background worker: collect data, then schedule UI update on main thread."""
        try:
            cpu   = self.monitor.get_cpu_metrics()
            ram   = self.monitor.get_memory_metrics()
            disk  = self.monitor.get_disk_metrics()
            net   = self.monitor.get_network_speed()
            bat   = self.monitor.get_battery_report()
            bloat = self.monitor.get_process_bloat_score()
            uptime    = self.monitor.get_system_uptime()
            top_cpu   = self.monitor.get_top_cpu_process()
            top_mem   = self.monitor.get_heaviest_process()
            heavy_app = top_mem.split("(")[0].strip() if "(" in top_mem else "Unknown"
            analysis  = self.ai.analyze_health(cpu, ram, disk, net, bat, heavy_app)
        except Exception as e:
            print(f"[Dashboard] Data fetch error: {e}")
            return

        self.after(0, lambda: self._apply_ui_update(
            cpu, ram, disk, net, bat, bloat, uptime, top_cpu, top_mem, analysis
        ))

    def _apply_ui_update(self, cpu, ram, disk, net, bat, bloat, uptime, top_cpu, top_mem, analysis):
        """Applies all dashboard UI updates — must run on the main thread."""
        beginner = mode_manager.is_beginner()

        if beginner:
            # ── Beginner Mode ─────────────────────────────────────────────────
            # Row 1 titles + values
            self.cpu_title.configure(text="Processor")
            self.cpu_card.configure(text=_fmt_beg_cpu(cpu["usage"]))

            self.ram_title.configure(text="Memory")
            self.ram_card.configure(text=_fmt_beg_ram(ram["percent"]))

            self.disk_title.configure(text="Storage Drive")
            self.disk_card.configure(text=_fmt_beg_disk(disk["percent"]))

            # Row 2
            self.net_title.configure(text="Internet")
            self.net_card.configure(text=_fmt_beg_net(net["down"]))

            self.pwr_title.configure(text="Battery")
            self.pwr_card.configure(text=_fmt_beg_battery(bat))

            self.bloat_title.configure(text="Running Apps")
            self.bloat_card.configure(text=_fmt_beg_bloat(bloat["rating"]))

            # Row 3
            self.uptime_title.configure(text="Time Since Restart")
            self.uptime_card.configure(text=_fmt_beg_uptime(uptime))

            self.top_cpu_title.configure(text="Busiest App")
            self.top_cpu_card.configure(text=_fmt_beg_process(top_cpu))

            self.top_mem_title.configure(text="Memory-Heavy App")
            self.top_mem_card.configure(text=_fmt_beg_process(top_mem))

            # Status header
            n_issues = sum(1 for i in analysis["insights"] if i["type"] not in ("System",))
            if analysis["status"] == "Critical":
                status_txt = "🚨 Your PC has serious problems!"
                status_col = THEME["danger_color"]
            elif analysis["status"] == "Warning" or n_issues:
                status_txt = f"⚠️ Your PC needs some attention"
                status_col = THEME["warning_color"]
            else:
                status_txt = "✅ Your PC is doing great!"
                status_col = THEME["success_color"]
            self.status_label.configure(text=status_txt, text_color=status_col)

            # Insight cards — simplified
            self._clear_insights()
            shown_types = set()
            for item in analysis["insights"]:
                t = item.get("type", "System")
                if t in shown_types:
                    continue
                shown_types.add(t)
                beg = _BEGINNER_INSIGHT.get(t, (item["msg"], item.get("action", "")))
                sev = "Critical" if t == "Performance" and cpu["usage"] > 85 else \
                      "Critical" if t == "Memory"      and ram["percent"] > 85 else \
                      "Critical" if t == "Storage"     and disk["percent"] > 90 else \
                      "Warning"  if t in ("Performance", "Memory", "Storage", "Power", "Security", "Maintenance") else \
                      "OK"
                self._add_insight_card(sev, beg[0], fix=beg[1])

            if not analysis["insights"]:
                self._add_insight_card("OK", "Everything looks great! No problems found.")

        else:
            # ── Expert (Advanced) Mode ─────────────────────────────────────────
            # Row 1
            self.cpu_title.configure(text="CPU Load")
            self.cpu_card.configure(text=f"{cpu['usage']}%")

            self.ram_title.configure(text="Memory Usage")
            self.ram_card.configure(text=f"{ram['percent']}%")

            self.disk_title.configure(text="Disk (C:)")
            self.disk_card.configure(text=f"{disk['percent']}% Used")

            # Row 2
            self.net_title.configure(text="Network Activity")
            self.net_card.configure(text=f"↓{net['down']}  ↑{net['up']}")

            self.pwr_title.configure(text="Power Context")
            self.pwr_card.configure(text=bat)

            self.bloat_title.configure(text="Background Noise")
            self.bloat_card.configure(text=f"{bloat['count']} Apps ({bloat['rating']})")

            # Row 3
            self.uptime_title.configure(text="System Uptime")
            self.uptime_card.configure(text=uptime)

            self.top_cpu_title.configure(text="Top CPU Hog")
            self.top_cpu_card.configure(text=top_cpu)

            self.top_mem_title.configure(text="Top Memory Hog")
            self.top_mem_card.configure(text=top_mem)

            # Status header
            status_color = THEME["success_color"]
            if analysis["status"] == "Warning":  status_color = THEME["warning_color"]
            if analysis["status"] == "Critical": status_color = THEME["danger_color"]
            self.status_label.configure(
                text=f"System Status: {analysis['status']}  │  Health Score: {analysis['score']}",
                text_color=status_color
            )

            # Insight cards — standard
            self._clear_insights()
            if analysis["insights"]:
                for item in analysis["insights"]:
                    self._add_insight_card(item["type"], item["msg"], fix=item["action"])
            else:
                self._add_insight_card("OK", "All systems nominal. Performance is optimal.")

        # Diagnostics cache summary (mode-aware) — always appended
        self._add_diag_summary_cards()

    def _add_diag_summary_cards(self):
        """Appends a short summary of diagnostics scan results to the insights panel."""
        beginner = mode_manager.is_beginner()
        thermal = diagnostics_cache._cache.get("thermal")
        drives  = diagnostics_cache._cache.get("drives")
        events  = diagnostics_cache._cache.get("events")

        if thermal:
            if beginner:
                if thermal.get("throttled"):
                    pct = thermal.get("percent", 100)
                    sev = "Critical" if pct < 60 else "Warning"
                    self._add_insight_card(sev,
                        "Your processor is running slower than normal due to heat",
                        fix="Clean the vents on your computer")
                else:
                    self._add_insight_card("OK", "Your processor is running at full speed")
            else:
                verdict = thermal.get("verdict", "")
                pct     = thermal.get("percent", 100)
                sev     = "Critical" if pct < 60 else ("Warning" if thermal.get("throttled") else "OK")
                self._add_insight_card(sev,
                    f"CPU Thermal: {verdict} ({pct}% of max speed)",
                    fix=thermal.get("tips", [""])[0] if thermal.get("throttled") else None)

        if drives:
            for d in drives:
                grade = d.get("health_grade", "Healthy")
                sev   = grade if grade in ("Healthy", "Warning", "Critical") else "Warning"
                if beginner:
                    drive_type = d.get("type", "storage")
                    if grade == "Critical":
                        self._add_insight_card("Critical",
                            f"Your {drive_type} drive may be about to fail!",
                            fix="Back up your important files immediately")
                    elif grade == "Warning":
                        self._add_insight_card("Warning",
                            f"Your {drive_type} drive has some issues",
                            fix="Consider backing up your files soon")
                    else:
                        self._add_insight_card("OK", "Your storage drive is healthy")
                else:
                    issue_msg = d["issues"][0] if d.get("issues") else "No issues."
                    self._add_insight_card(sev,
                        f"Drive Health — {d['model']}: {grade}",
                        fix=issue_msg if grade != "Healthy" else None)

        if events is not None:
            critical_count = sum(1 for e in events if e.get("severity") == "Critical")
            warning_count  = sum(1 for e in events if e.get("severity") == "Warning")
            if beginner:
                if critical_count > 0:
                    self._add_insight_card("Critical",
                        f"Windows found {critical_count} serious problem(s) recently",
                        fix="Open Diagnostics to see what happened")
                elif warning_count > 0:
                    self._add_insight_card("Warning",
                        f"Windows logged {warning_count} warning(s) recently",
                        fix="Open Diagnostics for more details")
                else:
                    self._add_insight_card("OK", "No problems found in recent Windows logs")
            else:
                if critical_count > 0:
                    self._add_insight_card("Critical",
                        f"Event Log: {critical_count} critical error(s) in the last 24h",
                        fix="Open Diagnostics → Event Log Miner for full details")
                elif warning_count > 0:
                    self._add_insight_card("Warning",
                        f"Event Log: {warning_count} warning(s) in the last 24h",
                        fix="Open Diagnostics → Event Log Miner for full details")
                else:
                    self._add_insight_card("OK", "Event Log: No errors in the last 24 hours")

    # ───────────────────────────────────────────────────────────────────────
    # 1-Click Optimize Automations
    # ───────────────────────────────────────────────────────────────────────

    def _run_1_click_optimize(self):
        """Automates routine PC tune-up: clears junk, flushes DNS, and shows results."""
        self.opt_btn.configure(state="disabled", text="⏳ Optimizing...")
        self._clear_insights()
        self._add_insight_card("System", "⚡ 1-Click Optimize initiated. Cleaning system files and flushing DNS...")
        
        def run_in_bg():
            from core.cleaner import SystemCleaner
            cleaner = SystemCleaner()
            summary = cleaner.run_one_click_boost()
            self.after(0, lambda: self._on_optimize_complete(summary))
            self._set_status_safe("✅ System Optimized!")
            import time; time.sleep(3)
            self._set_status_safe("System Status: Tracking...")
            self.after(0, lambda: self.opt_btn.configure(state="normal", text="⚡ 1-Click Optimize"))
        
        threading.Thread(target=run_in_bg, daemon=True).start()

        
    def _set_status_safe(self, txt):
        self.after(0, lambda: self.status_label.configure(text=txt))

    def auto_refresh(self):
        self.update_data()
        self.after(2000, self.auto_refresh)