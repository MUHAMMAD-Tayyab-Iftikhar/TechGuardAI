import customtkinter as ctk
from ui.styles import THEME

class FixesCenter(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=THEME["card_color"], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text="🛠️ Diagnostics & Fixes", font=("Roboto Medium", 22)).pack(side="left", padx=20, pady=16)

        # Tabs
        self.tabview = ctk.CTkTabview(self, fg_color=THEME["card_color"])
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        tab_diag = self.tabview.add("Health Scans")
        tab_fix = self.tabview.add("Error Fix Center")
        tab_upd = self.tabview.add("Software Updater")

        # Import UI blocks
        from ui.diagnostics_screen import DiagnosticsScreen
        from ui.fix_center import FixCenterScreen
        from ui.pro_tools_screen import UpdaterEngineUI

        self.diag = DiagnosticsScreen(tab_diag)
        self.diag.pack(fill="both", expand=True)

        self.fix = FixCenterScreen(tab_fix)
        self.fix.pack(fill="both", expand=True)

        self.upd = UpdaterEngineUI(tab_upd)
        self.upd.pack(fill="both", expand=True)
