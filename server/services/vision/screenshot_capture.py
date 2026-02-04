"""Backend screenshot capture for always-on screen vision."""

from __future__ import annotations

from io import BytesIO
from typing import Optional


def capture_screenshot_bytes() -> Optional[bytes]:
    try:
        import mss
        import mss.tools
    except Exception:
        return None

    with mss.mss() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        shot = sct.grab(monitor)
        png = mss.tools.to_png(shot.rgb, shot.size)
        return png
