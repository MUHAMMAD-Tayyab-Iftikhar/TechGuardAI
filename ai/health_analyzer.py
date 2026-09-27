import psutil
import time

class HealthAnalyzer:
    def __init__(self):
        self.boot_time = psutil.boot_time()

    def analyze_health(self, cpu, ram, disk, net_info, bat_info, heavy_app):
        insights = []
        status = "Healthy"
        score = 100

        # --- 1. Uptime Check (Prevent Lag) ---
        uptime_days = (time.time() - self.boot_time) / (24 * 3600)
        if uptime_days > 7:
            score -= 5
            insights.append({
                "type": "Maintenance",
                "msg": f"System has been running for {int(uptime_days)} days without a restart.",
                "action": "Restart your PC to clear kernel cache and fix micro-stutters."
            })

        # --- 2. CPU & Process Correlation ---
        if cpu['usage'] > 85:
            status = "Critical"
            score -= 30
            insights.append({
                "type": "Performance",
                "msg": f"Processor is under extreme load ({cpu['usage']}%) likely due to '{heavy_app}'.",
                "action": "If you are not gaming/rendering, end this task in the Process Manager."
            })
        elif cpu['usage'] > 60:
            if status != "Critical": status = "Warning"
            score -= 10
            insights.append({
                "type": "Performance",
                "msg": f"CPU usage is elevated. '{heavy_app}' is working hard.",
                "action": "Ensure laptop is plugged in for max performance."
            })

        # --- 3. RAM Bottleneck Analysis ---
        if ram['percent'] > 90:
            status = "Critical"
            score -= 30
            insights.append({
                "type": "Memory",
                "msg": f"RAM is critically full ({ram['percent']}%)! System may freeze.",
                "action": f"Close memory-heavy apps like '{heavy_app}' immediately."
            })
        elif ram['percent'] > 75:
            score -= 10
            insights.append({
                "type": "Memory",
                "msg": "Multitasking capability is reduced (RAM > 75%).",
                "action": "Close unused browser tabs to free up space."
            })

        # --- 4. Storage Health ---
        if disk['percent'] > 90:
            status = "Critical"
            score -= 20
            insights.append({
                "type": "Storage",
                "msg": f"Drive C: is dangerously full ({disk['free']} GB left). Windows may crash.",
                "action": "Run the System Cleaner or empty Recycle Bin now."
            })
        
        # --- 5. Battery & Power Logic ---
        # bat_info comes as string: "85% (Charging)"
        if "Discharging" in bat_info:
            try:
                percent = int(bat_info.split('%')[0])
                if percent < 20:
                    status = "Warning"
                    insights.append({
                        "type": "Power",
                        "msg": "Battery is critically low. Performance is throttled.",
                        "action": "Plug in your charger to restore full system speed."
                    })
            except:
                pass # safely ignore parsing errors

        # --- 6. Network Idle Check ---
        # If net usage is 0 but CPU is high, it might be a local virus or stuck process
        if net_info['down'] == "0.0 KB/s" and cpu['usage'] > 50:
             insights.append({
                "type": "Security",
                "msg": "High CPU usage detected with NO internet activity.",
                "action": "This is suspicious. Check if an offline virus scan is running."
            })

        # --- Default Healthy Message ---
        if not insights:
            insights.append({
                "type": "System",
                "msg": "All systems nominal. Performance is optimal.",
                "action": "No actions required."
            })

        return {
            "status": status,
            "score": max(0, score),
            "insights": insights
        }