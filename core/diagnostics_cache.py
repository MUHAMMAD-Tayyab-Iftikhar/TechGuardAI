"""
Shared singleton cache for diagnostic scan results.
DiagnosticsScreen writes here after each scan.
TechGuardBrain reads from here to enrich the chatbot prompt.
"""

_cache = {
    "thermal": None,   # dict from ThermalMonitor.get_throttle_status()
    "events":  None,   # list from EventLogMiner.get_critical_events()
    "drives":  None,   # list from DriveHealthMonitor.get_all_drives_health()
}


def update(key: str, data):
    """Store scan result. key must be 'thermal', 'events', or 'drives'."""
    if key in _cache:
        _cache[key] = data


def get_snapshot() -> str:
    """
    Returns a plain-English summary of all cached diagnostics for the AI prompt.
    Returns an empty string if nothing has been scanned yet.
    """
    parts = []

    # ── Thermal ──────────────────────────────────────────────
    thermal = _cache.get("thermal")
    if thermal:
        verdict = thermal.get("verdict", "Unknown")
        pct = thermal.get("percent", 0)
        curr = thermal.get("current_mhz", 0)
        max_mhz = thermal.get("max_mhz", 0)
        throttled = thermal.get("throttled", False)

        if throttled:
            parts.append(
                f"THERMAL ALERT: CPU is throttled ({verdict}). Running at {curr} MHz "
                f"out of {max_mhz} MHz ({pct}% of full speed). "
                f"Recommendations: {'; '.join(thermal.get('tips', []))}"
            )
        else:
            parts.append(
                f"THERMAL STATUS: Normal. CPU running at full speed "
                f"({curr} MHz / {max_mhz} MHz, {pct}%)."
            )

    # ── Event Log ─────────────────────────────────────────────
    events = _cache.get("events")
    if events is not None:
        critical = [e for e in events if e.get("severity") == "Critical"]
        warnings  = [e for e in events if e.get("severity") == "Warning"]
        if not events:
            parts.append("EVENT LOG (last 24h): No critical errors found.")
        else:
            summary_lines = [
                f"EVENT LOG (last 24h): {len(critical)} critical error(s), {len(warnings)} warning(s)."
            ]
            for ev in events[:8]:  # send top 8 to avoid prompt bloat
                summary_lines.append(
                    f"  - [{ev['severity']}] {ev['title']}: {ev['explanation'][:120]}"
                )
            parts.append("\n".join(summary_lines))

    # ── Drive Health ─────────────────────────────────────────
    drives = _cache.get("drives")
    if drives is not None:
        drive_lines = ["DRIVE HEALTH:"]
        for d in drives:
            issue_str = "; ".join(d.get("issues", []))
            drive_lines.append(
                f"  - {d['model']} ({d['type']}, {d['size_gb']} GB): "
                f"{d['health_grade']} — {issue_str}"
            )
        parts.append("\n".join(drive_lines))

    return "\n\n".join(parts)
