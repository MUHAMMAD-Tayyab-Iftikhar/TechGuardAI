"""
Admin privilege checker for Windows.
Checks if the current process has administrator privileges.
"""

import ctypes
import sys

def is_admin() -> bool:
    """
    Check if the current process is running with administrator privileges.
    
    Returns:
        bool: True if running as admin, False otherwise
    """
    try:
        if sys.platform != 'win32':
            return False
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


