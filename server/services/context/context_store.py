"""Session-scoped context store for multimodal artifacts (images, screen data)."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional


class ContextStore:
    """Lightweight in-memory store keyed by session_id."""

    _lock = threading.Lock()
    _sessions: Dict[str, Dict[str, Any]] = {}
    _max_image_bytes: int = 8 * 1024 * 1024  # 8 MB guardrail
    _ttl_seconds: int = 15 * 60  # 15 minutes

    @classmethod
    def set_image(cls, session_id: str, image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not session_id or not image_bytes:
            return False
        if len(image_bytes) > cls._max_image_bytes:
            return False
        payload = {
            "image_bytes": image_bytes,
            "metadata": metadata or {},
            "updated_at": time.time(),
        }
        with cls._lock:
            cls._sessions.setdefault(session_id, {})["image"] = payload
        return True

    @classmethod
    def get_latest_image(cls, session_id: str) -> Optional[bytes]:
        payload = cls.get_latest_payload(session_id).get("image")
        if not payload:
            return None
        return payload.get("image_bytes")

    @classmethod
    def set_screen_text(cls, session_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        if not session_id or not text:
            return False
        payload = {
            "text": text,
            "metadata": metadata or {},
            "updated_at": time.time(),
        }
        with cls._lock:
            cls._sessions.setdefault(session_id, {})["screen_text"] = payload
        return True

    @classmethod
    def get_screen_text(cls, session_id: str) -> Optional[str]:
        payload = cls.get_latest_payload(session_id).get("screen_text")
        if not payload:
            return None
        return payload.get("text")

    @classmethod
    def get_latest_payload(cls, session_id: str) -> Dict[str, Any]:
        with cls._lock:
            session_data = cls._sessions.get(session_id, {})
            cls._evict_expired_locked(session_data)
            return dict(session_data)

    @classmethod
    def evict(cls, session_id: str) -> None:
        with cls._lock:
            cls._sessions.pop(session_id, None)

    @classmethod
    def _evict_expired_locked(cls, session_data: Dict[str, Any]) -> None:
        now = time.time()
        keys_to_delete = []
        for key, payload in session_data.items():
            updated_at = payload.get("updated_at", 0)
            if now - updated_at > cls._ttl_seconds:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            session_data.pop(key, None)
