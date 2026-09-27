import win32evtlog
import win32evtlogutil
import win32con
import datetime
import re
import pywintypes

# Events that are noisy, harmless, and should be silently skipped
NOISY_EVENT_IDS = {
    10016,  # DCOM permission — harmless Windows quirk, not user-relevant
    1014,   # DNS Client warning — usually harmless slow DNS
    5781,   # NetLogon — common on home networks without a domain
    36888,  # SChannel — SSL negotiation failures (very common, rarely an issue)
    4202,   # Wireless adapter disconnected — happens on every standby/resume
    4201,   # Wireless adapter connected — informational noise
}

# Known Windows Event IDs and their plain-English meaning
KNOWN_EVENT_IDS = {
    # System Events
    41:   ("Kernel Power — Unexpected Shutdown", "Your PC lost power or rebooted without warning. Possible causes: power outage, overheating shutdown, or a driver crash. Check your power supply and temperatures.", "Critical"),
    1001: ("Windows Error Recovery", "Windows recovered from an unexpected failure. This often follows a Blue Screen of Death.", "Critical"),
    6008: ("Unexpected Shutdown", "Windows was not shut down properly. Could be a crash, power loss, or forced restart.", "Warning"),
    6006: ("Clean Shutdown", "System was shut down normally.", "OK"),
    7034: ("Service Crashed Unexpectedly", "A Windows service terminated unexpectedly. This can cause app instability.", "Warning"),
    7031: ("Service Terminated Unexpectedly", "A Windows service crashed and may have been restarted.", "Warning"),
    7023: ("Service Failed to Start", "A critical Windows service could not start, which may affect system functions.", "Warning"),
    7000: ("Service Failed to Start (Config Error)", "A service could not start due to a configuration or file error.", "Warning"),
    55:   ("NTFS File System Corruption Detected", "The NTFS file system detected corruption on a volume. Run 'chkdsk /f' immediately to prevent data loss.", "Critical"),
    50:   ("NTFS Log File Failure", "NTFS could not write to the volume log file. This can lead to data corruption.", "Critical"),
    4:    ("Driver Memory Corruption", "A driver has been detected corrupting memory. This is a common cause of Blue Screens.", "Critical"),
    
    # Application Errors
    1000: ("Application Crash", "An application crashed unexpectedly. This is usually caused by a bug in the app, corrupted files, or a missing update. Try reinstalling the app if it keeps happening.", "Warning"),
    1002: ("Application Hang / Freeze", "An app froze and stopped responding. Windows had to force-close it. If this happens often, the app may need to be updated or reinstalled.", "Warning"),
    1026: (".NET Runtime Error", "A Windows (.NET) application crashed. This can be caused by a corrupted Windows component. Run 'sfc /scannow' in an admin command prompt to fix it.", "Warning"),

    # Windows Licensing / Activation
    8198: ("Windows License Activation Failed", "Windows could not verify its license with Microsoft's servers. This may affect some features. Check your internet connection or re-enter your product key in Settings > Activation.", "Warning"),
    8200: ("Windows License Check Failed", "Windows tried to verify your license automatically and failed. This is often a temporary network issue and usually self-resolves.", "Warning"),

    # Network
    27:   ("Network Adapter Disconnected", "Your network adapter lost its connection. This may explain brief internet drops. Could be a loose cable, driver issue, or power saving setting turning off the adapter.", "Warning"),

    # Disk issues
    7:    ("Disk I/O Error", "Windows encountered a read/write error on your hard drive or SSD. This could be a sign of a failing drive. Run SMART diagnostics immediately.", "Critical"),
    51:   ("Disk Error During Paging", "Windows had trouble reading or writing data while managing memory. This is often caused by a failing hard drive. Back up your data and run a drive health check.", "Critical"),
}

class EventLogMiner:
    def __init__(self):
        self.logs_to_scan = ["System", "Application"]

    def get_critical_events(self, hours=24):
        """
        Scans Windows System and Application event logs for critical/error events
        within the last `hours` hours.
        Returns a list of dicts with event details.
        """
        results = []
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        seen_signatures = set()  # For deduplication

        for log_name in self.logs_to_scan:
            try:
                handle = win32evtlog.OpenEventLog(None, log_name)
                flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

                stop_reading = False  # Flag to break out of both loops once cutoff is hit
                while not stop_reading:
                    events = win32evtlog.ReadEventLog(handle, flags, 0)
                    if not events:
                        break

                    for event in events:
                        # Only look at Critical (1) and Error (2) level events
                        if event.EventType not in (win32con.EVENTLOG_ERROR_TYPE, win32con.EVENTLOG_WARNING_TYPE):
                            continue

                        # Parse time — stop if events are older than cutoff
                        try:
                            event_time = datetime.datetime.strptime(
                                str(event.TimeGenerated), "%Y-%m-%d %H:%M:%S"
                            )
                        except Exception:
                            continue

                        if event_time < cutoff:
                            # Events are sorted newest-first; stop reading any more pages
                            stop_reading = True
                            break

                        event_id = event.EventID & 0xFFFF  # Mask to get base ID
                        source = event.SourceName

                        # Skip known noisy events that are low value
                        if event_id in NOISY_EVENT_IDS:
                            continue

                        # Also skip generic BTHUSB (Bluetooth peripheral mode)
                        if source.upper() in ("BTHUSB", "BTHMINI") and event_id not in KNOWN_EVENT_IDS:
                            continue

                        # Deduplicate: same source + event ID within same hour
                        sig = f"{source}_{event_id}_{event_time.hour}"
                        if sig in seen_signatures:
                            continue
                        seen_signatures.add(sig)

                        # Look up plain-English description
                        if event_id in KNOWN_EVENT_IDS:
                            title, explanation, severity = KNOWN_EVENT_IDS[event_id]
                        else:
                            # Try to read the raw message and clean it up
                            try:
                                raw_msg = win32evtlogutil.SafeFormatMessage(event, log_name)
                                # Strip XML-like insertion strings and angle brackets
                                raw_msg = re.sub(r'<[^>]+>', '', raw_msg)
                                # Collapse whitespace
                                raw_msg = ' '.join(raw_msg.split())
                                # Truncate
                                explanation = (raw_msg[:200] + "...") if len(raw_msg) > 200 else raw_msg
                                if not explanation.strip():
                                    explanation = f"Windows logged an error from '{source}'. No plain-English description is available. Search Event ID {event_id} online for more details."
                            except Exception:
                                explanation = f"Windows logged an error from '{source}'. Try running TechGuardAI as Administrator for more details."
                            title = f"Error from: {source}"
                            # Determine severity from event type
                            severity = "Critical" if event.EventType == win32con.EVENTLOG_ERROR_TYPE else "Warning"

                        results.append({
                            "time": event_time.strftime("%H:%M — %b %d"),
                            "log": log_name,
                            "source": source,
                            "event_id": event_id,
                            "title": title,
                            "explanation": explanation,
                            "severity": severity
                        })

                win32evtlog.CloseEventLog(handle)

            except pywintypes.error as e:
                # Access denied or log not found
                results.append({
                    "time": "—",
                    "log": log_name,
                    "source": "TechGuardAI",
                    "event_id": 0,
                    "title": f"Cannot read {log_name} log",
                    "explanation": f"Access denied or log unavailable: {e.strerror}. Try running TechGuardAI as Administrator.",
                    "severity": "Warning"
                })
            except Exception as e:
                print(f"EventLogMiner error on {log_name}: {e}")

        # Sort by severity: Critical first, then Warning
        severity_order = {"Critical": 0, "Warning": 1, "OK": 2}
        results.sort(key=lambda x: severity_order.get(x["severity"], 3))

        return results[:30]  # Cap at 30 most important
