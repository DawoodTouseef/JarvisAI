"""Tools for vision analysis used by GeneralPurposeAgent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .tool_system import BaseTool
from server.services.context.context_store import ContextStore
from server.services.vision.pipeline import VisionPipeline


class VisionAnalyzeSchema(BaseModel):
    session_id: str = Field(..., description="Session id for pulling the latest image context")


class VisionAnalyzeTool(BaseTool):
    name: str = "vision_analyze"
    description: str = "Run OCR + object detection on the latest screen/image for the session."
    args_schema = VisionAnalyzeSchema

    async def run(self, session_id: str):
        screenshot_image = ContextStore.get_screenshot_image(session_id)
        if not screenshot_image:
            return {"error": "No screenshot context available for this session."}
        camera_enabled = ContextStore.get_camera_enabled(session_id)
        camera_image = ContextStore.get_camera_image(session_id) if camera_enabled else None
        pipeline = VisionPipeline()
        return await pipeline.analyze_inputs(
            screenshot_image=screenshot_image,
            camera_image=camera_image,
            camera_enabled=camera_enabled,
        )


class VisionPerceptionSchema(BaseModel):
    session_id: str = Field(..., description="Session id for pulling the latest vision context")


class VisionPerceptionTool(BaseTool):
    name: str = "vision_perception"
    description: str = "Centralized vision perception (screen + optional camera)."
    args_schema = VisionPerceptionSchema

    async def run(self, session_id: str):
        tool = VisionAnalyzeTool()
        return await tool.run(session_id=session_id)
