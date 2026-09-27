import sqlite3
import os
from datetime import datetime, timedelta

# Resolve DB path relative to the project root (two levels above this module)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB_PATH = os.path.join(_PROJECT_ROOT, "techguard_telemetry.db")

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = _DEFAULT_DB_PATH
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    ram_usage REAL,
                    disk_free REAL,
                    top_process TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    detail TEXT,
                    severity TEXT DEFAULT 'WARNING'
                )
            """)
            conn.commit()

    def log_metrics(self, cpu, ram, disk_free, top_proc):
        """Logs a snapshot of system metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO system_metrics (cpu_usage, ram_usage, disk_free, top_process)
                    VALUES (?, ?, ?, ?)
                """, (cpu, ram, disk_free, top_proc))
                conn.commit()
            self.prune_old_data()
        except Exception as e:
            print(f"Database Log Error: {e}")

    def get_historical_context(self, hours=24):
        """Returns summarizing stats for the last X hours."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                time_limit = datetime.utcnow() - timedelta(hours=hours)
                cursor.execute("""
                    SELECT cpu_usage, ram_usage, disk_free, top_process, timestamp 
                    FROM system_metrics 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (time_limit,))
                rows = cursor.fetchall()
                
                if not rows:
                    return "No historical data available for this period."
                
                avg_cpu = sum(row[0] for row in rows) / len(rows)
                avg_ram = sum(row[1] for row in rows) / len(rows)
                
                summary = f"Summary of last {hours} hours:\n"
                summary += f"- Avg CPU: {avg_cpu:.1f}%\n"
                summary += f"- Avg RAM: {avg_ram:.1f}%\n"
                summary += f"- Most frequent top process: {self._get_most_frequent(rows)}\n"
                return summary
        except Exception as e:
            return f"Error fetching history: {str(e)}"

    def _get_most_frequent(self, rows):
        from collections import Counter
        procs = [row[3] for row in rows if row[3] != "Scanning..."]
        if not procs: return "None"
        return Counter(procs).most_common(1)[0][0]

    def log_event(self, event_type, detail, severity="WARNING"):
        """Logs a discrete system event (network drop, CPU spike, etc.)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO event_log (event_type, detail, severity)
                    VALUES (?, ?, ?)
                """, (event_type, detail, severity))
                conn.commit()
        except Exception as e:
            print(f"Event Log Error: {e}")

    def get_predictions(self, days=7):
        """
        Reads the event_log for the last N days, counts recurring patterns,
        and returns a list of plain-English prediction strings.
        """
        predictions = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                time_limit = datetime.utcnow() - timedelta(days=days)
                cursor.execute("""
                    SELECT event_type, COUNT(*) as cnt
                    FROM event_log
                    WHERE timestamp > ?
                    GROUP BY event_type
                    ORDER BY cnt DESC
                """, (time_limit,))
                rows = cursor.fetchall()

            messages = {
                "NETWORK_DROP": (
                    "🌐 Your internet connection has dropped {n} time(s) in the last {d} days. "
                    "This pattern suggests an unstable adapter or router. "
                    "Try updating your network driver or restarting your router."
                ),
                "CPU_SPIKE": (
                    "🔥 Your CPU hit dangerous levels {n} time(s) in the last {d} days. "
                    "A background app may be misbehaving. "
                    "Check the Top CPU App stats and consider closing unused programs."
                ),
                "DISK_PRESSURE": (
                    "💾 Your disk ran critically low on space {n} time(s) in the last {d} days. "
                    "Consider running the System Cleaner to free up space."
                ),
                "APP_CRASH": (
                    "💥 Windows logged {n} application crash(es) in the last {d} days. "
                    "Check the Event Logs for the crashing app and consider reinstalling it."
                ),
            }

            for event_type, count in rows:
                if count >= 2 and event_type in messages:
                    predictions.append(
                        messages[event_type].format(n=count, d=days)
                    )
        except Exception as e:
            print(f"Prediction Error: {e}")

        return predictions

    def get_recent_events(self, hours=24, limit=20):
        """Returns the most recent raw events for context."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                time_limit = datetime.utcnow() - timedelta(hours=hours)
                cursor.execute("""
                    SELECT timestamp, event_type, detail, severity
                    FROM event_log
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (time_limit, limit))
                return cursor.fetchall()
        except Exception as e:
            print(f"Recent Events Error: {e}")
            return []

    def prune_old_data(self, days=7):
        """Deletes data older than X days to save space."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                time_limit = datetime.utcnow() - timedelta(days=days)
                cursor.execute("DELETE FROM system_metrics WHERE timestamp < ?", (time_limit,))
                cursor.execute("DELETE FROM event_log WHERE timestamp < ?", (time_limit,))
                conn.commit()
        except Exception as e:
            print(f"Database Prune Error: {e}")
