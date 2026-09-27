import psutil
import socket
import winreg
import ctypes
import os

class NetworkPrivacyManager:
    """Handles deep network inspection and Windows privacy settings via Registry."""

    # ── Active Connections ───────────────────────────────────────────────────
    
    def get_active_connections(self):
        """Returns a list of established external connections and the apps responsible."""
        active = []
        try:
            conns = psutil.net_connections(kind='inet')
            for c in conns:
                # We only care about established external outbound connections
                if c.status == 'ESTABLISHED' and c.raddr:
                    ip = c.raddr.ip
                    # Filter out local loopback and generic multicast
                    if ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10.") or ip == "0.0.0.0":
                        continue
                        
                    pid = c.pid
                    app_name = "Unknown"
                    if pid:
                        try:
                            app_name = psutil.Process(pid).name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                            
                    # Try to resolve hostname (with short timeout so it doesn't block)
                    hostname = ip
                    try:
                        # very short DNS resolution, often cached
                        socket.setdefaulttimeout(0.1)
                        hostname = socket.gethostbyaddr(ip)[0]
                    except Exception:
                        pass
                        
                    active.append({
                        "app": app_name,
                        "pid": pid,
                        "ip": ip,
                        "port": c.raddr.port,
                        "host": hostname
                    })
        except Exception as e:
            print(f"Connection monitor error: {e}")
            
        # Deduplicate identical connections
        unique = []
        seen = set()
        for c in active:
            sig = f"{c['app']}-{c['ip']}:{c['port']}"
            if sig not in seen:
                seen.add(sig)
                unique.append(c)
                
        return sorted(unique, key=lambda x: x['app'].lower())

    # ── Windows Privacy Toggles (Registry) ───────────────────────────────────

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def get_telemetry_status(self):
        """Checks if Windows telemetry is blocked. Returns True if BLOCKED."""
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", 
                               0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "AllowTelemetry")
            winreg.CloseKey(key)
            return val == 0
        except FileNotFoundError:
            return False # Default Windows behaviour is not blocked

    def set_telemetry_blocked(self, blocked: bool):
        """Sets Windows Telemetry levels (Requires Admin)."""
        if not self.is_admin():
            raise PermissionError("Administrator rights required to modify telemetry settings.")
            
        try:
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, 
                                 r"SOFTWARE\Policies\Microsoft\Windows\DataCollection")
            val = 0 if blocked else 3 # 0 = Off, 3 = Full
            winreg.SetValueEx(key, "AllowTelemetry", 0, winreg.REG_DWORD, val)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error setting telemetry: {e}")
            return False
