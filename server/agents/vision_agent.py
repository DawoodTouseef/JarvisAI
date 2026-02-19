"""Vision Agent - OCR + object detection + screen context."""

from __future__ import annotations

from typing import Any, Dict
import logging

from .base_agent import BaseAgent, Task, AgentResponse
from server.services.context.context_store import ContextStore
from server.services.vision.pipeline import VisionPipeline
from server.services.vision.types import VisionInput, VisionConfig


class VisionAgent(BaseAgent):
    def __init__(self, agent_id: str = "vision_agent_v1"):
        super().__init__(
            agent_id=agent_id,
            name="Vision Agent",
            description="Analyzes images/screen captures using OCR and object detection."
        )
        self.pipeline = VisionPipeline()
        self.logger = logging.getLogger(__name__)

    def can_handle_task(self, task: Task) -> bool:
        query = str(task.metadata.get("query", "")).lower()
        keywords = ["vision", "image", "screenshot", "ocr", "screen", "detect", "read text"]
        return any(k in query for k in keywords)

    async def process_task(self, task: Task) -> AgentResponse:
        task_id = task.metadata.get("parent_task_id") or task.id
        await self.emit_event("active_agent", task_id, {"agent": self.name})
        await self.emit_event("agent_state", task_id, {"state": "executing", "agent": self.name})
        await self.emit_event("agent_activity", task_id, {"agent": self.name, "message": "Analyzing screen"})
        session_id = ContextStore.get_session_for_task(task_id)
        screenshot_image = ContextStore.get_screenshot_image(session_id) if session_id else None
        if not screenshot_image:
            await self.emit_event("error_event", task_id, {
                "source": "vision",
                "agent": self.name,
                "message": "No screenshot context available for this session."
            })
            return AgentResponse(
                agent_id=self.agent_id,
                success=False,
                error="No screenshot context available for this session."
            )
        camera_enabled = ContextStore.get_camera_enabled(session_id) if session_id else False
        camera_image = ContextStore.get_camera_image(session_id) if (session_id and camera_enabled) else None
        payload = ContextStore.get_latest_payload(session_id) if session_id else {}
        vision_input = VisionInput(
            screenshot_image=screenshot_image,
            camera_image=camera_image if camera_enabled else None,
            metadata={
                "timestamp": payload.get("screenshot_image", {}).get("metadata", {}).get("timestamp"),
                "active_agents": [],
                "user_context": payload.get("screen_text", {}).get("text") if payload.get("screen_text") else None,
            },
        )
        vision_config = VisionConfig(camera_enabled=camera_enabled)
        try:
            self.logger.info("VisionAgent: processing vision inputs (camera_enabled=%s)", camera_enabled)
            result = await self.pipeline.analyze_inputs(
                screenshot_image=vision_input.screenshot_image,
                camera_image=vision_input.camera_image,
                camera_enabled=vision_config.camera_enabled,
            )
            result["metadata"] = vision_input.metadata
            await self.emit_event("agent_activity", task_id, {"agent": self.name, "message": "Vision analysis complete"})
            return AgentResponse(agent_id=self.agent_id, success=True, result=result)
        except Exception as exc:
            self.logger.exception("VisionAgent: vision processing failed")
            await self.emit_event("error_event", task_id, {
                "source": "vision",
                "agent": self.name,
                "message": str(exc)
            })
            return AgentResponse(agent_id=self.agent_id, success=False, error=str(exc))
