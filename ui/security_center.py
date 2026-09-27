import customtkinter as ctk
from ui.styles import THEME

class SecurityCenter(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=THEME["card_color"], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text="🛡️ Security & Privacy", font=("Roboto Medium", 22)).pack(side="left", padx=20, pady=16)

        # Tabs
        self.tabview = ctk.CTkTabview(self, fg_color=THEME["card_color"])
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        tab_threat = self.tabview.add("Threat Scanner")
        tab_net = self.tabview.add("Network & Telemetry")

        # Import UI blocks
        from ui.security_screen import SecurityScreen
        from ui.pro_tools_screen import PrivacyEngineUI

        self.threat = SecurityScreen(tab_threat)
        self.threat.pack(fill="both", expand=True)

        self.net = PrivacyEngineUI(tab_net)
        self.net.pack(fill="both", expand=True)
