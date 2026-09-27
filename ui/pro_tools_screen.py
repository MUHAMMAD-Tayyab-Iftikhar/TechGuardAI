import customtkinter as ctk
from ui.styles import THEME, FONTS
from core.software_updater import SoftwareUpdater
from core.network_privacy import NetworkPrivacyManager
from core.startup_manager import StartupManager

class UpdaterEngineUI(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.updater = SoftwareUpdater()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        
        self.lbl_upd_status = ctk.CTkLabel(top_frame, text="Ready to scan for updates.", font=FONTS["body"])
        self.lbl_upd_status.pack(side="left", padx=10)

        self.btn_scan_upd = ctk.CTkButton(top_frame, text="🔍 Scan for Updates", command=self._scan_updates)
        self.btn_scan_upd.pack(side="right", padx=10)

        self.upd_scroll = ctk.CTkScrollableFrame(self, fg_color="#1a2535")
        self.upd_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def _scan_updates(self):
        self.btn_scan_upd.configure(state="disabled", text="⏳ Scanning...")
        self.lbl_upd_status.configure(text="Checking winget for out-of-date apps (can take 10-30s).")
        for w in self.upd_scroll.winfo_children(): w.destroy()
        
        def on_done(results):
            self.after(0, lambda: self._render_updates(results))
        self.updater.check_for_updates(on_done)

    def _render_updates(self, results):
        self.btn_scan_upd.configure(state="normal", text="🔍 Scan for Updates")
        if not results:
            self.lbl_upd_status.configure(text="✅ All installed software is up to date!")
            return
            
        self.lbl_upd_status.configure(text=f"⚠️ {len(results)} application(s) have updates available.")
        
        for i, app in enumerate(results):
            row = ctk.CTkFrame(self.upd_scroll, fg_color=THEME["bg_color"], corner_radius=6)
            row.pack(fill="x", pady=4, padx=5)
            row.grid_columnconfigure(0, weight=1)
            
            lbl = ctk.CTkLabel(
                row, 
                text=f"{app['name']}  (v{app['version']} ➔ v{app['available']})", 
                font=("Roboto Medium", 13),
                anchor="w"
            )
            lbl.grid(row=0, column=0, sticky="w", padx=15, pady=12)
            
            # Update individual button
            btn = ctk.CTkButton(
                row, text="Update", width=80,
                command=lambda a=app['id'], b=row: self._install_app(a, b)
            )
            btn.grid(row=0, column=1, padx=15, pady=12)

    def _install_app(self, app_id, row_frame):
        for child in row_frame.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(state="disabled", text="Installing...")
        
        def success():
            self.after(0, row_frame.destroy)
        def fail(err):
            print(f"Update failed: {err}")
            for child in row_frame.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    child.configure(state="normal", text="Failed")
                    child.configure(fg_color=THEME["danger_color"])
                    
        self.updater.install_update(app_id, success, fail)

    # ── Privacy Tab ──────────────────────────────────────────────────────────

class PrivacyEngineUI(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.privacy = NetworkPrivacyManager()
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Toggles section (Left)
        tog_frame = ctk.CTkFrame(self, fg_color="transparent")
        tog_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(tog_frame, text="Windows Privacy Tracking", font=("Roboto Medium", 16)).pack(pady=(0, 10), anchor="w")
        
        self.telemetry_var = ctk.StringVar(value="on")
        is_blocked = self.privacy.get_telemetry_status()
        if is_blocked: self.telemetry_var.set("off")
        
        self.sw_telemetry = ctk.CTkSwitch(
            tog_frame, text="Windows Data Collection (Telemetry)", 
            command=self._toggle_telemetry,
            variable=self.telemetry_var, onvalue="on", offvalue="off"
        )
        self.sw_telemetry.pack(pady=10, anchor="w")
        
        if not self.privacy.is_admin():
            ctk.CTkLabel(tog_frame, text="⚠️ Requires Run as Admin to change.", text_color=THEME["warning_color"]).pack(anchor="w")
            self.sw_telemetry.configure(state="disabled")

        # Network Monitor (Right/Bottom)
        lbl_conn = ctk.CTkLabel(self, text="Active Outbound Connections", font=("Roboto Medium", 16))
        lbl_conn.grid(row=0, column=1, sticky="sw", padx=10, pady=10)
        
        self.conn_btn = ctk.CTkButton(self, text="Refresh Map", width=100, command=self._refresh_conns)
        self.conn_btn.grid(row=0, column=1, sticky="se", padx=10, pady=10)

        self.conn_scroll = ctk.CTkScrollableFrame(self, fg_color="#1a2535")
        self.conn_scroll.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        self.after(200, self._refresh_conns)

    def _toggle_telemetry(self):
        blocked = self.telemetry_var.get() == "off"
        success = self.privacy.set_telemetry_blocked(blocked)
        if not success:
            # Revert switch if failed
            self.telemetry_var.set("on" if blocked else "off")

    def _refresh_conns(self):
        self.conn_btn.configure(state="disabled", text="⏳ Scanning...")
        for w in self.conn_scroll.winfo_children(): w.destroy()
        ctk.CTkLabel(self.conn_scroll, text="Scanning network sockets...\nThis might take a moment.", text_color="gray").pack(pady=20)
        
        def _fetch_in_bg():
            from utils import mode_manager
            beginner = mode_manager.is_beginner()
            conns = self.privacy.get_active_connections()
            self.after(0, lambda: self._render_conns(conns, beginner))
            
        import threading
        threading.Thread(target=_fetch_in_bg, daemon=True).start()

    def _render_conns(self, conns, beginner):
        self.conn_btn.configure(state="normal", text="Refresh Map")
        for w in self.conn_scroll.winfo_children(): w.destroy()
        
        if not conns:
            ctk.CTkLabel(self.conn_scroll, text="No active external connections.").pack(pady=20)
            return
            
        for c in conns:
            row = ctk.CTkFrame(self.conn_scroll, fg_color=THEME["bg_color"], corner_radius=6)
            row.pack(fill="x", pady=2, padx=5)
            row.grid_columnconfigure(0, weight=1)
            
            if beginner:
                text = f"🌐 App '{c['app']}' is talking to {c['host']}"
            else:
                text = f"⚙️ {c['app']} (PID: {c['pid']})   ➔   🌐 {c['host']}  ({c['ip']}:{c['port']})"
                
            ctk.CTkLabel(row, text=text, anchor="w").grid(row=0, column=0, padx=10, pady=8, sticky="w")

    # ── Startup Tab ──────────────────────────────────────────────────────────

class StartupEngineUI(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.startup = StartupManager()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        
        ctk.CTkLabel(top, text="Manage programs that launch automatically when PC boots.", font=FONTS["body"]).pack(side="left", padx=10)
        self.btn_refresh = ctk.CTkButton(top, text="Refresh", width=80, command=self._refresh_startup)
        self.btn_refresh.pack(side="right", padx=10)

        self.start_scroll = ctk.CTkScrollableFrame(self, fg_color="#1a2535")
        self.start_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.after(200, self._refresh_startup)

    def _refresh_startup(self):
        self.btn_refresh.configure(state="disabled", text="⏳ Loading...")
        for w in self.start_scroll.winfo_children(): w.destroy()
        ctk.CTkLabel(self.start_scroll, text="Checking registry for startup keys...\nThis might take a moment.", text_color="gray").pack(pady=20)
        
        def _fetch_in_bg():
            from utils import mode_manager
            beginner = mode_manager.is_beginner()
            apps = self.startup.get_startup_apps()
            self.after(0, lambda: self._render_startup(apps, beginner))
            
        import threading
        threading.Thread(target=_fetch_in_bg, daemon=True).start()

    def _render_startup(self, apps, beginner):
        self.btn_refresh.configure(state="normal", text="Refresh")
        for w in self.start_scroll.winfo_children(): w.destroy()
        
        if not apps:
            ctk.CTkLabel(self.start_scroll, text="No startup apps detected.").pack(pady=20)
            return

        for app in apps:
            row = ctk.CTkFrame(self.start_scroll, fg_color=THEME["bg_color"], corner_radius=6)
            row.pack(fill="x", pady=3, padx=5)
            row.grid_columnconfigure(0, weight=1)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.grid(row=0, column=0, sticky="w", padx=10, pady=8)
            
            ctk.CTkLabel(info_frame, text=app['name'], font=("Roboto Medium", 13)).pack(anchor="w")
            if not beginner:
                ctk.CTkLabel(info_frame, text=app['command'], font=("Roboto", 10), text_color="#888888", wraplength=400).pack(anchor="w")
            
            btn = ctk.CTkButton(
                row, text="Remove", width=70, fg_color="#7a2a2a", hover_color="#9c3232",
                command=lambda a=app, r=row: self._remove_startup(a, r)
            )
            btn.grid(row=0, column=1, padx=15, pady=8)

    def _remove_startup(self, app_dict, row_widget):
        import winreg
        success = self.startup.remove_startup_app(app_dict['name'], app_dict['root'], app_dict['path'])
        if success:
            row_widget.destroy()
        else:
            if app_dict['root'] == winreg.HKEY_LOCAL_MACHINE and not self.startup.is_admin():
                # Notify UI about admin requirements
                for child in row_widget.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        child.configure(text="Need Admin", fg_color=THEME["warning_color"])
