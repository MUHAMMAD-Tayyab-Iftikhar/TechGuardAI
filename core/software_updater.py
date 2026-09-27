import subprocess
import threading

class SoftwareUpdater:
    """Wrapper for Windows winget to find and install software updates."""

    def __init__(self):
        self.checking = False
        self.updates_available = []

    def check_for_updates(self, on_complete=None):
        """Runs winget upgrade asynchronously and calls on_complete(results)."""
        if self.checking:
            return
        self.checking = True

        def _run():
            try:
                # --accept-source-agreements prevents the occasional prompt
                result = subprocess.run(
                    ["winget", "upgrade", "--accept-source-agreements"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                updates = self._parse_winget_output(result.stdout)
                self.updates_available = updates
                if on_complete:
                    on_complete(updates)
            except Exception as e:
                print(f"Error checking updates: {e}")
                if on_complete:
                    on_complete([])
            finally:
                self.checking = False

        threading.Thread(target=_run, daemon=True).start()

    def _parse_winget_output(self, output: str) -> list:
        """
        Parses winget upgrade output.
        Returns a list of dicts: {"name": str, "id": str, "version": str, "available": str}
        """
        lines = output.splitlines()
        results = []
        
        # Output looks like:
        # Name       Id      Version   Available Source
        # ---------------------------------------------
        # AppName    app.id  1.0       2.0       winget
        
        start_parsing = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "--------" in line:
                start_parsing = True
                continue
                
            if start_parsing:
                # Stop if we hit footer messages like "1 upgrades available."
                if "upgrade" in line and "available." in line:
                    break
                    
                # Split by 2 or more spaces, since names can have single spaces
                import re
                parts = re.split(r'\s{2,}', line)
                if len(parts) >= 4:
                    results.append({
                        "name": parts[0].strip(),
                        "id": parts[1].strip(),
                        "version": parts[2].strip(),
                        "available": parts[3].strip()
                    })
        return results

    def install_update(self, app_id: str, on_success=None, on_error=None):
        """Installs a specific update silently in the background."""
        def _run():
            try:
                result = subprocess.run(
                    ["winget", "upgrade", "--id", app_id, "--silent", 
                     "--accept-source-agreements", "--accept-package-agreements"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0 or "successfully" in result.stdout.lower():
                    if on_success: on_success()
                else:
                    if on_error: on_error(result.stderr or result.stdout)
            except Exception as e:
                if on_error: on_error(str(e))

        threading.Thread(target=_run, daemon=True).start()

    def install_all_updates(self, on_success=None, on_error=None):
        """Installs all available updates."""
        def _run():
            try:
                result = subprocess.run(
                    ["winget", "upgrade", "--all", "--silent", 
                     "--accept-source-agreements", "--accept-package-agreements"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0 or "successfully" in result.stdout.lower():
                    if on_success: on_success()
                else:
                    if on_error: on_error(result.stderr or result.stdout)
            except Exception as e:
                if on_error: on_error(str(e))

        threading.Thread(target=_run, daemon=True).start()
