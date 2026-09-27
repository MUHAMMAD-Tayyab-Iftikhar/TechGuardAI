"""Quick test to verify all 3 diagnostic features work and output is readable."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("TEST 1: Thermal Throttle Detector")
print("=" * 60)
try:
    from core.thermal_monitor import ThermalMonitor
    t = ThermalMonitor()
    data = t.get_throttle_status()
    print(f"  Status  : {data['verdict']}")
    print(f"  Speed   : {data['current_mhz']} MHz / {data['max_mhz']} MHz ({data['percent']}%)")
    print(f"  Throttled: {data['throttled']}")
    print("  Tips:")
    for tip in data.get("tips", []):
        print(f"    - {tip}")
    temp = t.get_cpu_temperature()
    print(f"  Temp    : {temp}°C" if temp else "  Temp    : Not available")
except Exception as e:
    print(f"  FAILED: {e}")

print()
print("=" * 60)
print("TEST 2: Event Log Miner (last 24h)")
print("=" * 60)
try:
    from core.event_log_miner import EventLogMiner
    miner = EventLogMiner()
    events = miner.get_critical_events(hours=24)
    print(f"  Found {len(events)} event(s)")
    for ev in events[:5]:
        print(f"  [{ev['severity']}] [{ev['time']}] {ev['title']}")
        print(f"    -> {ev['explanation'][:120]}")
except Exception as e:
    print(f"  FAILED: {e}")

print()
print("=" * 60)
print("TEST 3: SMART Drive Health Monitor")
print("=" * 60)
try:
    from core.drive_health import DriveHealthMonitor
    dm = DriveHealthMonitor()
    drives = dm.get_all_drives_health()
    print(f"  Found {len(drives)} drive(s)")
    for d in drives:
        print(f"  {d['grade_display']}  {d['model']}  ({d['type']}, {d['size_gb']} GB)")
        for issue in d['issues']:
            print(f"    - {issue}")
except Exception as e:
    print(f"  FAILED: {e}")

print()
print("All tests done.")
