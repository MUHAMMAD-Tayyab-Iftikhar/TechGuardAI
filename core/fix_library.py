"""
fix_library.py
--------------
Local knowledge base of numbered, actionable fix steps for common Windows
problems. No internet connection required.

API
---
    get_fix_for_event(source, event_id)  -> (title, steps) | None
    get_fix_for_symptom(key)             -> (title, steps) | None
    search_fixes(query)                  -> [(title, steps), ...]
    get_all_symptom_fixes()              -> {category: [(key, label), ...]}
"""

# ---------------------------------------------------------------------------
# Event ID Fix Database
# Key: (source_lower_or_None, event_id)
# Value: (title, [step, step, ...])
# ---------------------------------------------------------------------------
_EVENT_FIXES = {

    # ── Power / Stability ────────────────────────────────────────────────────
    (None, 41): (
        "Fix: Unexpected Shutdown (Kernel-Power 41)",
        [
            "Feel if your PC vents are extremely hot — overheating is the #1 cause",
            "Check all power cables are firmly connected at both ends",
            "If on laptop, try a different power adapter",
            "Run a memory test: Start → type 'Memory Diagnostic' → Restart now and check",
            "Open Win+X → Device Manager → right-click each adapter → Update driver",
            "Install Windows updates: Start → Settings → Windows Update → Check for updates",
            "If crashes continue, consider checking the power supply unit (PSU) on a desktop",
        ],
    ),
    (None, 6008): (
        "Fix: Unexpected Restart / Dirty Shutdown",
        [
            "Check if the PC is overheating using TechGuardAI Diagnostics → Thermal Detector",
            "Run memory diagnostics: Start → type 'Memory Diagnostic' → Restart and check",
            "Reseat power cable connections (desktop) or check battery contacts (laptop)",
            "Update all drivers via Win+X → Device Manager",
            "Run SFC scan: TechGuardAI Diagnostics → System File Checker",
            "Disable automatic restart to read BSOD codes: Win+X → System → Advanced system settings → Startup and Recovery → uncheck 'Automatically restart'",
        ],
    ),
    (None, 1001): (
        "Fix: Windows Error Reporting / Crash Logged",
        [
            "Restart your PC — a one-off crash usually resolves itself",
            "Update Windows: Start → Settings → Windows Update",
            "Run SFC scan: TechGuardAI Diagnostics → System File Checker",
            "Check TechGuardAI Diagnostics → Event Log Miner for related errors nearby in time",
        ],
    ),

    # ── Application Crashes ──────────────────────────────────────────────────
    (None, 1000): (
        "Fix: Application Crash (Event 1000)",
        [
            "Right-click the crashed app → Run as administrator (fixes permission issues)",
            "Check the app's website for the latest version and update it",
            "Uninstall and reinstall: Start → Settings → Apps → find app → Uninstall",
            "If a browser crashed, clear cache: Ctrl+Shift+Delete → clear all data",
            "Delete the app's config/data folder in %AppData% or %LocalAppData%",
            "Install Visual C++ Redistributables from Microsoft's website (many apps need these)",
            "Run Windows Update in case a system component the app depends on needs updating",
        ],
    ),
    (None, 1002): (
        "Fix: Application Not Responding / Hanging",
        [
            "Wait 30 seconds — Windows sometimes recovers automatically",
            "Force-close via Ctrl+Shift+Esc → Task Manager → find app → End Task",
            "Increase Virtual Memory: Start → search 'Adjust appearance' → Advanced → Virtual Memory → Change → set to 1.5× your RAM in MB",
            "Update the application to its latest version",
            "If it's a browser, disable extensions one by one to find the culprit",
            "Check if your disk is nearly full — a full disk causes hangs (use TechGuardAI Drive Analyzer)",
        ],
    ),

    # ── File System ──────────────────────────────────────────────────────────
    ("ntfs", 55): (
        "Fix: NTFS File System Corruption (Event 55)",
        [
            "⚠️ IMPORTANT: Back up your important files to an external drive NOW",
            "Press Win+X → Windows Terminal (Admin) or Command Prompt (Admin)",
            "Type exactly: chkdsk C: /f /r  and press Enter (replace C: with affected drive)",
            "Type Y when asked to schedule on next boot, then press Enter",
            "Restart your PC — chkdsk will run before Windows loads (takes 15–60 minutes)",
            "After chkdsk completes, run SFC: TechGuardAI Diagnostics → System File Checker",
            "Run Drive Health scan in TechGuardAI Diagnostics to monitor drive condition",
        ],
    ),
    ("ntfs", 4): (
        "Fix: NTFS Disk Error (Event 4)",
        [
            "Back up important files as a precaution",
            "Press Win+X → Windows Terminal (Admin)",
            "Type: chkdsk C: /f  and press Enter",
            "Type Y to schedule for next boot, then restart",
            "Run Drive Health scan after chkdsk completes",
        ],
    ),

    # ── Services ────────────────────────────────────────────────────────────
    (None, 7034): (
        "Fix: Windows Service Crashed Unexpectedly",
        [
            "Press Win+R, type services.msc, press Enter",
            "Find the service name shown in the event, right-click → Start",
            "If it crashes again, right-click → Properties → Recovery tab",
            "Set 'First failure' to 'Restart the Service' and click OK",
            "If the service is for an installed app (printer, antivirus), reinstall that app",
            "Check Windows Update — service crashes are often fixed by updates",
        ],
    ),
    (None, 7001): (
        "Fix: Service Failed to Start (Dependency Missing)",
        [
            "Press Win+R, type services.msc, press Enter",
            "Find the service and double-click it",
            "Click the 'Dependencies' tab — all listed services must be running first",
            "For each dependency, right-click it in the list → Start",
            "Once all dependencies are running, start the original service",
            "If it still fails, try restarting Windows",
        ],
    ),

    # ── Network ─────────────────────────────────────────────────────────────
    (None, 4202): (
        "Fix: Network Adapter Disconnected",
        [
            "Check your WiFi signal strength or Ethernet cable connection",
            "Right-click network icon in taskbar → Troubleshoot problems",
            "Win+X → Device Manager → Network Adapters → right-click → Update driver",
            "If WiFi drops frequently, set power management to Max Performance: Device Manager → Network Adapter → Properties → Power Management → uncheck 'Allow the computer to turn off this device'",
            "Run: ipconfig /flushdns in Admin Command Prompt",
            "As a last resort: netsh winsock reset in Admin Command Prompt, then restart",
        ],
    ),
    (None, 4201): (
        "Fix: Network Adapter Connected (After Drop)",
        [
            "If your network drops repeatedly, check the cable or WiFi signal",
            "Update the network adapter driver via Device Manager",
            "Disable adapter power saving: Device Manager → Network Adapter → Properties → Power Management → uncheck 'Allow the computer to turn off this device to save power'",
        ],
    ),

    # ── Security ─────────────────────────────────────────────────────────────
    (None, 4625): (
        "Fix: Failed Login Attempt",
        [
            "Check who tried to log in — look at the 'Account Name' in the event details",
            "If you don't recognise the username, change your Windows password immediately",
            "Start → Settings → Accounts → Sign-in options → Change your password",
            "Enable Windows Firewall if disabled: Start → Windows Security → Firewall",
            "Review your saved credentials: Win+R → control /name Microsoft.CredentialManager",
        ],
    ),
    (None, 36888): (
        "Fix: SSL/TLS Handshake Error (Schannel 36888)",
        [
            "Right-click the clock in the taskbar → Adjust date/time — make sure date and time are CORRECT (wrong clock causes SSL errors)",
            "Run Windows Update: Start → Settings → Windows Update → Check for updates",
            "Clear browser cache completely: Ctrl+Shift+Delete → All time → clear all",
            "Reinstall the application causing the error (if app-specific)",
            "Check that Windows Firewall is not blocking the application",
        ],
    ),
    (None, 10010): (
        "Fix: DCOM/Component Timeout Error",
        [
            "This is usually harmless and caused by Microsoft Edge or Office background services",
            "If it appears more than 20 times per day: Run Windows Update",
            "Press Win+R → type dcomcnfg → expand Component Services → My Computer → right-click Properties → Default Properties → set 'Default Authentication Level' to Connect",
            "Restart Windows after making any DCOM changes",
        ],
    ),

    # ── Windows Update ───────────────────────────────────────────────────────
    (None, 20): (
        "Fix: Windows Update Installation Failed",
        [
            "Run the Windows Update Troubleshooter: Start → Settings → System → Troubleshoot → Windows Update",
            "Press Win+R → services.msc → find 'Windows Update' → right-click → Restart",
            "Open Admin Command Prompt and run these in order:",
            "  net stop wuauserv",
            "  net stop bits",
            "  ren C:\\Windows\\SoftwareDistribution SoftwareDistribution.bak",
            "  net start wuauserv",
            "  net start bits",
            "Restart your PC and try updating again",
            "If still failing: DISM /Online /Cleanup-Image /RestoreHealth  in Admin Command Prompt",
        ],
    ),
}


# ---------------------------------------------------------------------------
# Symptom Fix Database
# ---------------------------------------------------------------------------
_SYMPTOM_FIXES = {
    "high_cpu": (
        "Fix: High CPU Usage",
        [
            "Press Ctrl+Shift+Esc to open Task Manager",
            "Click the 'CPU' column header to sort by highest usage",
            "If a browser tops the list, close unused tabs (each tab uses CPU)",
            "Right-click any unknown high process → End Task",
            "Disable startup programs: Task Manager → Startup tab → disable non-essential items",
            "Check for malware: Start → Windows Security → Virus & threat protection → Quick scan",
            "Run Windows Update — many CPU issues are fixed by patches",
            "Restart your PC if uptime is more than 3 days",
        ],
    ),
    "high_ram": (
        "Fix: High Memory / RAM Usage",
        [
            "Close browser tabs you are not using (each can use 50–200 MB)",
            "Press Ctrl+Shift+Esc → click 'Memory' column to find the biggest consumer",
            "Close applications using over 1 GB that you don't need right now",
            "Disable startup programs: Task Manager → Startup → disable unneeded items",
            "Increase Virtual Memory: Start → search 'Adjust appearance' → Advanced → Virtual Memory → Change → set Custom to 1.5× your RAM in MB",
            "Restart your PC to clear cached memory",
            "If this happens constantly, consider upgrading RAM (check your PC's max supported RAM)",
        ],
    ),
    "disk_full": (
        "Fix: Storage Drive Almost Full",
        [
            "Open TechGuardAI → Drive Analyzer to find and delete large unused files",
            "Empty the Recycle Bin: right-click Recycle Bin on desktop → Empty Recycle Bin",
            "Delete files in Downloads folder you no longer need",
            "Run TechGuardAI → System Cleaner to remove temp files",
            "Uninstall unused apps: Start → Settings → Apps → sort by Size",
            "Move large files (videos, photos) to an external drive or cloud (OneDrive, Google Drive)",
            "Use Disk Cleanup: Start → type 'Disk Cleanup' → select C: → also click 'Clean up system files'",
        ],
    ),
    "slow_boot": (
        "Fix: PC Boots Slowly",
        [
            "Disable startup programs: Ctrl+Shift+Esc → Startup tab → disable non-essential items",
            "Enable Fast Startup: Start → Control Panel → Power Options → 'Choose what power buttons do' → Turn on fast startup",
            "Run TechGuardAI → System Cleaner to free up disk space",
            "Check if Windows Update is running in the background (expected after updates)",
            "Run TechGuardAI Diagnostics → Drive Health — slow boot may indicate a failing drive",
            "Run SFC: TechGuardAI Diagnostics → System File Checker",
            "If PC takes over 3 minutes to boot, back up files — drive may be failing",
        ],
    ),
    "no_internet": (
        "Fix: No Internet Connection",
        [
            "Restart your router: unplug it, wait 10 seconds, plug it back in",
            "Right-click the network icon in the taskbar → Troubleshoot problems",
            "Run TechGuardAI chatbot and ask it to flush DNS (or open Admin Command Prompt and type: ipconfig /flushdns)",
            "Press Win+R → type ncpa.cpl → right-click your connection → Disable, then Enable",
            "Update network driver: Win+X → Device Manager → Network Adapters → right-click → Update driver",
            "Reset network stack (Admin Command Prompt): netsh winsock reset → restart PC",
            "Connect a different device to the same network — if it also fails, the issue is the router/ISP",
        ],
    ),
    "overheating": (
        "Fix: PC Overheating / Thermal Throttling",
        [
            "Turn off the PC, then use a can of compressed air to blow dust out of all vents",
            "Ensure at least 15 cm of clear space around all vents — never block them",
            "On a laptop: always use on a hard flat surface, never on a bed or pillow",
            "Check that all fans are spinning (you should feel airflow)",
            "Consider a laptop cooling pad for extended heavy use",
            "If you built your own desktop: check that thermal paste is applied on the CPU and the CPU cooler is seated properly",
            "Monitor temperatures over time using TechGuardAI Diagnostics → Thermal Detector",
        ],
    ),
    "slow_pc": (
        "Fix: PC Running Slowly",
        [
            "Restart your PC — this alone fixes most slowness",
            "Check TechGuardAI Dashboard — see if CPU or Memory is in the 🔴 red zone",
            "Close browser tabs you are not actively using",
            "Run TechGuardAI System Cleaner to remove junk files",
            "Disable startup programs: Ctrl+Shift+Esc → Startup tab",
            "Run a malware scan: Start → Windows Security → Quick scan",
            "Check Drive Health in TechGuardAI Diagnostics — a failing drive causes extreme slowness",
        ],
    ),
    "blue_screen": (
        "Fix: Blue Screen of Death (BSOD)",
        [
            "Note the error code shown (e.g. MEMORY_MANAGEMENT, IRQL_NOT_LESS_OR_EQUAL, PAGE_FAULT)",
            "Restart your PC — a one-time BSOD is often not serious",
            "Run memory test: Start → type 'Memory Diagnostic' → Restart now and check for problems",
            "Run SFC: TechGuardAI Diagnostics → System File Checker",
            "Check Event Log: TechGuardAI Diagnostics → Event Log Miner — look for entries near crash time",
            "Update all drivers: Win+X → Device Manager → for each category, right-click → Update driver",
            "Update Windows: Start → Settings → Windows Update",
            "If BSODs are frequent, your RAM or hard drive may be failing — check Drive Health & RAM",
        ],
    ),
    "pc_restart_randomly": (
        "Fix: PC Restarting Randomly / Spontaneously",
        [
            "Check for overheating using TechGuardAI Diagnostics → Thermal Detector",
            "Run memory test: Start → type 'Memory Diagnostic' → Restart now",
            "Reseat all power cables inside your desktop PC (if applicable)",
            "Update display driver and chipset drivers via Device Manager",
            "Disable automatic restart to read BSOD errors: Win+X → System → Advanced system settings → Startup and Recovery → uncheck 'Automatically restart'",
            "Check TechGuardAI Event Log for Kernel-Power Event ID 41 entries",
            "Run SFC: TechGuardAI Diagnostics → System File Checker",
        ],
    ),
    "printer_not_working": (
        "Fix: Printer Not Working",
        [
            "Check the printer is powered on and the cable (or WiFi) is connected",
            "Run the printer troubleshooter: Start → Settings → System → Troubleshoot → Printer",
            "Restart the Print Spooler service: Win+R → services.msc → find 'Print Spooler' → right-click → Restart",
            "Remove and re-add the printer: Start → Settings → Bluetooth & devices → Printers → Remove → Add device",
            "Download and install the latest printer driver from the manufacturer's website",
            "Try printing a test page from printer properties to isolate the issue",
        ],
    ),
    "audio_not_working": (
        "Fix: No Sound / Audio Not Working",
        [
            "Right-click the speaker icon in the taskbar → Sound settings",
            "Make sure the correct output device is selected (speakers vs headphones vs monitor speakers)",
            "Check the volume is not muted — there are separate hardware, system, and app volume controls",
            "Right-click the speaker icon → Troubleshoot sound problems",
            "Update the audio driver: Win+X → Device Manager → Sound, video and game controllers → right-click → Update driver",
            "Restart Windows Audio: Win+R → services.msc → 'Windows Audio' → right-click → Restart",
        ],
    ),
    "windows_update_failed": (
        "Fix: Windows Update Failed or Stuck",
        [
            "Run the Windows Update troubleshooter: Start → Settings → System → Troubleshoot → Windows Update",
            "Restart the update service: Win+R → services.msc → 'Windows Update' → right-click → Restart",
            "Clear update cache (Admin Command Prompt, run each line):",
            "  net stop wuauserv  →  net stop bits  →  ren C:\\Windows\\SoftwareDistribution SoftwareDistribution.bak  →  net start wuauserv  →  net start bits",
            "Restart and try Windows Update again",
            "If still failing, run in Admin Command Prompt: DISM /Online /Cleanup-Image /RestoreHealth",
            "Then run: sfc /scannow  (or use TechGuardAI Diagnostics → System File Checker)",
        ],
    ),
    "wifi_slow": (
        "Fix: WiFi Running Slowly",
        [
            "Move closer to the router — WiFi signal degrades quickly through walls",
            "Restart the router: unplug, wait 10 seconds, plug back in",
            "Check if many devices are using the same network simultaneously",
            "Change the WiFi channel on your router (use channel 1, 6, or 11 for 2.4GHz)",
            "Consider switching to a 5GHz WiFi network if your router supports it (faster but shorter range)",
            "Update the network adapter driver: Win+X → Device Manager → Network Adapters → Update driver",
            "Disable VPN temporarily if you are using one — VPNs reduce speeds",
        ],
    ),
    "pc_wont_wake": (
        "Fix: PC Won't Wake from Sleep",
        [
            "Press any keyboard key or click the mouse to wake",
            "If unresponsive, hold the power button for 5 seconds to force restart",
            "Change sleep settings: Win+X → Device Manager → keyboards and mice → Properties → Power Management → uncheck 'Allow computer to turn off this device'",
            "Update chipset drivers from your PC/motherboard manufacturer's website",
            "Run: powercfg /energy  in Admin Command Prompt to see power issues",
            "Disable hybrid sleep: Start → Power Options → Change plan settings → Change advanced → Sleep → allow hybrid sleep → Off",
        ],
    ),
}

# Symptom browse categories (ordered)
_CATEGORIES = {
    "⚡ Performance": [
        ("high_cpu",   "High CPU Usage"),
        ("high_ram",   "High Memory / RAM Usage"),
        ("slow_pc",    "PC Running Slowly"),
        ("slow_boot",  "Slow Boot / Startup"),
        ("overheating","PC Overheating / Thermal Throttling"),
    ],
    "💾 Storage": [
        ("disk_full", "Storage Drive Almost Full"),
    ],
    "🌐 Network": [
        ("no_internet", "No Internet Connection"),
        ("wifi_slow",   "WiFi Running Slowly"),
    ],
    "💥 Crashes": [
        ("blue_screen",         "Blue Screen of Death (BSOD)"),
        ("pc_restart_randomly", "PC Restarting Randomly"),
        ("pc_wont_wake",        "PC Won't Wake from Sleep"),
    ],
    "🔧 Hardware": [
        ("printer_not_working", "Printer Not Working"),
        ("audio_not_working",   "No Sound / Audio Not Working"),
    ],
    "🪟 Windows": [
        ("windows_update_failed", "Windows Update Failed"),
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_fix_for_event(source: str, event_id: int):
    """
    Returns (title, steps) for a known Windows Event ID, or None.
    Tries (source_lower, event_id) first, then (None, event_id).
    """
    src = (source or "").lower()
    result = _EVENT_FIXES.get((src, event_id))
    if result:
        return result
    return _EVENT_FIXES.get((None, event_id))


def get_fix_for_symptom(key: str):
    """
    Returns (title, steps) for a known symptom key, or None.
    """
    return _SYMPTOM_FIXES.get(key)


def search_fixes(query: str) -> list:
    """
    Case-insensitive search across all fix titles and steps.
    Returns up to 8 matching (title, steps) tuples.
    """
    q = query.lower().strip()
    if not q:
        return []
    seen   = set()
    results = []

    def _check(title, steps):
        if title in seen:
            return
        if q in title.lower() or any(q in s.lower() for s in steps):
            seen.add(title)
            results.append((title, steps))

    for (_, _), (title, steps) in _EVENT_FIXES.items():
        _check(title, steps)
        if len(results) >= 8:
            break

    for _, (title, steps) in _SYMPTOM_FIXES.items():
        _check(title, steps)
        if len(results) >= 8:
            break

    return results


def get_all_symptom_fixes() -> dict:
    """Returns the ordered category browse structure."""
    return _CATEGORIES
