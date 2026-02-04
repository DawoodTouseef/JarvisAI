"""Vision interface contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VisionInput:
    screenshot_image: bytes
    camera_image: Optional[bytes]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisionConfig:
    camera_enabled: bool
    vision_models: List[str] = field(default_factory=lambda: ["ocr", "detection", "multimodal"])
