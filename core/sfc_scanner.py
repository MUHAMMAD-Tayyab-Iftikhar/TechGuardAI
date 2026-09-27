"""
sfc_scanner.py
--------------
Runs Windows System File Checker (sfc /scannow) in a background thread
and parses the result into a structured dict.

Requirements: Administrator privileges (sfc refuses to run without them).

CBS log at C:\\Windows\\Logs\\CBS\\CBS.log is always written in English
regardless of Windows locale, so it is used as a reliable fallback.
"""

import os
import re
import time
import ctypes
import threading
import subprocess

_CBS_LOG           = r"C:\Windows\Logs\CBS\CBS.log"
_ESTIMATED_SECONDS = 200          # shown to user; real time varies 90-360 s


# ── Public helpers ────────────────────────────────────────────────────────────

def is_admin() -> bool:
    """True when the current process has Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_sfc(progress_cb=None, done_cb=None):
    """
    Launch sfc /scannow in a daemon thread.

    progress_cb(pct: int, message: str)  called every ~3 s while scanning
    done_cb(result: dict)                called once when finished

    Result keys:
        status    "clean" | "fixed" | "unfixable" | "no_admin" | "error"
        title     Short headline
        detail    Plain-English explanation
        log_path  Path to CBS.log (or None if absent)
        steps     List of next-step strings (populated for "unfixable")
    """
    threading.Thread(
        target=_worker, args=(progress_cb, done_cb), daemon=True
    ).start()


# ── Internal worker ───────────────────────────────────────────────────────────

def _worker(progress_cb, done_cb):
    result = {
        "status":   "unknown",
        "title":    "Scan complete",
        "detail":   "",
        "log_path": _CBS_LOG if os.path.exists(_CBS_LOG) else None,
        "steps":    [],
    }

    # ── Admin check ──────────────────────────────────────────────────────────
    if not is_admin():
        result.update({
            "status": "no_admin",
            "title":  "Administrator access required",
            "detail": (
                "The System File Checker must run as Administrator. "
                "Right-click TechGuardAI.exe and choose "
                "\"Run as administrator\", then try again."
            ),
        })
        if done_cb:
            done_cb(result)
        return

    # ── Simulated progress (sfc doesn't stream reliably) ────────────────────
    stop_flag = threading.Event()

    def _progress_loop():
        start = time.time()
        while not stop_flag.is_set():
            elapsed = time.time() - start
            pct = min(92, int((elapsed / _ESTIMATED_SECONDS) * 90) + 3)
            if progress_cb:
                try:
                    progress_cb(pct, f"Scanning Windows system files… ({int(elapsed)}s elapsed)")
                except Exception:
                    pass
            time.sleep(3)

    threading.Thread(target=_progress_loop, daemon=True).start()

    # ── Run sfc /scannow ──────────────────────────────────────────────────────
    try:
        proc = subprocess.run(
            ["sfc", "/scannow"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=600,
        )

        # SFC writes UTF-16 LE on modern Windows; try several encodings
        raw = (proc.stdout or b"") + (proc.stderr or b"")
        output = ""
        for enc in ("utf-16-le", "utf-16", "cp1252", "utf-8"):
            try:
                decoded = raw.decode(enc).replace("\x00", "").strip()
                if len(decoded) > 20:
                    output = decoded
                    break
            except Exception:
                continue

        result["raw_output"] = output
        out_low = output.lower()

        if "did not find any integrity violations" in out_low:
            result.update({
                "status": "clean",
                "title":  "All Windows system files are healthy",
                "detail": (
                    "No corrupted or missing files were found. "
                    "Your Windows installation is fully intact."
                ),
            })
        elif any(x in out_low for x in (
                "found corrupt files and successfully repaired",
                "found corrupt files and repaired")):
            result.update({
                "status": "fixed",
                "title":  "Corrupted files found and repaired",
                "detail": (
                    "Windows found some damaged system files and fixed them automatically. "
                    "A restart is recommended to complete the repair."
                ),
                "steps": ["Restart your PC now to apply the repairs"],
            })
        elif "found corrupt files but was unable to fix" in out_low:
            result.update({
                "status": "unfixable",
                "title":  "Corrupted files found — could not be repaired automatically",
                "detail": (
                    "Windows found damaged system files but could not repair them. "
                    "This usually means the Windows repair source itself is corrupted. "
                    "The DISM tool can fix this in ~10 minutes."
                ),
                "steps": [
                    "Open Start → type cmd → right-click Command Prompt → Run as administrator",
                    'Type:  DISM /Online /Cleanup-Image /RestoreHealth  and press Enter',
                    "Wait ~10 minutes for DISM to finish, then run this scan again",
                ],
            })
        elif "could not perform the requested operation" in out_low:
            result.update({
                "status": "error",
                "title":  "Scan could not run",
                "detail": (
                    "Windows was unable to start the scan. Another SFC may be running, "
                    "or the system is busy. Try restarting and scanning again."
                ),
            })
        else:
            # Fallback to CBS log
            result = _parse_cbs_log(result)

    except subprocess.TimeoutExpired:
        result.update({
            "status": "error",
            "title":  "Scan timed out",
            "detail": "The scan took too long. Restart your PC and try again.",
        })
    except FileNotFoundError:
        result.update({
            "status": "error",
            "title":  "SFC not found",
            "detail": "The System File Checker could not be found on this system.",
        })
    except Exception as e:
        result.update({
            "status": "error",
            "title":  "Scan error",
            "detail": str(e),
        })
    finally:
        stop_flag.set()
        if progress_cb:
            try:
                progress_cb(100, "Scan complete")
            except Exception:
                pass

    if done_cb:
        done_cb(result)


def _parse_cbs_log(result: dict) -> dict:
    """
    Fallback: read the tail of CBS.log (always English) to determine result.
    """
    try:
        with open(_CBS_LOG, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 65536))   # read last 64 KB
            tail = f.read()

        if "[SR] Verify complete" in tail:
            cannot_repair = "[SR] Cannot repair" in tail or "[SR] Could not" in tail
            did_repair    = "[SR] Repairing" in tail

            if cannot_repair:
                result.update({
                    "status": "unfixable",
                    "title":  "Corrupted files found — could not be repaired",
                    "detail": "Windows found and could not fix damaged system files. Run DISM to repair the source.",
                    "steps": [
                        "Open Start → cmd → right-click → Run as administrator",
                        "Type: DISM /Online /Cleanup-Image /RestoreHealth",
                        "Wait ~10 minutes, then run this scan again",
                    ],
                })
            elif did_repair:
                result.update({
                    "status": "fixed",
                    "title":  "Corrupted files found and repaired",
                    "detail": "Windows repaired some system files. Restart your PC to complete the fix.",
                    "steps":  ["Restart your PC to complete the repair"],
                })
            else:
                result.update({
                    "status": "clean",
                    "title":  "All Windows system files are healthy",
                    "detail": "No corrupted or missing files were found.",
                })

    except Exception:
        if not result.get("detail"):
            result["detail"] = (
                "Results could not be read automatically. "
                f"Check the scan log at {_CBS_LOG} for details."
            )

    return result
