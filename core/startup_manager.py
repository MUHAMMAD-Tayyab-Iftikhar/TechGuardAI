import winreg
import os
import ctypes

class StartupManager:
    """Manages Windows startup applications via the Registry."""

    def __init__(self):
        self.run_keys = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
        ]

    def get_startup_apps(self):
        """Returns a list of startup applications."""
        apps = []
        for root, path in self.run_keys:
            try:
                key = winreg.OpenKey(root, path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, val, typ = winreg.EnumValue(key, i)
                        scope = "User" if root == winreg.HKEY_CURRENT_USER else "System"
                        apps.append({
                            "name": name,
                            "command": str(val),
                            "scope": scope,
                            "enabled": True, # For this basic version, if it's in the Run key, it's enabled.
                            "root": root,
                            "path": path
                        })
                        i += 1
                    except OSError:
                        break # No more values
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass
                
        return sorted(apps, key=lambda x: x['name'].lower())

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def remove_startup_app(self, name: str, root_hkey, sub_path: str):
        """
        Removes an app from the startup sequence (Deletes its key).
        Disabling properly requires interacting with StartupApproved keys which gets complex,
        so deleting the Run key value is the most definitive way to disable it.
        """
        if root_hkey == winreg.HKEY_LOCAL_MACHINE and not self.is_admin():
            raise PermissionError("Admin privileges required to remove System-level startup apps.")
            
        try:
            key = winreg.OpenKey(root_hkey, sub_path, 0, winreg.KEY_ALL_ACCESS)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Failed to remove startup app {name}: {e}")
            return False
