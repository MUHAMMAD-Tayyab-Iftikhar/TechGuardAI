import psutil
import wmi
import datetime

class ThermalMonitor:
    def __init__(self):
        try:
            self.wmi_client = wmi.WMI()
        except Exception:
            self.wmi_client = None

    def get_throttle_status(self):
        """
        Detects whether the CPU is thermally throttled.
        Compares current clock speed vs max clock speed.
        Returns a result dict with full diagnostics.
        """
        result = {
            "throttled": False,
            "current_mhz": 0,
            "max_mhz": 0,
            "percent": 100.0,
            "verdict": "Unknown",
            "tips": []
        }

        # --- Method 1: WMI (most accurate) ---
        if self.wmi_client:
            try:
                processors = self.wmi_client.Win32_Processor()
                if processors:
                    proc = processors[0]
                    current = getattr(proc, "CurrentClockSpeed", 0)
                    max_speed = getattr(proc, "MaxClockSpeed", 0)

                    if current and max_speed and max_speed > 0:
                        result["current_mhz"] = current
                        result["max_mhz"] = max_speed
                        pct = round((current / max_speed) * 100, 1)
                        result["percent"] = pct

                        if pct < 60:
                            result["throttled"] = True
                            result["verdict"] = "Severely Throttled"
                            result["tips"] = [
                                "Your CPU is running at less than 60% of its rated speed.",
                                "Likely cause: Extreme overheating. Check if fans are spinning.",
                                "Action: Clean dust from CPU heatsink/laptop vents immediately.",
                                "Action: Re-apply thermal paste if PC is 3+ years old."
                            ]
                        elif pct < 85:
                            result["throttled"] = True
                            result["verdict"] = "Throttled"
                            result["tips"] = [
                                f"CPU running at {pct}% of max speed due to thermal pressure.",
                                "Action: Improve airflow — ensure vents are not blocked.",
                                "Action: Consider a cooling pad if using a laptop.",
                                "Action: Check which apps are hogging CPU and close them."
                            ]
                        else:
                            result["throttled"] = False
                            result["verdict"] = "Normal"
                            result["tips"] = ["CPU is performing at full rated speed. No throttling detected."]
                        return result
            except Exception as e:
                print(f"ThermalMonitor WMI error: {e}")

        # --- Method 2: psutil fallback ---
        try:
            freq = psutil.cpu_freq()
            if freq:
                result["current_mhz"] = round(freq.current)
                result["max_mhz"] = round(freq.max) if freq.max else round(freq.current)
                if freq.max and freq.max > 0:
                    pct = round((freq.current / freq.max) * 100, 1)
                    result["percent"] = pct
                    result["throttled"] = pct < 85
                    result["verdict"] = "Throttled" if pct < 85 else "Normal"
                    if pct < 85:
                        result["tips"] = [
                            f"CPU running at {pct}% of max speed.",
                            "Action: Check for high CPU usage apps and close unnecessary ones.",
                            "Action: Clean CPU/GPU heatsink vents."
                        ]
                    else:
                        result["tips"] = ["CPU is performing at normal frequency. No throttling detected."]
                else:
                    result["verdict"] = "Normal (Max Speed Unknown)"
                    result["tips"] = ["Could not determine maximum CPU frequency for comparison."]
        except Exception as e:
            result["verdict"] = f"Scan Error: {e}"

        return result

    def get_cpu_temperature(self):
        """
        Tries to get CPU temperature via WMI.
        Returns temperature in Celsius, or None if unavailable.
        NOTE: Requires HWiNFO or Open Hardware Monitor running
              as a WMI provider for accurate temps on most systems.
        """
        if not self.wmi_client:
            return None
        try:
            # Try MSAcpi_ThermalZoneTemperature (works on some systems)
            w = wmi.WMI(namespace="root\\wmi")
            temps = w.MSAcpi_ThermalZoneTemperature()
            if temps:
                # Convert from tenths of Kelvin to Celsius
                celsius = (temps[0].CurrentTemperature / 10.0) - 273.15
                return round(celsius, 1)
        except Exception:
            pass
        return None
