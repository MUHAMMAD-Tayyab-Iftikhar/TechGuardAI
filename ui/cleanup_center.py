import customtkinter as ctk
from ui.styles import THEME

class CleanupCenter(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=THEME["card_color"], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text="🧹 Cleanup Center", font=("Roboto Medium", 22)).pack(side="left", padx=20, pady=16)

        # Tabs
        self.tabview = ctk.CTkTabview(self, fg_color=THEME["card_color"])
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        tab_cleaner = self.tabview.add("System Junk")
        tab_drive = self.tabview.add("Large Files")

        # Import and inject existing screens into tabs
        from ui.cleaner_screen import CleanerScreen
        from ui.drive_analyzer_screen import DriveAnalyzerScreen

        self.cleaner = CleanerScreen(tab_cleaner)
        self.cleaner.pack(fill="both", expand=True)

        self.drive = DriveAnalyzerScreen(tab_drive)
        self.drive.pack(fill="both", expand=True)
