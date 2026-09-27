import os
import ctypes
from ctypes import wintypes
import stat
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemCleaner:
    def __init__(self):
        self.scan_targets = {
            "System Temp": os.environ.get('TEMP'),
            "Windows Temp": os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp'),
            "Recycle Bin": "RecycleBin", # Special flag
        }

    def get_file_size(self, path):
        """Calculates total size of a directory in bytes."""
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception:
            pass # Permission errors are common in Temp folders
        return total_size

    def get_recycle_bin_stats(self):
        """Uses Windows API to get accurate Recycle Bin size."""
        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [
                ('cbSize', wintypes.DWORD),
                ('i64Size', ctypes.c_int64),
                ('i64NumItems', ctypes.c_int64),
            ]
        
        try:
            rb_info = SHQUERYRBINFO()
            rb_info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
            # 0 means S_OK (Success)
            res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb_info))
            if res == 0:
                return rb_info.i64Size
        except Exception as e:
            logger.error(f"Error reading Recycle Bin: {e}")
        
        return 0

    def scan_junk(self):
        """Returns a dict of {category: size_in_mb}"""
        results = {}

        # 1. Check Folders and Recycle Bin
        for name, path in self.scan_targets.items():
            size_bytes = 0
            
            if name == "Recycle Bin":
                size_bytes = self.get_recycle_bin_stats()
            elif path and os.path.exists(path):
                size_bytes = self.get_file_size(path)

            results[name] = round(size_bytes / (1024 * 1024), 2) # Convert to MB

        return results

    def clean_junk(self, selected_items):
        """
        Deletes files in selected categories.
        Returns: MB cleaned (float)
        """
        bytes_cleaned = 0

        for item in selected_items:
            # --- 1. Handle Recycle Bin ---
            if item == "Recycle Bin":
                try:
                    # Get size before cleaning to report it
                    current_size = self.get_recycle_bin_stats()
                    
                    # SHERB_NOCONFIRMATION = 1, SHERB_NOPROGRESSUI = 2, SHERB_NOSOUND = 4
                    flags = 1 | 2 | 4 
                    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
                    
                    bytes_cleaned += current_size
                except Exception as e:
                    logger.error(f"Failed to empty Recycle Bin: {e}")
                continue

            # --- 2. Handle Temp Folders ---
            path = self.scan_targets.get(item)
            if path and os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        file_path = os.path.join(root, f)
                        try:
                            # Try to get size first
                            size = os.path.getsize(file_path)
                            
                            # Attempt to remove
                            os.remove(file_path) 
                            bytes_cleaned += size
                        except PermissionError:
                            # If permission denied, check if read-only and try to change it
                            try:
                                os.chmod(file_path, stat.S_IWRITE)
                                os.remove(file_path)
                                bytes_cleaned += size
                            except Exception as e:
                                # Common when file is in use or system file - log as debug to reduce noise
                                logger.debug(f"Failed to delete {file_path} after chmod: {e}")
                        except OSError as e:
                            # Handle common Windows errors silently or with debug logging
                            # 32 = ERROR_SHARING_VIOLATION (File used by another process)
                            # 5 = ERROR_ACCESS_DENIED
                            if getattr(e, 'winerror', 0) == 32:
                                logger.debug(f"Skipped (in use): {file_path}")
                            elif getattr(e, 'winerror', 0) == 5:
                                logger.debug(f"Skipped (access denied): {file_path}")
                            else:
                                logger.warning(f"Error deleting {file_path}: {e}")
                        except Exception as e:
                            logger.debug(f"Skipping {file_path}: {e}")

        return round(bytes_cleaned / (1024 * 1024), 2)

    def flush_dns(self):
        """Flushes the Windows DNS Resolver Cache."""
        try:
            import subprocess
            result = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                logger.info("Successfully flushed DNS cache.")
                return True
            else:
                logger.error(f"Failed to flush DNS cache: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error executing ipconfig /flushdns: {e}")
            return False

    def run_one_click_boost(self):
        """
        Executes a full system optimization:
        1. Identifies sizes of Temp folders and Recycle Bin
        2. Cleans them
        3. Flushes DNS
        Returns a summary dictionary.
        """
        summary = {
            "success": True,
            "mb_cleaned": 0.0,
            "items_cleaned": [],
            "dns_flushed": False,
            "errors": []
        }

        try:
            # 1 & 2: Clean junk files
            targets = list(self.scan_targets.keys())
            summary["items_cleaned"] = targets
            
            # Use existing clean_junk method which also gets size before deleting for recycle bin
            cleaned_mb = self.clean_junk(targets)
            summary["mb_cleaned"] = cleaned_mb
            
            # 3: Flush DNS
            summary["dns_flushed"] = self.flush_dns()
            
        except Exception as e:
            summary["success"] = False
            summary["errors"].append(str(e))
            logger.error(f"One-Click Boost encountered an error: {e}")

        return summary