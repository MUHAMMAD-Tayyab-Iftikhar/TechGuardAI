import customtkinter as ctk
from ui.styles import THEME, FONTS
from core.process_analyzer import ProcessAnalyzer
from utils import mode_manager

# Shared monospace font — MUST be identical for header and data rows
# so that fixed-width string padding (:<38 etc.) maps to the same pixels.
_TABLE_FONT = ("Consolas", 13)


class ProcessScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.proc_analyzer = ProcessAnalyzer()

        # Title
        ctk.CTkLabel(self, text="Active Process Manager", font=FONTS["header"]).pack(anchor="w", padx=20, pady=20)

        # Table Header — same font as data rows so columns line up perfectly
        self.header_frame = ctk.CTkFrame(self, fg_color=THEME["card_color"])
        self.header_frame.pack(fill="x", padx=20)
        self.header_lbl = ctk.CTkLabel(
            self.header_frame, text="",
            font=_TABLE_FONT,
            anchor="w",
        )
        self.header_lbl.pack(padx=10, pady=8, anchor="w")

        # Scrollable Area for Processes
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.proc_labels = ctk.CTkLabel(
            self.scroll_frame, text="Loading...",
            font=_TABLE_FONT,
            justify="left", anchor="nw",
        )
        self.proc_labels.pack(fill="both", expand=True)

        # Refresh Button
        self.refresh_btn = ctk.CTkButton(self, text="Refresh List", command=self.update_process_list)
        self.refresh_btn.pack(pady=20)

        # Initial Load deferred after mainloop
        self.after(200, self.update_process_list)

    def update_process_list(self):
        self.refresh_btn.configure(state="disabled", text="⏳ Loading...")
        self.proc_labels.configure(text="Scanning system processes...\nThis might take a moment.", text_color="gray")

        def _fetch_in_bg():
            top_apps = self.proc_analyzer.get_top_processes(sort_by='memory', limit=15)
            beginner = mode_manager.is_beginner()
            self.after(0, lambda: self._render_process_list(top_apps, beginner))

        import threading
        threading.Thread(target=_fetch_in_bg, daemon=True).start()

    def _render_process_list(self, top_apps, beginner):
        self.refresh_btn.configure(state="normal", text="Refresh List")
        self.proc_labels.configure(text_color=THEME.get("text_color", "#e0e0e0"))

        if beginner:
            self.header_lbl.configure(text=f"{'Background Application':<38}  {'Impact on PC':<12}")
        else:
            self.header_lbl.configure(text=f"{'PID':<8}  {'Process Name':<32}  {'Memory Usage':<12}")

        display_text = ""
        for app in top_apps:
            name = app['name'][:28] + "..." if len(app['name']) > 28 else app['name']

            if beginner:
                if app['usage'] > 500:   impact = "Heavy"
                elif app['usage'] > 150: impact = "Medium"
                else:                    impact = "Light"
                display_text += f"{name:<38}  {impact:<12}\n\n"
            else:
                display_text += f"{str(app['pid']):<8}  {name:<32}  {app['usage']:.1f} MB\n\n"

        self.proc_labels.configure(text=display_text)