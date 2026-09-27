import sys
import os
import time

# Add root to sys.path
sys.path.append(os.getcwd())

from core.action_handler import ActionHandler
from core.database_manager import DatabaseManager
from core.security_scanner import SecurityScanner

def test_agentic_actions():
    print("--- Testing Agentic Actions ---")
    handler = ActionHandler()
    
    # Test protected process
    # Use a likely existing but protected PID (like 4 - System)
    success, msg = handler.terminate_process(4) 
    print(f"Protected Process Test: {msg}")
    if not success and "critical system process" in msg:
        print("Success: Protection logic worked.")
    else:
        print(f"Failure: Protection logic did not behave as expected. Msg: {msg}")
    
    # Test temp clear (dry run check)
    print("Testing Temp Clear Logic...")
    # We won't actually clear everything in a test, but check if it runs
    success, msg = handler.clear_temp_files()
    print(f"Temp Clear Result: {msg}")

def test_telemetry():
    print("\n--- Testing Telemetry Database ---")
    db = DatabaseManager("test_telemetry_v2.db")
    db.log_metrics(10.5, 45.2, 50.0, "TestProcess.exe")
    db.log_metrics(15.0, 48.0, 49.5, "TestProcess.exe")
    
    # Small sleep to ensure timestamps are within range if there's any lag
    time.sleep(1)
    
    context = db.get_historical_context(1)
    print(f"Historical Context:\n{context}")
    
    if "Avg CPU: 12.8" in context or "Avg CPU: 12.7" in context:
        print("Success: Database logging and averaging works.")
    else:
        print("Failure: Data mismatch.")

def test_security():
    print("\n--- Testing Security Scanner ---")
    scanner = SecurityScanner()
    snapshot = scanner.get_security_snapshot()
    
    print(f"Firewall Status: {snapshot['firewall_defender']}")
    print(f"Listening Ports: {len(snapshot['listening_ports'])} found.")
    print(f"Startup Apps: {len(snapshot['startup_programs'])} found.")
    
    if snapshot['listening_ports']:
        print(f"First Port: {snapshot['listening_ports'][0]}")
    
    if snapshot['startup_programs']:
        print(f"First Startup: {snapshot['startup_programs'][0]}")

if __name__ == "__main__":
    test_agentic_actions()
    test_telemetry()
    test_security()
