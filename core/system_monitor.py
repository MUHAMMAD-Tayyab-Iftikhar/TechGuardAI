import psutil
import time
import wmi # Required for deep battery stats
import datetime
import threading
from core.database_manager import DatabaseManager

_STATS_CACHE_TTL = 1.5  # seconds

class SystemMonitor:
    def __init__(self):
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        try:
            self.wmi_client = wmi.WMI()
        except:
            self.wmi_client = None
        self.system_procs = {
            "explorer.exe", "System", "wininit.exe", "services.exe",
            "lsass.exe", "csrss.exe", "smss.exe", "winlogon.exe",
            "svchost.exe", "registry", "fontdrvhost.exe", "dwm.exe"
        }
        # Cache for get_all_stats() to avoid redundant process scans
        self._stats_cache = None
        self._stats_cache_time = 0.0
        self._stats_lock = threading.Lock()
        
        # Initialize Database and Background Logging
        self.db = DatabaseManager()
        self.stop_event = threading.Event()
        self.log_thread = threading.Thread(target=self._logging_loop, daemon=True)
        self.log_thread.start()

    def _logging_loop(self):
        """Background loop to sample system metrics every 5 minutes."""
        while not self.stop_event.is_set():
            try:
                # Read raw values directly — no string parsing needed
                cpu = self.get_cpu_metrics()["usage"]
                ram = self.get_memory_metrics()["percent"]
                disk_free = self.get_disk_metrics()["free"]
                # Reuse cached stats for top process name
                stats = self.get_all_stats()
                top_proc = stats.get("Top CPU App", "Scanning...")
                self.db.log_metrics(cpu, ram, disk_free, top_proc)
            except Exception as e:
                print(f"Logging Thread Error: {e}")

            # Wait for 5 minutes (300 seconds) or until stopped
            self.stop_event.wait(300)

    def get_cpu_metrics(self):
        return {
            "usage": psutil.cpu_percent(interval=None),
            "cores": psutil.cpu_count(logical=True),
            "freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0
        }

    def get_memory_metrics(self):
        mem = psutil.virtual_memory()
        return {
            "total": round(mem.total / (1024**3), 2),
            "percent": mem.percent
        }

    def get_disk_metrics(self):
        try:
            usage = psutil.disk_usage('C:\\')
            return {
                "device": "C:",
                "percent": usage.percent,
                "free": round(usage.free / (1024**3), 2)
            }
        except:
            return {"percent": 0, "free": 0}

    def get_network_speed(self):
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        
        bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
        time_elapsed = current_time - self.last_time
        if time_elapsed == 0: time_elapsed = 1
        
        upload_speed = (bytes_sent / time_elapsed) / 1024
        download_speed = (bytes_recv / time_elapsed) / 1024
        
        self.last_net_io = current_net_io
        self.last_time = current_time
        
        return {
            "up": f"{upload_speed:.1f} KB/s",
            "down": f"{download_speed:.1f} KB/s"
        }

    def get_battery_report(self):
        """Returns a human-readable battery health status."""
        if not self.wmi_client: 
            return "Desktop PC (AC Power)"
            
        try:
            batteries = self.wmi_client.query("Select * from Win32_Battery")
            if not batteries:
                return "Desktop PC (No Battery)"
            
            psutil_bat = psutil.sensors_battery()
            status = "Charging" if psutil_bat.power_plugged else "Discharging"
            return f"{psutil_bat.percent}% ({status})"
        except:
            return "Battery Sensor Error"

    def get_process_bloat_score(self):
        """Returns the count of processes and a 'rating'."""
        count = len(psutil.pids())
        rating = "Normal"
        if count < 100: rating = "Clean"
        elif count > 180: rating = "Bloated"
        elif count > 250: rating = "Overloaded"
        return {"count": count, "rating": rating}

    # --- NEW METHODS FOR ROW 3 ---

    def get_system_uptime(self):
        """Calculates how long the system has been running."""
        boot_time = psutil.boot_time()
        seconds = time.time() - boot_time
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        
        if d > 0:
            return f"{int(d)}d {int(h)}h {int(m)}m"
        return f"{int(h)}h {int(m)}m"

    def get_top_cpu_process(self):
        """Wrapper for backward compatibility."""
        stats = self.get_all_stats()
        return stats.get("Top CPU App", "Scanning...")

    def get_heaviest_process(self):
        """Wrapper for backward compatibility."""
        stats = self.get_all_stats()
        return stats.get("Top RAM App", "Scanning...")

    def get_cleanup_candidates(self):
        """Identifies non-critical user apps using high memory (>200MB)."""
        candidates = []
        try:
            for p in psutil.process_iter(['name', 'memory_info']):
                try:
                    name = p.info['name']
                    if name.lower() in self.system_procs:
                        continue
                        
                    mem_mb = p.info['memory_info'].rss / (1024 * 1024)
                    if mem_mb > 200:
                        candidates.append({
                            "name": name,
                            "pid": p.pid,
                            "mem": int(mem_mb)
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Error in get_cleanup_candidates: {e}")
            
        return candidates

    def get_all_stats(self):
        """Aggregates all stats for the AI context efficiently.

        Results are cached for _STATS_CACHE_TTL seconds so multiple callers
        within the same refresh cycle (dashboard, chatbot, logger) share a
        single process scan.
        """
        with self._stats_lock:
            now = time.time()
            if self._stats_cache is not None and (now - self._stats_cache_time) < _STATS_CACHE_TTL:
                return self._stats_cache

        cpu = self.get_cpu_metrics()
        mem = self.get_memory_metrics()
        disk = self.get_disk_metrics()
        battery = self.get_battery_report()
        uptime = self.get_system_uptime()

        # Optimize: Get top processes in a single pass
        top_cpu_app = "Scanning..."
        top_mem_app = "Scanning..."

        try:
            # Collect data for all processes once
            processes = []
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
                try:
                    processes.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if processes:
                # Find top CPU
                top_cpu = max(processes, key=lambda x: x['cpu_percent'] or 0)
                top_cpu_app = f"{top_cpu['name']} ({top_cpu['cpu_percent']}%)"

                # Find top Memory
                top_mem = max(processes, key=lambda x: x['memory_info'].rss if x['memory_info'] else 0)
                mem_mb = top_mem['memory_info'].rss / (1024 * 1024)
                top_mem_app = f"{top_mem['name']} ({int(mem_mb)} MB)"
        except Exception as e:
            print(f"Error gathering process stats: {e}")

        result = {
            "CPU Logic": f"{cpu['usage']}% (Freq: {cpu['freq']}Mhz)",
            "RAM Usage": f"{mem['percent']}% (Total: {mem['total']}GB)",
            "Disk Space": f"{disk['free']}GB Free ({disk['percent']}% Used)",
            "Battery": battery,
            "System Uptime": uptime,
            "Top CPU App": top_cpu_app,
            "Top RAM App": top_mem_app
        }

        with self._stats_lock:
            self._stats_cache = result
            self._stats_cache_time = time.time()
        return result