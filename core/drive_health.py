import subprocess
import wmi
import re

class DriveHealthMonitor:
    def __init__(self):
        try:
            self.wmi_client = wmi.WMI()
        except Exception:
            self.wmi_client = None

    def get_all_drives_health(self):
        """
        Returns a list of drive health reports.
        Each entry: {name, model, serial, type, status, health_grade, issues, temp_c, size_gb}
        """
        drives = []

        # --- Primary: WMI Win32_DiskDrive ---
        if self.wmi_client:
            try:
                disk_drives = self.wmi_client.Win32_DiskDrive()
                for disk in disk_drives:
                    report = self._analyze_wmi_drive(disk)
                    drives.append(report)
            except Exception as e:
                print(f"DriveHealthMonitor WMI error: {e}")

        # --- Fallback: WMIC command-line ---
        if not drives:
            drives = self._fallback_wmic_scan()

        return drives

    def _analyze_wmi_drive(self, disk):
        """Builds a health report from a WMI Win32_DiskDrive object."""
        issues = []
        health_grade = "Healthy"

        name = getattr(disk, "Caption", "Unknown Drive")
        model = getattr(disk, "Model", name)
        serial = getattr(disk, "SerialNumber", "N/A")
        status = getattr(disk, "Status", "Unknown")
        media_type = getattr(disk, "MediaType", "Unknown")
        size_bytes = getattr(disk, "Size", 0)
        size_gb = round(int(size_bytes) / (1024**3), 1) if size_bytes else 0

        # Determine drive type
        drive_type = "SSD" if ("SSD" in model.upper() or "SOLID" in media_type.upper()) else "HDD"

        # Assess WMI Status field
        if status and status.lower() not in ("ok", "pred fail"):
            health_grade = "Critical"
            issues.append(f"Drive status reported by Windows: '{status}' — investigate immediately.")
        elif status and status.lower() == "pred fail":
            health_grade = "Warning"
            issues.append("Windows predicts this drive may fail soon. Back up your data now.")

        # Assess partition count (0 partitions = possibly dead drive)
        partitions = getattr(disk, "Partitions", None)
        if partitions is not None and int(partitions) == 0:
            issues.append("No partitions detected on this drive — it may be uninitialized or failing.")

        # Try to get SMART status via Win32_DiskDriveToDiskPartition
        smart_status = self._get_smart_status(model)
        if smart_status:
            if smart_status.lower() == "pred fail":
                health_grade = "Critical"
                issues.append("SMART reports: 'Predicted Failure' — your drive is about to fail. Back up files IMMEDIATELY.")
            elif smart_status.lower() != "ok":
                if health_grade == "Healthy":
                    health_grade = "Warning"
                issues.append(f"SMART Status: {smart_status}")

        if not issues:
            issues.append("No known issues detected. Drive appears healthy.")

        # Derive a colour grade
        if health_grade == "Healthy":
            grade_display = "Healthy"
        elif health_grade == "Warning":
            grade_display = "Warning"
        else:
            grade_display = "Critical"

        return {
            "name": name,
            "model": model,
            "serial": serial.strip(),
            "type": drive_type,
            "status": status,
            "health_grade": health_grade,
            "grade_display": grade_display,
            "issues": issues,
            "temp_c": None,  # Temperature requires Open Hardware Monitor or vendor tools
            "size_gb": size_gb,
        }

    def _get_smart_status(self, model_hint):
        """Attempts to read SMART failure status via WMI."""
        if not self.wmi_client:
            return None
        try:
            # Win32_DiskDrive has a Status field; for extended SMART we use MSStorageDriver_FailurePredictStatus
            w = wmi.WMI(namespace="root\\wmi")
            statuses = w.MSStorageDriver_FailurePredictStatus()
            for s in statuses:
                reason = getattr(s, "Reason", 0)
                pred_failure = getattr(s, "PredictFailure", False)
                if pred_failure:
                    return "pred fail"
            return "ok"
        except Exception:
            return None

    def _fallback_wmic_scan(self):
        """Runs 'wmic diskdrive' CLI as a fallback when WMI is unavailable."""
        drives = []
        try:
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "Caption,Status,Size,MediaType", "/format:csv"],
                capture_output=True, text=True, timeout=15
            )
            lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip() and "Caption" not in l]
            for line in lines:
                parts = line.split(",")
                if len(parts) >= 4:
                    name = parts[1] if len(parts) > 1 else "Unknown"
                    media = parts[2] if len(parts) > 2 else ""
                    size_bytes = parts[3] if len(parts) > 3 else "0"
                    status = parts[4] if len(parts) > 4 else "Unknown"
                    try:
                        size_gb = round(int(size_bytes) / (1024**3), 1)
                    except:
                        size_gb = 0

                    drives.append({
                        "name": name,
                        "model": name,
                        "serial": "N/A",
                        "type": "SSD" if "SSD" in name.upper() else "HDD",
                        "status": status,
                        "health_grade": "Warning" if status.lower() != "ok" else "Healthy",
                        "grade_display": "Healthy" if status.lower() == "ok" else "Warning",
                        "issues": [f"Status: {status}"] if status.lower() != "ok" else ["No issues detected."],
                        "temp_c": None,
                        "size_gb": size_gb,
                    })
        except Exception as e:
            print(f"Fallback wmic scan failed: {e}")
            drives.append({
                "name": "Unknown Drive",
                "model": "Unknown",
                "serial": "N/A",
                "type": "Unknown",
                "status": "Scan Failed",
                "health_grade": "Unknown",
                "grade_display": "Unknown",
                "issues": [f"Drive scan failed: {e}. Try running TechGuardAI as Administrator."],
                "temp_c": None,
                "size_gb": 0,
            })
        return drives
