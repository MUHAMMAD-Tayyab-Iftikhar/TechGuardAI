"""
security_screen.py
------------------
Suspicious Process Detector UI screen.

Shows a scannable list of processes flagged for suspicious behaviour,
with risk badges (HIGH / MEDIUM / LOW), plain-English reasons,
and a one-click Kill button for each flagged process.
"""

import threading
import psutil
import customtkinter as ctk
from ui.styles import THEME, FONTS
from core.suspicious_process import scan_suspicious_processes
from utils import mode_manager

# Colour tokens for risk levels
RISK_COLORS = {
    "HIGH":   ("#cf352e", "#3d1010", "🚨"),   # (accent, bg, icon)
    "MEDIUM": ("#f1c40f", "#3a3010", "⚠️"),
    "LOW":    ("#1f6aa5", "#1a2535", "🔵"),
}


class SecurityScreen(ctk.CTkFrame):
    """Suspicious Process Detector — full screen."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header card ──
        header = ctk.CTkFrame(self, fg_color=THEME["card_color"], corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="🔍  Suspicious Process Detector",
            font=("Roboto Medium", 22),
        ).grid(row=0, column=0, padx=20, pady=(14, 2), sticky="w")

        ctk.CTkLabel(
            header,
            text="Scans running processes for malware-like behaviour — no internet needed.",
            font=FONTS["body"],
            text_color="#888888",
        ).grid(row=1, column=0, padx=20, pady=(0, 14), sticky="w")

        self.scan_btn = ctk.CTkButton(
            header,
            text="🔍  Scan Now",
            width=160,
            height=38,
            fg_color=THEME["accent_color"],
            hover_color="#145a8a",
            font=("Roboto Medium", 13, "bold"),
            command=self._start_scan,
        )
        self.scan_btn.grid(row=0, column=2, rowspan=2, padx=20, pady=14, sticky="e")

        # Status / summary strip
        self.summary_lbl = ctk.CTkLabel(
            header,
            text="Click 'Scan Now' to check your running processes.",
            font=FONTS["small"],
            text_color="#666666",
        )
        self.summary_lbl.grid(row=2, column=0, columnspan=3, padx=20, pady=(0, 10), sticky="w")

        # ── Scrollable results area ──
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.scroll.grid_columnconfigure(0, weight=1)

        # Placeholder
        self.placeholder = ctk.CTkLabel(
            self.scroll,
            text="No scan run yet.\nClick  ⬆  Scan Now  to check your PC for suspicious processes.",
            font=FONTS["body"],
            text_color="#555555",
            justify="center",
        )
        self.placeholder.grid(row=0, column=0, pady=60)

    # ── Scan logic ────────────────────────────────────────────────────────────

    def _start_scan(self):
        self.scan_btn.configure(state="disabled", text="⏳  Scanning…")
        self.summary_lbl.configure(text="Scanning processes…", text_color=THEME["accent_color"])
        self._clear_results()
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        findings = scan_suspicious_processes()
        self.after(0, lambda: self._show_results(findings))

    # ── Results rendering ─────────────────────────────────────────────────────

    def _clear_results(self):
        for w in self.scroll.winfo_children():
            w.destroy()

    def _show_results(self, findings: list):
        self._clear_results()
        self.scan_btn.configure(state="normal", text="🔍  Scan Now")

        beginner = mode_manager.is_beginner()

        if not findings:
            # ── All Clear ──
            self.summary_lbl.configure(
                text="✅  No suspicious processes found — your PC looks clean!",
                text_color=THEME["success_color"],
            )
            ok_card = ctk.CTkFrame(self.scroll, fg_color="#1a3325", corner_radius=10)
            ok_card.grid(row=0, column=0, sticky="ew", padx=4, pady=8)
            ctk.CTkLabel(
                ok_card,
                text="✅  All Clear — No suspicious processes detected",
                font=("Roboto Medium", 14),
                text_color=THEME["success_color"],
            ).pack(padx=20, pady=16)
            return

        # Count by risk
        high   = sum(1 for f in findings if f["risk"] == "HIGH")
        medium = sum(1 for f in findings if f["risk"] == "MEDIUM")
        low    = sum(1 for f in findings if f["risk"] == "LOW")

        if beginner:
            if high:
                summary = f"🚨 Found {high} serious concern(s) and {medium + low} minor one(s) — review below"
            else:
                summary = f"⚠️ Found {medium + low} item(s) worth checking — review below"
        else:
            summary = (f"Found {len(findings)} flagged process(es) — "
                       f"HIGH: {high}  MEDIUM: {medium}  LOW: {low}")

        self.summary_lbl.configure(
            text=summary,
            text_color=THEME["danger_color"] if high else THEME["warning_color"],
        )

        for i, finding in enumerate(findings):
            self._build_finding_card(finding, row=i, beginner=beginner)

        # Disclaimer at bottom
        ctk.CTkLabel(
            self.scroll,
            text=(
                "ℹ️  This scan uses behavioural rules, not a virus signature database. "
                "A flagged process is not necessarily malware — investigate before killing it."
            ),
            font=FONTS["small"],
            text_color="#555555",
            wraplength=700,
            justify="left",
        ).grid(row=len(findings), column=0, padx=10, pady=(8, 4), sticky="w")

    def _build_finding_card(self, f: dict, row: int, beginner: bool):
        """Renders one flagged process as a styled card."""
        risk   = f["risk"]
        accent, bg, icon = RISK_COLORS.get(risk, RISK_COLORS["LOW"])

        card = ctk.CTkFrame(self.scroll, fg_color=bg, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=4, pady=5)
        card.grid_columnconfigure(1, weight=1)

        # Left colour bar
        ctk.CTkFrame(card, width=5, fg_color=accent, corner_radius=3).grid(
            row=0, column=0, rowspan=10, sticky="ns", padx=(6, 0), pady=8
        )

        # Risk badge + process name
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=1, sticky="ew", padx=(10, 8), pady=(10, 2))
        top.grid_columnconfigure(1, weight=1)

        badge_text = {"HIGH": "SERIOUS", "MEDIUM": "SUSPICIOUS", "LOW": "MINOR"}.get(risk, risk) if beginner else risk
        badge = ctk.CTkLabel(
            top,
            text=f" {icon}  {badge_text} ",
            font=("Roboto Medium", 11, "bold"),
            fg_color=accent,
            text_color="white" if risk != "MEDIUM" else "black",
            corner_radius=6,
        )
        badge.grid(row=0, column=0, sticky="w")

        # Process name (friendly in beginner mode)
        if beginner:
            display_name = self._friendly_name(f["name"])
            ctk.CTkLabel(top, text=display_name,
                         font=("Roboto Medium", 14), anchor="w").grid(
                row=0, column=1, sticky="w", padx=(10, 0))
        else:
            ctk.CTkLabel(top, text=f["name"],
                         font=("Roboto Medium", 14, "bold"), anchor="w").grid(
                row=0, column=1, sticky="w", padx=(10, 0))
            ctk.CTkLabel(top, text=f"PID: {f['pid']}",
                         font=FONTS["small"], text_color="#777777").grid(
                row=0, column=2, sticky="e", padx=(0, 4))

        # Reasons
        reasons_frame = ctk.CTkFrame(card, fg_color="transparent")
        reasons_frame.grid(row=1, column=1, sticky="ew", padx=(10, 8), pady=(0, 4))

        for r_text in f["reasons"]:
            display = self._simplify_reason(r_text) if beginner else r_text
            ctk.CTkLabel(
                reasons_frame,
                text=f"  •  {display}",
                font=FONTS["body"],
                text_color="#cccccc",
                anchor="w",
                justify="left",
                wraplength=640,
            ).pack(anchor="w")

        # Exe path (expert only)
        if not beginner and f.get("exe"):
            ctk.CTkLabel(
                reasons_frame,
                text=f"  📂  {f['exe']}",
                font=FONTS["small"],
                text_color="#666666",
                anchor="w",
                wraplength=640,
            ).pack(anchor="w", pady=(2, 0))

        # CPU usage
        if f.get("cpu", 0) > 0:
            cpu_lbl = f"Using {f['cpu']:.0f}% processor" if beginner else f"CPU: {f['cpu']:.1f}%"
            ctk.CTkLabel(
                reasons_frame,
                text=f"  ⚙️  {cpu_lbl}",
                font=FONTS["small"],
                text_color="#888888",
            ).pack(anchor="w")

        # Action buttons row
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=2, column=1, sticky="e", padx=(8, 12), pady=(2, 10))

        kill_label = "End This Program" if beginner else f"Kill PID {f['pid']}"
        ctk.CTkButton(
            btn_row,
            text=f"🛑  {kill_label}",
            width=160,
            height=30,
            fg_color="#8B1A1A",
            hover_color="#a02020",
            font=("Roboto Medium", 12),
            command=lambda pid=f["pid"], name=f["name"]: self._kill_process(pid, name),
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            btn_row,
            text="Ignore",
            width=80,
            height=30,
            fg_color="#333333",
            hover_color="#3d3d3d",
            font=FONTS["body"],
            command=card.destroy,
        ).pack(side="right")

    def _kill_process(self, pid: int, name: str):
        """Terminates a process and shows result."""
        from tkinter import messagebox
        confirm = messagebox.askyesno(
            "Confirm End Process",
            f"Are you sure you want to end:\n\n{name}  (PID {pid})\n\n"
            "This will immediately close the program. Unsaved work may be lost.",
            icon="warning",
        )
        if not confirm:
            return
        try:
            p = psutil.Process(pid)
            p.terminate()
            self.summary_lbl.configure(
                text=f"✅  {name} (PID {pid}) has been ended.",
                text_color=THEME["success_color"],
            )
            # Re-scan after 1.5s so removed process disappears from list
            self.after(1500, self._start_scan)
        except psutil.NoSuchProcess:
            messagebox.showinfo("Not Found", f"{name} is no longer running.")
        except psutil.AccessDenied:
            messagebox.showerror("Access Denied",
                                 f"Could not end {name}.\n\nTry running TechGuardAI as Administrator.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Plain-English helpers ─────────────────────────────────────────────────

    @staticmethod
    def _friendly_name(proc_name: str) -> str:
        """Maps exe names to friendlier display names where known."""
        known = {
            "powershell.exe": "PowerShell (command runner)",
            "cmd.exe":        "Command Prompt",
            "wscript.exe":    "Windows Script Host",
            "mshta.exe":      "HTML Application Host",
            "regsvr32.exe":   "DLL Registration Tool",
            "rundll32.exe":   "DLL Runner",
        }
        return known.get(proc_name.lower(), proc_name)

    @staticmethod
    def _simplify_reason(reason: str) -> str:
        """Makes technical reason strings friendlier for beginners."""
        if "suspicious folder" in reason or "temp" in reason.lower():
            return "Running from a temporary folder (unusual for normal apps)"
        if "masquerad" in reason or "impersonat" in reason:
            return "This program has the same name as a Windows system file but is in the wrong place"
        if "AppData folder" in reason:
            return "Running from a hidden app data folder — not a normal installation location"
        if "auto-starts" in reason or "auto-start" in reason:
            return "This program starts automatically every time you turn on your PC"
        if "processor" in reason or "CPU" in reason:
            return "Using a large amount of your processor without a clear reason"
        return reason
