"""System context snapshot provider."""

from __future__ import annotations

import platform
import time
from typing import Dict, Any

import psutil


def get_snapshot() -> Dict[str, Any]:
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent if hasattr(psutil, "disk_usage") else None,
        "uptime_seconds": time.time() - psutil.boot_time(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }
