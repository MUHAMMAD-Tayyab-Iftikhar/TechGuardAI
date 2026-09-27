import customtkinter as ctk
from ui.styles import THEME

class PerformanceCenter(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=THEME["card_color"], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text="🚀 Performance", font=("Roboto Medium", 22)).pack(side="left", padx=20, pady=16)

        # Tabs
        self.tabview = ctk.CTkTabview(self, fg_color=THEME["card_color"])
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        tab_proc = self.tabview.add("Active Applications")
        tab_start = self.tabview.add("Startup Items")

        # Import UI blocks
        from ui.process_screen import ProcessScreen
        from ui.pro_tools_screen import StartupEngineUI

        self.proc = ProcessScreen(tab_proc)
        self.proc.pack(fill="both", expand=True)

        self.start = StartupEngineUI(tab_start)
        self.start.pack(fill="both", expand=True)
