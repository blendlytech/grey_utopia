"""paths.py -- Resource and user-data path resolution for source and frozen (PyInstaller) runs.

Bundled read-only content (data/, web/) is looked up relative to the PyInstaller
extraction root when frozen. Writable state (saves/, legacy.json) always lives in
a persistent, per-user directory so it survives across app updates and is never
written into the (potentially read-only or ephemeral) install/extraction path.
"""
from __future__ import annotations
import os
import sys


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> str:
    """Root directory for bundled read-only resources (data/, web/)."""
    if is_frozen():
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def user_data_dir() -> str:
    """Writable, persistent directory root for saves/legacy state.

    Source runs keep writing next to the project (unchanged dev behavior).
    Frozen runs write to %APPDATA%/GreyUtopia (or ~/.greyutopia elsewhere),
    since the extraction/install directory is not a safe place to persist data.
    """
    if not is_frozen():
        return app_root()
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "GreyUtopia")
    os.makedirs(path, exist_ok=True)
    return path
