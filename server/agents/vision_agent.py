"""Vision Agent - OCR + object detection + screen context."""

from __future__ import annotations

from typing import Any, Dict

from .base_agent import BaseAgent, Task, AgentResponse
from server.services.context.context_store import ContextStore
from server.services.vision.pipeline import VisionPipeline


class VisionAgent(BaseAgent):
    def __init__(self, agent_id: str = "vision_agent_v1"):
        super().__init__(
            agent_id=agent_id,
            name="Vision Agent",
            description="Analyzes images/screen captures using OCR and object detection."
        )
        self.pipeline = VisionPipeline()

    def can_handle_task(self, task: Task) -> bool:
        query = str(task.metadata.get("query", "")).lower()
        keywords = ["vision", "image", "screenshot", "ocr", "screen", "detect", "read text"]
        return any(k in query for k in keywords)

    async def process_task(self, task: Task) -> AgentResponse:
        session_id = task.metadata.get("session_id")
        image_bytes = ContextStore.get_latest_image(session_id) if session_id else None
        if not image_bytes:
            return AgentResponse(
                agent_id=self.agent_id,
                success=False,
                error="No image context available for this session."
            )
        try:
            result = await self.pipeline.analyze(image_bytes)
            return AgentResponse(agent_id=self.agent_id, success=True, result=result)
        except Exception as exc:
            return AgentResponse(agent_id=self.agent_id, success=False, error=str(exc))
