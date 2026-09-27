import psutil
import os
import stat
import shutil

class ActionHandler:
    def __init__(self):
        # Critical system processes that should never be killed
        self.protected_processes = {
            "explorer.exe", "system", "idle", "wininit.exe", "services.exe",
            "lsass.exe", "csrss.exe", "smss.exe", "winlogon.exe",
            "svchost.exe", "registry", "fontdrvhost.exe", "dwm.exe"
        }

    def terminate_process(self, pid):
        """Safely terminates a process by PID."""
        try:
            proc = psutil.Process(pid)
            name = proc.name().lower()
            
            if name in self.protected_processes:
                return False, f"Risk Alert: '{name}' is a critical system process and cannot be closed."
            
            proc.terminate()
            return True, f"Successfully terminated {name} (PID: {pid})."
        except psutil.NoSuchProcess:
            return False, "Error: Process not found (it may have already closed)."
        except psutil.AccessDenied:
            return False, "Error: Access Denied. Try running TechGuard as Administrator."
        except Exception as e:
            return False, f"Error: {str(e)}"

    def clear_temp_files(self):
        """Clears the current user's temporary files."""
        temp_dir = os.environ.get('TEMP')
        if not temp_dir or not os.path.exists(temp_dir):
            return False, "Error: Could not locate system TEMP directory."
            
        deleted_count = 0
        errors = 0
        
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    deleted_count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    deleted_count += 1
            except Exception:
                errors += 1
                
        return True, f"Cleaned {deleted_count} items from Temp folder ({errors} items currently in use)."

    def delete_file(self, path: str):
        """Safely deletes a single file. Returns (success: bool, message: str)."""
        from core.disk_analyzer import DiskAnalyzer
        analyzer = DiskAnalyzer()
        return analyzer.delete_file(path)
