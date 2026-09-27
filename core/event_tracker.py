"""
event_tracker.py
Background service that polls every 60 seconds for system events
(network drops, CPU spikes, disk pressure, app crashes) and logs
them to the event_log table via DatabaseManager.
"""
import threading
import time
import psutil
import winreg
from core.database_manager import DatabaseManager


class EventTracker:
    """
    Runs a silent background thread monitoring for recurring system problems.
    Events are written to the database so get_predictions() can surface them
    in the chatbot prompt as proactive warnings.
    """

    # How often to poll (seconds)
    POLL_INTERVAL = 60

    # Thresholds
    CPU_SPIKE_THRESHOLD = 90      # %
    DISK_PRESSURE_THRESHOLD = 90  # % used

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()
        self.stop_event = threading.Event()

        # State tracking — to detect *transitions* rather than constant states
        self._prev_net_adapters: dict[str, bool] = {}   # adapter_name -> is_up
        self._cpu_spike_streak = 0                       # consecutive high-CPU readings
        self._last_event_ids: set[int] = set()           # Windows event IDs already logged

        # Seed initial network adapter states
        self._prev_net_adapters = self._get_adapter_states()

        # Seed initial Windows Application event IDs to avoid logging stale errors on startup
        self._last_event_ids = self._get_recent_error_event_ids()

        self._thread = threading.Thread(target=self._run, daemon=True, name="EventTracker")

    def start(self):
        self._thread.start()
        print("[EventTracker] Started background event monitoring.")

    def stop(self):
        self.stop_event.set()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self._check_network()
                self._check_cpu()
                self._check_disk()
                self._check_app_crashes()
            except Exception as e:
                print(f"[EventTracker] Poll error: {e}")

            self.stop_event.wait(self.POLL_INTERVAL)

    # ------------------------------------------------------------------
    # Checkers
    # ------------------------------------------------------------------

    def _check_network(self):
        """Detect any adapter that was UP and is now DOWN."""
        current = self._get_adapter_states()
        for name, is_up in current.items():
            prev_up = self._prev_net_adapters.get(name, True)  # assume up if unknown
            if prev_up and not is_up:
                detail = f"Network adapter '{name}' went offline."
                self.db.log_event("NETWORK_DROP", detail, "WARNING")
                print(f"[EventTracker] Logged NETWORK_DROP — {detail}")
        self._prev_net_adapters = current

    def _check_cpu(self):
        """Log a CPU_SPIKE if CPU stays above threshold for 2 consecutive polls."""
        usage = psutil.cpu_percent(interval=1)
        if usage >= self.CPU_SPIKE_THRESHOLD:
            self._cpu_spike_streak += 1
        else:
            self._cpu_spike_streak = 0

        if self._cpu_spike_streak >= 2:
            detail = f"CPU usage reached {usage:.1f}% (sustained high load)."
            self.db.log_event("CPU_SPIKE", detail, "WARNING")
            print(f"[EventTracker] Logged CPU_SPIKE — {detail}")
            self._cpu_spike_streak = 0  # Reset so we don't spam

    def _check_disk(self):
        """Log DISK_PRESSURE when C: usage crosses the threshold."""
        try:
            usage = psutil.disk_usage("C:\\")
            if usage.percent >= self.DISK_PRESSURE_THRESHOLD:
                free_gb = usage.free / (1024 ** 3)
                detail = f"C: drive is {usage.percent:.1f}% full ({free_gb:.1f} GB free)."
                self.db.log_event("DISK_PRESSURE", detail, "WARNING")
                print(f"[EventTracker] Logged DISK_PRESSURE — {detail}")
        except Exception as e:
            print(f"[EventTracker] Disk check failed: {e}")

    def _check_app_crashes(self):
        """
        Scan the Windows Application Event Log for new Error-level entries
        with EventID 1000 (Application Error) or 1002 (Application Hang).
        Uses winreg to read from Windows Event Log entries without admin rights.
        Falls back silently if access is denied.
        """
        try:
            import win32evtlog  # pywin32
            current_ids = set()

            handle = win32evtlog.OpenEventLog(None, "Application")
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

            events = win32evtlog.ReadEventLog(handle, flags, 0)
            win32evtlog.CloseEventLog(handle)

            crash_event_ids = {1000, 1002}  # App Error, App Hang

            for event in (events or []):
                record_id = event.RecordNumber
                current_ids.add(record_id)
                if (event.EventID & 0xFFFF) in crash_event_ids and record_id not in self._last_event_ids:
                    source = event.SourceName or "Unknown App"
                    detail = f"Application crash/hang: {source} (EventID {event.EventID & 0xFFFF})"
                    self.db.log_event("APP_CRASH", detail, "ERROR")
                    print(f"[EventTracker] Logged APP_CRASH — {detail}")

            if current_ids:
                self._last_event_ids = current_ids

        except ImportError:
            pass  # pywin32 not available — skip crash monitoring
        except Exception as e:
            pass  # Silently skip if permissions are denied

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_adapter_states(self) -> dict:
        """Returns {adapter_name: is_up} for all non-loopback adapters."""
        states = {}
        try:
            stats = psutil.net_if_stats()
            for name, stat in stats.items():
                if name.lower() == "loopback" or name.startswith("Lo"):
                    continue
                states[name] = stat.isup
        except Exception:
            pass
        return states

    def _get_recent_error_event_ids(self) -> set:
        """Seed the known event ID set at startup to avoid logging old errors."""
        ids = set()
        try:
            import win32evtlog
            handle = win32evtlog.OpenEventLog(None, "Application")
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            win32evtlog.CloseEventLog(handle)
            for event in (events or []):
                ids.add(event.RecordNumber)
        except Exception:
            pass
        return ids
