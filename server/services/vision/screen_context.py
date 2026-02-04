"""Heuristics for turning OCR + detections into UI context."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def infer_ui_context(ocr_text: str, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    buttons = [line for line in lines if re.fullmatch(r"[A-Z0-9 _-]{2,20}", line)]
    warnings = [line for line in lines if "error" in line.lower() or "warning" in line.lower()]
    urls = [line for line in lines if "http://" in line.lower() or "https://" in line.lower()]
    objects = [d.get("class_name") for d in detections if d.get("class_name")]
    objects = list(dict.fromkeys(objects))

    return {
        "buttons": buttons[:10],
        "warnings": warnings[:10],
        "urls": urls[:10],
        "objects": objects[:15],
    }
