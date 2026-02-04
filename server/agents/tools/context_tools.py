"""Tools for retrieving system and session context."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .tool_system import BaseTool
from server.services.context.system_context import get_snapshot
from server.services.context.context_store import ContextStore


class SystemContextSchema(BaseModel):
    detail: str = Field("basic", description="Context detail level: basic|full")


class SystemContextTool(BaseTool):
    name: str = "system_context"
    description: str = "Get system state snapshot (CPU, memory, uptime, platform)."
    args_schema = SystemContextSchema

    async def run(self, detail: str = "basic"):
        snapshot = get_snapshot()
        if detail == "basic":
            return {
                "cpu_percent": snapshot.get("cpu_percent"),
                "memory_percent": snapshot.get("memory_percent"),
                "uptime_seconds": snapshot.get("uptime_seconds"),
            }
        return snapshot


class SessionContextSchema(BaseModel):
    session_id: str = Field(..., description="Session id to retrieve stored context")


class SessionContextTool(BaseTool):
    name: str = "session_context"
    description: str = "Get latest session context metadata (image, timestamps)."
    args_schema = SessionContextSchema

    async def run(self, session_id: str):
        payload = ContextStore.get_latest_payload(session_id)
        if not payload:
            return {"error": "No context found for this session."}
        # Do not return raw bytes
        image_meta = payload.get("image", {}).get("metadata", {}) if payload.get("image") else {}
        screen_text = payload.get("screen_text", {}).get("text") if payload.get("screen_text") else None
        return {"image_metadata": image_meta, "screen_text": screen_text}
