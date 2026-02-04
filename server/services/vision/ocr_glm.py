"""GLM OCR integration."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict
import requests


class GlmOcrClient:
    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        self.endpoint = endpoint or os.getenv("GLM_OCR_URL")
        self.api_key = api_key or os.getenv("GLM_OCR_API_KEY")

    def _build_headers(self) -> Dict[str, str]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def extract_text(self, image_bytes: bytes) -> Dict[str, Any]:
        if not self.endpoint:
            raise RuntimeError("GLM_OCR_URL is not configured.")
        files = {"image": ("image.png", image_bytes, "application/octet-stream")}
        response = requests.post(self.endpoint, headers=self._build_headers(), files=files, timeout=30)
        response.raise_for_status()
        return response.json()

    def extract_text_base64(self, image_bytes: bytes) -> Dict[str, Any]:
        if not self.endpoint:
            raise RuntimeError("GLM_OCR_URL is not configured.")
        payload = {"image_base64": base64.b64encode(image_bytes).decode("utf-8")}
        response = requests.post(self.endpoint, headers=self._build_headers(), json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
