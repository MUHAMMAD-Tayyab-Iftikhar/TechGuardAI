import psutil
import socket
import winreg
import wmi

class SecurityScanner:
    def __init__(self):
        try:
            self.wmi_client = wmi.WMI()
        except:
            self.wmi_client = None

    def get_security_snapshot(self):
        """Aggregates security-related info into a snapshot."""
        return {
            "listening_ports": self._get_listening_ports(),
            "firewall_defender": self._get_firewall_status(),
            "startup_programs": self._get_startup_programs()
        }

    def _get_listening_ports(self):
        """Scans for open listening ports."""
        ports = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN':
                    ports.append({
                        "port": conn.laddr.port,
                        "pid": conn.pid,
                        "ip": conn.laddr.ip
                    })
        except Exception:
            pass
        return ports[:10] # Limit to top 10

    def _get_firewall_status(self):
        """Checks if Windows Defender/Firewall is active using WMI with SecurityCenter2."""
        try:
            # Shift to SecurityCenter2 namespace for security products
            sc2_client = wmi.WMI(namespace=r"root\SecurityCenter2")
            antivirus = sc2_client.AntivirusProduct()
            firewall = sc2_client.FirewallProduct()
            
            av_names = [av.displayName for av in antivirus]
            fw_names = [fw.displayName for fw in firewall]
            
            return {
                "antivirus": av_names if av_names else "Not Found/Disabled",
                "firewall": fw_names if fw_names else "Not Found/Disabled"
            }
        except Exception as e:
            # Fallback for systems where SecurityCenter2 might be inaccessible
            return f"Security Query Error: {e}"

    def _get_startup_programs(self):
        """Lists recently added startup programs from the Registry."""
        startups = []
        paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
        ]
        
        for root, path in paths:
            try:
                with winreg.OpenKey(root, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        name, val, _ = winreg.EnumValue(key, i)
                        startups.append(name)
            except WindowsError:
                continue
        return startups[:15] # Limit list
