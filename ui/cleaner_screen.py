import customtkinter as ctk
import threading
from ui.styles import THEME, FONTS
from core.cleaner import SystemCleaner

class CleanerScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.cleaner = SystemCleaner()
        self.checkboxes = {} # specific checkboxes map
        
        # --- Title Section ---
        ctk.CTkLabel(self, text="One-Click System Cleaner", font=FONTS["header"]).pack(anchor="w", padx=20, pady=20)
        
        desc = "Safely remove temporary files, cache, and recycle bin items to free up space."
        ctk.CTkLabel(self, text=desc, font=FONTS["body"], text_color="gray").pack(anchor="w", padx=20, pady=(0, 20))

        # --- Options Frame ---
        self.options_frame = ctk.CTkFrame(self, fg_color=THEME["card_color"])
        self.options_frame.pack(fill="x", padx=20, pady=10)
        
        self.items = ["System Temp", "Windows Temp", "Recycle Bin"]
        
        # Create Checkboxes
        for item in self.items:
            row = ctk.CTkFrame(self.options_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=10)
            
            # Checkbox
            var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(row, text=item, variable=var, font=FONTS["subheader"])
            chk.pack(side="left")
            self.checkboxes[item] = {"var": var, "widget": chk}
            
            # Size Label (initially empty)
            size_lbl = ctk.CTkLabel(row, text="Ready to scan", font=FONTS["body"], text_color="gray")
            size_lbl.pack(side="right", padx=10)
            self.checkboxes[item]["label"] = size_lbl

        # --- Action Buttons ---
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=20)

        self.btn_scan = ctk.CTkButton(self.btn_frame, text="Scan Now", width=150, command=self.start_scan)
        self.btn_scan.pack(side="left", padx=10)

        self.btn_clean = ctk.CTkButton(self.btn_frame, text="Clean Selected", width=150, fg_color=THEME["danger_color"], hover_color="#a02020", state="disabled", command=self.start_clean)
        self.btn_clean.pack(side="right", padx=10)

        # Status
        self.status_lbl = ctk.CTkLabel(self, text="", font=("Roboto", 12))
        self.status_lbl.pack(pady=10)

    def start_scan(self):
        self.status_lbl.configure(text="Scanning... Please wait.")
        self.btn_scan.configure(state="disabled")
        # Run in thread so UI doesn't freeze
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        results = self.cleaner.scan_junk()
        
        total_mb = 0
        for item, size_mb in results.items():
            total_mb += size_mb
            # Update UI label safely
            txt = f"{size_mb} MB"
            self.checkboxes[item]["label"].configure(text=txt)
        
        self.status_lbl.configure(text=f"Scan Complete. Found approx {total_mb:.1f} MB of junk.")
        self.btn_scan.configure(state="normal")
        self.btn_clean.configure(state="normal")

    def start_clean(self):
        selected = [k for k, v in self.checkboxes.items() if v["var"].get()]
        if not selected: return

        self.status_lbl.configure(text="Cleaning... Do not close.")
        self.btn_clean.configure(state="disabled")
        
        threading.Thread(target=self._run_clean, args=(selected,), daemon=True).start()

    def _run_clean(self, selected):
        cleaned_mb = self.cleaner.clean_junk(selected)
        self.status_lbl.configure(text=f"Cleanup Complete! Recovered {cleaned_mb} MB of space.")
        self.btn_clean.configure(state="normal")
        # Re-scan to show 0
        self.start_scan()