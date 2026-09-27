# disk_analyzer.py — TechGuardAI Drive Analyzer core
#
# Design:
#   • scan_large_files uses different strategies per drive type:
#       C: (system drive) — scans targeted roots with noise-filtered AppData
#       Other drives     — scans the whole drive (they're fast data drives)
#   • _scandir_walk uses os.scandir() for Windows-native speed.
#   • run_full_scan is SEQUENTIAL in one background thread (avoids I/O contention).
#   • done_cb is always called via finally.

import os
import stat
import time
import winreg
import logging
import datetime
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category map
# ---------------------------------------------------------------------------
CATEGORY_MAP = {
    "Videos":     {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
                   ".webm", ".m4v", ".mpeg", ".mpg", ".ts", ".m2ts"},
    "Images":     {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
                   ".webp", ".ico", ".heic", ".raw", ".cr2", ".nef"},
    "Documents":  {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt",
                   ".pptx", ".txt", ".odt", ".csv", ".rtf", ".epub"},
    "Installers": {".exe", ".msi", ".iso", ".img", ".dmg",
                   ".zip", ".rar", ".7z", ".tar", ".gz", ".cab"},
    "Audio":      {".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a"},
    "Code":       {".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
                   ".java", ".cpp", ".c", ".cs", ".go", ".rs",
                   ".swift", ".kt", ".php", ".rb"},
}

# ---------------------------------------------------------------------------
# Skip-set constants
# ---------------------------------------------------------------------------

# Minimum skip set — used when scanning non-system (data) drives.
# Only blocks directories that are genuinely inaccessible or useless.
SKIP_DATA_DRIVE = frozenset({
    "winsxs",
    "$recycle.bin",
    "system volume information",
    "$windows.~bt",
    "$windows.~ws",
})

# Extended skip set — used inside the Users tree on C:  to avoid the deep
# developer/runtime caches that contain millions of tiny files.
# Covers: NPM, conda/pip, browser caches, JetBrains, VS, Docker layers, etc.
SKIP_APPDATA_CACHE = frozenset({
    # npm / node
    "node_modules", "npm-cache", ".npm",
    # Python / conda
    "conda", "__pycache__", ".conda", "pkgs",
    # Browser caches
    "cache", "cache2", "gpucache", "code cache",
    "shadercache", "blob_storage", "storage",
    # JetBrains / IDEs
    "caches", "system", "plugins",
    # Docker / container layers
    "overlay2", "containers", "layers", "blobs",
    # VS / MSBuild
    "objd", "bin", "obj",
    # Misc package managers
    ".gradle", ".m2", ".nuget",
    # Electron / Chromium app caches
    "crashreports", "crashpad", "crashdata",
    ".yarn",
    # Android SDK — contains emulator system images + millions of build files
    "android",
})

# Skip anything starting with these characters
SKIP_PREFIXES = ("$", ".")

# Protected paths — the UI will block deletion of these
PROTECTED_PATHS = frozenset({
    "c:\\windows",
    "c:\\windows\\system32",
    "c:\\program files\\windows defender",
    "c:\\programdata\\microsoft\\windows defender",
})

SCAN_TIMEOUT_SEC = 120


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _fmt_size(n: int) -> str:
    if n >= 1 << 30:
        return f"{n / (1 << 30):.2f} GB"
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.1f} KB"
    return f"{n} B"


def _get_category(ext: str) -> str:
    ext = ext.lower()
    for cat, exts in CATEGORY_MAP.items():
        if ext in exts:
            return cat
    return "Others"


def _should_skip(name: str, skip_set: frozenset) -> bool:
    nl = name.lower()
    for p in SKIP_PREFIXES:
        if nl.startswith(p):
            return True
    return nl in skip_set


def _scandir_walk(root: str,
                  min_size: int = 0,
                  abort_flag=None,
                  skip_set: frozenset = SKIP_DATA_DRIVE):
    """
    Iterative scandir-based directory walk.
    Yields (path, name, size_bytes, atime) for every file >= min_size.

    On Windows, DirEntry.stat() reuses FindNextFile data — no extra syscall
    per file. This is 3-5× faster than os.walk() + os.stat().
    """
    stack = [root]
    while stack:
        if abort_flag and abort_flag.is_set():
            return
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if abort_flag and abort_flag.is_set():
                        return
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if not _should_skip(entry.name, skip_set):
                                stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            st = entry.stat()   # free on Windows
                            if st.st_size >= min_size:
                                yield (entry.path, entry.name,
                                       st.st_size, st.st_atime)
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            continue


def get_available_drives() -> list:
    """Return all mounted, accessible drive mount-points."""
    drives = []
    try:
        import psutil
        for part in psutil.disk_partitions(all=False):
            if part.fstype and part.mountpoint:
                drives.append(part.mountpoint)
    except Exception:
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            mp = f"{letter}:\\"
            if os.path.exists(mp):
                drives.append(mp)
    return drives or ["C:\\"]


def estimate_scan_time(min_size_mb: int) -> str:
    if min_size_mb >= 1024:
        return "~30 seconds"
    if min_size_mb >= 500:
        return "~30 seconds"
    if min_size_mb >= 100:
        return "~1 minute"
    if min_size_mb >= 50:
        return "~1-2 minutes"
    if min_size_mb >= 10:
        return "~3 minutes"
    return "~5 minutes"


# ---------------------------------------------------------------------------
# DiskAnalyzer
# ---------------------------------------------------------------------------

class DiskAnalyzer:
    """All disk-scanning operations scoped to one drive."""

    def __init__(self, drive: str = "C:\\"):
        self.drive = drive.rstrip("/\\") + "\\"
        self._scan_results: dict = {}
        self._is_scanning = False
        self._scan_lock = threading.Lock()
        self.min_large_file_bytes = 100 * 1024 * 1024

    # ------------------------------------------------------------------
    # Drive summary
    # ------------------------------------------------------------------

    def get_drive_summary(self) -> dict:
        try:
            import psutil
            u = psutil.disk_usage(self.drive)
            return {
                "total_gb":  round(u.total / (1 << 30), 2),
                "used_gb":   round(u.used  / (1 << 30), 2),
                "free_gb":   round(u.free  / (1 << 30), 2),
                "percent":   u.percent,
                "total_str": _fmt_size(u.total),
                "used_str":  _fmt_size(u.used),
                "free_str":  _fmt_size(u.free),
            }
        except Exception as exc:
            logger.error("get_drive_summary: %s", exc)
            return {k: (0 if k in ("total_gb", "used_gb", "free_gb", "percent")
                        else "N/A")
                    for k in ("total_gb", "used_gb", "free_gb", "percent",
                               "total_str", "used_str", "free_str")}

    # ------------------------------------------------------------------
    # Large files  (the main scanner)
    # ------------------------------------------------------------------

    def scan_large_files(self,
                         top_n: int = 200,
                         min_size_bytes: int = None,
                         progress_cb=None,
                         abort_flag=None) -> list:
        """
        Return up to top_n files >= min_size_bytes, sorted largest-first.

        Strategy (tuned from profiling):
          C: drive  — scans the following roots with appropriate skip sets:
                       • Users tree        (with SKIP_APPDATA_CACHE to avoid
                                            node_modules, conda, browser caches)
                       • Program Files     (with SKIP_DATA_DRIVE)
                       • Program Files(x86)(with SKIP_DATA_DRIVE)
                       • ProgramData       (with SKIP_DATA_DRIVE)
                       • all other top-level dirs (slim/fast)
          Other drives — scans the ENTIRE drive (they're data drives, fast)
        """
        if min_size_bytes is None:
            min_size_bytes = self.min_large_file_bytes

        drive_upper = self.drive.upper()
        is_system = drive_upper.startswith("C:")

        files: list = []
        seen_paths: set  = set()
        seen_inodes: set = set()
        count = 0

        def _add(path, name, size, atime):
            nonlocal count
            if path in seen_paths:
                return
            seen_paths.add(path)
            try:
                st = os.stat(path)
                key = (st.st_dev, st.st_ino)
                if key in seen_inodes:
                    return
                seen_inodes.add(key)
            except OSError:
                pass
            files.append({
                "path": path,
                "name": name,
                "size_bytes": size,
                "size_str": _fmt_size(size),
                "last_accessed": atime,
                "last_accessed_str": datetime.datetime.fromtimestamp(
                    atime).strftime("%Y-%m-%d"),
                "category": _get_category(Path(name).suffix),
            })
            count += 1
            if progress_cb and count % 5 == 0:
                progress_cb(count)

        if is_system:
            home = os.path.expanduser("~")
            # Roots with their matching skip sets
            scan_plan = [
                # Users tree — skip noise caches (node_modules etc)
                (home,
                 SKIP_DATA_DRIVE | SKIP_APPDATA_CACHE),
                # Program Files — standard skip
                (os.path.join(self.drive, "Program Files"),
                 SKIP_DATA_DRIVE),
                (os.path.join(self.drive, "Program Files (x86)"),
                 SKIP_DATA_DRIVE),
                (os.path.join(self.drive, "ProgramData"),
                 SKIP_DATA_DRIVE),
                # Everything else at drive root that isn't Users/Program/Windows
                # Walk only top-level dirs to catch any outliers quickly
            ]
            # Also include any other top-level dirs on C that aren't in the plan
            plan_parents = {
                "users", "program files", "program files (x86)", "programdata",
                "windows",   # too slow even after winsxs skip
            }
            try:
                for entry in os.scandir(self.drive):
                    if (entry.is_dir(follow_symlinks=False) and
                            not _should_skip(entry.name, SKIP_DATA_DRIVE) and
                            entry.name.lower() not in plan_parents):
                        scan_plan.append((entry.path, SKIP_DATA_DRIVE))
            except (PermissionError, OSError):
                pass
        else:
            # Non-system drive: scan the entire thing
            scan_plan = [(self.drive, SKIP_DATA_DRIVE)]

        for root, skip in scan_plan:
            if not os.path.exists(root):
                continue
            if abort_flag and abort_flag.is_set():
                break
            for path, name, size, atime in _scandir_walk(
                    root,
                    min_size=min_size_bytes,
                    abort_flag=abort_flag,
                    skip_set=skip):
                _add(path, name, size, atime)

        files.sort(key=lambda f: f["size_bytes"], reverse=True)
        return files[:top_n]

    # ------------------------------------------------------------------
    # Old / unused files
    # ------------------------------------------------------------------

    def scan_old_files(self,
                       days: int = 180,
                       top_n: int = 100,
                       progress_cb=None,
                       abort_flag=None) -> list:
        """
        Files not accessed in `days` days.
        C: → user-visible folders only (Documents, Downloads, …)
        Other drives → whole drive scan.
        """
        cutoff = time.time() - days * 86400
        drive_upper = self.drive.upper()

        if drive_upper.startswith("C:"):
            scan_plan = [
                (d, SKIP_DATA_DRIVE)
                for d in [
                    os.path.expanduser("~\\Documents"),
                    os.path.expanduser("~\\Downloads"),
                    os.path.expanduser("~\\Desktop"),
                    os.path.expanduser("~\\Videos"),
                    os.path.expanduser("~\\Music"),
                    os.path.expanduser("~\\Pictures"),
                    os.path.expanduser("~\\OneDrive"),
                ]
                if os.path.exists(d)
            ]
        else:
            scan_plan = [(self.drive, SKIP_DATA_DRIVE)]

        old_files = []
        count = 0

        for root, skip in scan_plan:
            if abort_flag and abort_flag.is_set():
                break
            for path, name, size, atime in _scandir_walk(
                    root, min_size=0, abort_flag=abort_flag, skip_set=skip):
                if atime < cutoff:
                    old_files.append({
                        "path": path, "name": name,
                        "size_bytes": size,
                        "size_str": _fmt_size(size),
                        "last_accessed": atime,
                        "last_accessed_str": datetime.datetime.fromtimestamp(
                            atime).strftime("%Y-%m-%d"),
                        "category": _get_category(Path(name).suffix),
                        "days_unused": int((time.time() - atime) / 86400),
                    })
                    count += 1
                    if progress_cb and count % 50 == 0:
                        progress_cb(count)

        old_files.sort(key=lambda f: f["size_bytes"], reverse=True)
        return old_files[:top_n]

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------

    def scan_downloads(self) -> list:
        folder = os.path.expanduser("~\\Downloads")
        result = []
        if not os.path.exists(folder):
            return result
        for path, name, size, atime in _scandir_walk(
                folder, min_size=0, skip_set=frozenset()):
            result.append({
                "path": path, "name": name,
                "size_bytes": size, "size_str": _fmt_size(size),
                "last_accessed": atime,
                "last_accessed_str": datetime.datetime.fromtimestamp(
                    atime).strftime("%Y-%m-%d"),
                "category": _get_category(Path(name).suffix),
            })
        result.sort(key=lambda f: f["size_bytes"], reverse=True)
        return result

    # ------------------------------------------------------------------
    # By category
    # ------------------------------------------------------------------

    def scan_by_category(self,
                         progress_cb=None,
                         abort_flag=None) -> dict:
        totals = {cat: {"size_bytes": 0, "file_count": 0}
                  for cat in list(CATEGORY_MAP.keys()) + ["Others"]}

        drive_upper = self.drive.upper()
        if drive_upper.startswith("C:"):
            roots = [
                d for d in [
                    os.path.expanduser("~"),
                    os.path.join(self.drive, "Games"),
                    os.path.join(self.drive, "SteamLibrary"),
                ]
                if os.path.exists(d)
            ]
            skip = SKIP_DATA_DRIVE | SKIP_APPDATA_CACHE
        else:
            roots = [self.drive]
            skip = SKIP_DATA_DRIVE

        count = 0
        for root in roots:
            if abort_flag and abort_flag.is_set():
                break
            for path, name, size, atime in _scandir_walk(
                    root, min_size=0, abort_flag=abort_flag, skip_set=skip):
                cat = _get_category(Path(name).suffix)
                totals[cat]["size_bytes"] += size
                totals[cat]["file_count"] += 1
                count += 1
                if progress_cb and count % 500 == 0:
                    progress_cb(count)

        for cat in totals:
            totals[cat]["size_str"] = _fmt_size(totals[cat]["size_bytes"])
        return totals

    # ------------------------------------------------------------------
    # Installed apps
    # ------------------------------------------------------------------

    def scan_installed_apps(self) -> list:
        apps = []
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, reg_path in reg_paths:
            try:
                with winreg.OpenKey(hive, reg_path) as key:
                    i = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, sub_name) as sub:
                                def _qv(n, default="", _s=sub):
                                    try:
                                        return winreg.QueryValueEx(_s, n)[0]
                                    except FileNotFoundError:
                                        return default
                                name = _qv("DisplayName")
                                if name:
                                    size_kb = _qv("EstimatedSize", 0)
                                    sb = int(size_kb) * 1024 if size_kb else 0
                                    apps.append({
                                        "name":             name,
                                        "version":          _qv("DisplayVersion"),
                                        "publisher":        _qv("Publisher"),
                                        "size_bytes":       sb,
                                        "size_str":         _fmt_size(sb) if sb else "Unknown",
                                        "install_date":     _qv("InstallDate"),
                                        "uninstall_string": _qv("UninstallString"),
                                    })
                        except OSError:
                            break
                        i += 1
            except OSError:
                continue

        seen: set = set()
        unique = [a for a in apps
                  if a["name"] not in seen and not seen.add(a["name"])]
        unique.sort(key=lambda a: a["size_bytes"], reverse=True)
        return unique

    # ------------------------------------------------------------------
    # Delete file
    # ------------------------------------------------------------------

    def delete_file(self, path: str) -> tuple:
        try:
            normalized = os.path.normcase(os.path.abspath(path))
            for p in PROTECTED_PATHS:
                if normalized.startswith(p):
                    return False, "Blocked: this is a protected system path."
            if not os.path.exists(path):
                return False, "File not found (already deleted?)."
            size = os.path.getsize(path)
            try:
                os.chmod(path, stat.S_IWRITE)
            except OSError:
                pass
            os.remove(path)
            return True, f"Deleted. Freed {_fmt_size(size)}."
        except PermissionError:
            return False, (f"Access Denied: '{os.path.basename(path)}' "
                           "is in use or protected.")
        except Exception as exc:
            return False, f"Error: {exc}"

    # ------------------------------------------------------------------
    # Full sequential scan
    # ------------------------------------------------------------------

    def run_full_scan(self,
                      progress_cb=None,
                      done_cb=None,
                      min_size_bytes: int = None):
        """
        Run every sub-scan sequentially in one daemon thread.
        Sequential beats parallel for disk I/O (avoids seek contention).
        done_cb(results) is ALWAYS called, even on error.
        """
        if min_size_bytes is None:
            min_size_bytes = self.min_large_file_bytes

        def _worker():
            results: dict = {}
            try:
                with self._scan_lock:
                    self._is_scanning = True

                def _prog(pct: int, msg: str):
                    if progress_cb:
                        try:
                            progress_cb(pct, msg)
                        except Exception:
                            pass

                _prog(5,  "Checking drive usage…")
                results["summary"] = self.get_drive_summary()

                _prog(12, "Scanning Downloads folder…")
                results["downloads"] = self.scan_downloads()

                _prog(20, "Reading installed apps…")
                results["apps"] = self.scan_installed_apps()

                _prog(30, f"Scanning {self.drive} for large files…")
                results["large_files"] = self.scan_large_files(
                    top_n=200,
                    min_size_bytes=min_size_bytes,
                    progress_cb=lambda n: _prog(
                        min(30 + n, 65), "Finding large files…"),
                )

                _prog(68, "Finding old & unused files…")
                results["old_files"] = self.scan_old_files(
                    days=180,
                    progress_cb=lambda n: _prog(
                        68 + min(n // 5, 12), "Finding old files…"),
                )

                _prog(82, "Categorising files by type…")
                results["by_category"] = self.scan_by_category(
                    progress_cb=lambda n: _prog(
                        82 + min(n // 500, 15), "Categorising…"),
                )

                _prog(100, "Scan complete!")
                self._scan_results = results

            except Exception as exc:
                logger.error("run_full_scan: %s", exc)
                results.setdefault("large_files", [])
                results.setdefault("old_files",   [])
                results.setdefault("by_category", {})
                results.setdefault("downloads",   [])
                results.setdefault("apps",        [])
                results["error"] = str(exc)

            finally:
                with self._scan_lock:
                    self._is_scanning = False
                if done_cb:
                    try:
                        done_cb(results)
                    except Exception as exc:
                        logger.error("done_cb raised: %s", exc)

        threading.Thread(
            target=_worker, daemon=True, name="DiskScanner"
        ).start()

    # ------------------------------------------------------------------
    # Chatbot summary
    # ------------------------------------------------------------------

    def get_chatbot_summary(self) -> str:
        try:
            s  = self.get_drive_summary()
            dl = self.scan_downloads()
            dl_sz = _fmt_size(sum(f["size_bytes"] for f in dl))
            lines = [
                (f"Drive {self.drive}: {s['used_str']} used / "
                 f"{s['total_str']} ({s['percent']}% full, "
                 f"{s['free_str']} free)"),
                f"Downloads: {len(dl)} files, {dl_sz} total",
            ]
            if self._scan_results:
                lf = self._scan_results.get("large_files", [])
                if lf:
                    lines.append("Top 5 largest files:")
                    for f in lf[:5]:
                        lines.append(
                            f"  - {f['name']} ({f['size_str']}) "
                            f"last accessed {f['last_accessed_str']}"
                        )
                old = self._scan_results.get("old_files", [])
                if old:
                    sz = _fmt_size(sum(f["size_bytes"] for f in old))
                    lines.append(
                        f"Unused (6+ months): {len(old)} files, {sz}"
                    )
            return "\n".join(lines)
        except Exception as exc:
            return f"Disk analysis unavailable: {exc}"
