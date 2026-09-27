"""
mode_manager.py
---------------
Global toggle between Beginner (simplified) and Advanced (Expert) mode.
Persists the user's preference in config.ini under [UserPrefs].

Usage
-----
    from utils import mode_manager

    if mode_manager.is_beginner():
        # show plain English
        ...

    mode_manager.toggle()                    # flip and notify callbacks
    mode_manager.register_callback(my_fn)   # called with new_mode str on toggle
"""

import os
import sys
import configparser

_SECTION = "UserPrefs"
_KEY     = "mode"
_mode    = "beginner"       # safe default for new users
_callbacks: list = []


# ── Config path ───────────────────────────────────────────────────────────────

def _get_config_path() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "config.ini")


# ── Persistence ───────────────────────────────────────────────────────────────

def _load():
    global _mode
    config = configparser.ConfigParser()
    path = _get_config_path()
    if os.path.exists(path):
        config.read(path)
        _mode = config.get(_SECTION, _KEY, fallback="beginner")


def _save():
    config = configparser.ConfigParser()
    path = _get_config_path()
    if os.path.exists(path):
        config.read(path)
    if not config.has_section(_SECTION):
        config.add_section(_SECTION)
    config.set(_SECTION, _KEY, _mode)
    try:
        with open(path, "w") as f:
            config.write(f)
    except Exception:
        pass


_load()   # initialise from disk on import


# ── Public API ────────────────────────────────────────────────────────────────

def is_beginner() -> bool:
    """True when the app is in Beginner (simplified) mode."""
    return _mode == "beginner"


def get_mode() -> str:
    """Returns 'beginner' or 'advanced'."""
    return _mode


def toggle():
    """Flip the mode and notify all registered callbacks."""
    global _mode
    _mode = "advanced" if _mode == "beginner" else "beginner"
    _save()
    for cb in list(_callbacks):
        try:
            cb(_mode)
        except Exception:
            pass


def register_callback(cb):
    """Register fn(new_mode: str) — called whenever the mode changes."""
    if cb not in _callbacks:
        _callbacks.append(cb)
