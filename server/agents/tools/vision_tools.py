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
        image_bytes = ContextStore.get_latest_image(session_id)
        if not image_bytes:
            return {"error": "No image context available for this session."}
        pipeline = VisionPipeline()
        return await pipeline.analyze(image_bytes)
