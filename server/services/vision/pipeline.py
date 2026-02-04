"""Vision pipeline orchestrating OCR + object detection."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from .ocr_glm import GlmOcrClient
from .detector_yolo import YoloDetector
from .screen_context import infer_ui_context


class VisionPipeline:
    def __init__(self, ocr_client: Optional[GlmOcrClient] = None, detector: Optional[YoloDetector] = None):
        self.ocr_client = ocr_client or GlmOcrClient()
        self.detector = detector or YoloDetector()

    async def analyze(self, image_bytes: bytes) -> Dict[str, Any]:
        ocr_task = asyncio.wait_for(asyncio.to_thread(self._run_ocr, image_bytes), timeout=25)
        det_task = asyncio.wait_for(asyncio.to_thread(self._run_detection, image_bytes), timeout=25)

        ocr_result, det_result = await asyncio.gather(ocr_task, det_task, return_exceptions=True)

        ocr_payload = self._normalize_ocr(ocr_result)
        det_payload = self._normalize_det(det_result)

        ui_context = infer_ui_context(ocr_payload["text"], det_payload["objects"])

        return {
            "ocr": ocr_payload,
            "objects": det_payload["objects"],
            "ui_context": ui_context,
            "errors": {
                "ocr": ocr_payload.get("error"),
                "detection": det_payload.get("error"),
            },
        }

    def _run_ocr(self, image_bytes: bytes) -> Dict[str, Any]:
        return self.ocr_client.extract_text(image_bytes)

    def _run_detection(self, image_bytes: bytes):
        return self.detector.detect(image_bytes)

    def _normalize_ocr(self, result: Any) -> Dict[str, Any]:
        if isinstance(result, Exception):
            return {"text": "", "blocks": [], "error": str(result)}
        if isinstance(result, dict):
            text = result.get("text") or result.get("content") or ""
            blocks = result.get("blocks") or result.get("lines") or []
            return {"text": text, "blocks": blocks, "raw": result}
        return {"text": str(result), "blocks": []}

    def _normalize_det(self, result: Any) -> Dict[str, Any]:
        if isinstance(result, Exception):
            return {"objects": [], "error": str(result)}
        if isinstance(result, list):
            return {"objects": result}
        return {"objects": []}
