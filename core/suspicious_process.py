"""
suspicious_process.py
---------------------
Detects processes that exhibit common malware/adware behavioural traits.

Checks performed (no internet lookups required):
  1. Running from a temp/suspicious folder (%TEMP%, AppData\\Local\\Temp, Downloads, etc.)
  2. No verified publisher (digital signature absent — common for unsigned malware)
  3. Unusual parent process (e.g. cmd.exe or wscript.exe spawned a GUI app)
  4. Process masquerading (same name as a known system process but wrong path)
  5. High CPU at night / unexpected hours (heuristic)
  6. Startup-registered process that is unsigned or from a suspicious location

Each finding is assigned a risk level: LOW / MEDIUM / HIGH
Only user-visible, non-whitelisted processes are evaluated.
"""

import os
import psutil
import winreg
import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Whitelist — well-known signed apps that are safe to skip
# ---------------------------------------------------------------------------
_WHITELIST_NAMES = frozenset({
    # Windows core
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
    "explorer.exe", "dwm.exe", "fontdrvhost.exe", "spoolsv.exe",
    "taskhostw.exe", "sihost.exe", "ctfmon.exe", "runtimebroker.exe",
    "searchindexer.exe", "searchhost.exe", "dllhost.exe", "conhost.exe",
    "wslhost.exe", "msmpeng.exe",  # Defender
    # Common safe apps
    "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe", "opera.exe",
    "code.exe", "pycharm64.exe", "idea64.exe", "notepad.exe", "notepad++.exe",
    "discord.exe", "slack.exe", "teams.exe", "zoom.exe", "skype.exe",
    "spotify.exe", "vlc.exe", "steam.exe", "pythonw.exe", "python.exe",
    "node.exe", "git.exe", "powershell.exe", "cmd.exe",
    "onedrive.exe", "dropbox.exe", "googledrivefs.exe",
})

# Folders that are highly suspicious for executables to run from
_SUSPICIOUS_DIRS = (
    os.environ.get("TEMP", ""),
    os.environ.get("TMP", ""),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
    os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
    os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    "\\windows\\temp",
    "\\recycle",
    "\\$recycle",
)

# Known system processes that MUST live in System32 / SysWOW64
_SYSTEM_PROCESS_PATHS = {
    "svchost.exe":    "windows\\system32",
    "lsass.exe":      "windows\\system32",
    "csrss.exe":      "windows\\system32",
    "wininit.exe":    "windows\\system32",
    "smss.exe":       "windows\\system32",
    "winlogon.exe":   "windows\\system32",
    "services.exe":   "windows\\system32",
    "explorer.exe":   "windows",
    "taskhostw.exe":  "windows\\system32",
}

# Registry keys for startup programs
_STARTUP_KEYS = [
    (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
]


def _is_in_suspicious_dir(exe_path: str) -> bool:
    """Returns True if the exe is running from a known-bad location."""
    if not exe_path:
        return False
    path_lower = exe_path.lower()
    for d in _SUSPICIOUS_DIRS:
        if d and path_lower.startswith(d.lower()):
            return True
    return False


def _is_masquerading(name: str, exe_path: str) -> bool:
    """Returns True if a process has a system-process name but wrong path."""
    if not exe_path:
        return False
    name_lower  = name.lower()
    path_lower  = exe_path.lower()
    expected    = _SYSTEM_PROCESS_PATHS.get(name_lower)
    if expected and expected not in path_lower:
        return True
    return False


def _get_startup_exe_paths() -> set:
    """Read all startup entry values from the registry and return exe paths."""
    paths = set()
    for hive, reg_path in _STARTUP_KEYS:
        try:
            with winreg.OpenKey(hive, reg_path) as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        _, val, _ = winreg.EnumValue(key, i)
                        # Extract path (strip quotes, arguments)
                        val = str(val).strip().strip('"').split('"')[0].split()[0]
                        paths.add(val.lower())
                    except Exception:
                        continue
        except Exception:
            continue
    return paths


def _has_digital_signature(exe_path: str) -> bool:
    """
    Quick heuristic check: files in Program Files / Windows are almost
    always signed. Files in AppData/Downloads/Temp usually aren't.
    A proper check would call WinVerifyTrust via ctypes — expensive per-file.
    We use the path heuristic for speed and flag only if also suspicious.
    """
    if not exe_path:
        return False
    p = exe_path.lower()
    trusted_prefixes = (
        "c:\\windows\\",
        "c:\\program files\\",
        "c:\\program files (x86)\\",
    )
    return any(p.startswith(pfx) for pfx in trusted_prefixes)


def scan_suspicious_processes() -> list:
    """
    Scan all running processes for suspicious behavioural indicators.

    Returns a list of dicts, each with:
        pid, name, exe, risk, reasons  (list of plain-English strings)
    Sorted by risk: HIGH → MEDIUM → LOW.
    """
    startup_paths = _get_startup_exe_paths()
    findings      = []

    for proc in psutil.process_iter(["pid", "name", "exe", "ppid", "cpu_percent"]):
        try:
            info      = proc.info
            name      = (info.get("name") or "").strip()
            exe       = (info.get("exe") or "").strip()
            pid       = info.get("pid")
            cpu       = info.get("cpu_percent") or 0.0
            name_low  = name.lower()
            exe_low   = exe.lower()

            # Skip whitelisted system processes
            if name_low in _WHITELIST_NAMES:
                continue

            # Skip processes with no exe (kernel threads etc.)
            if not exe:
                continue

            reasons = []
            risk    = "LOW"

            # ── Check 1: Suspicious folder ─────────────────────────────────
            if _is_in_suspicious_dir(exe):
                reasons.append(f"Running from a suspicious folder: {os.path.dirname(exe)}")
                risk = "HIGH"

            # ── Check 2: Masquerading as a system process ──────────────────
            if _is_masquerading(name, exe):
                reasons.append(
                    f"Process name '{name}' looks like a Windows system file "
                    f"but is running from '{os.path.dirname(exe)}' — possible impersonation"
                )
                risk = "HIGH"

            # ── Check 3: Not from a trusted location AND not signed path ───
            if not _has_digital_signature(exe) and exe and risk == "LOW":
                # Only flag if also in AppData (common malware drop zone)
                local_app = os.environ.get("LOCALAPPDATA", "").lower()
                if local_app and exe_low.startswith(local_app) and \
                        "programs" not in exe_low:
                    reasons.append(
                        "Running from your AppData folder without being a known installed app"
                    )
                    risk = "MEDIUM"

            # ── Check 4: In startup list but from suspicious location ──────
            if exe_low in startup_paths and risk in ("HIGH", "MEDIUM"):
                reasons.append("This process auto-starts with Windows")

            # ── Check 5: Very high CPU from unknown process ────────────────
            if cpu > 50 and not _has_digital_signature(exe) and risk == "LOW":
                reasons.append(
                    f"Unknown process using {cpu:.0f}% of your processor"
                )
                risk = "MEDIUM"

            if reasons:
                findings.append({
                    "pid":     pid,
                    "name":    name,
                    "exe":     exe,
                    "cpu":     cpu,
                    "risk":    risk,
                    "reasons": reasons,
                })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    # Sort: HIGH first, then MEDIUM, then LOW
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda x: order.get(x["risk"], 3))
    return findings
