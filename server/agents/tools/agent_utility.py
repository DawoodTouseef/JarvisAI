"""Agent Utility Tool - Allows agents to communicate with Task Manager and the User"""

import asyncio
from typing import Dict, Any, Optional

class AgentUtilityTool:
    """Tool provided to agents for system interactions and conversational loops"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def request_clarification(self, task_id: str, question: str) -> str:
        """
        Pauses agent execution to ask the user a question via voice/WebSocket.
        Returns the user's spoken transcription as a string.
        """
        return await self.orchestrator.request_clarification(task_id, question)

    def stop_task(self, task_id: str) -> bool:
        """Stop a specific running task"""
        return self.orchestrator.task_manager.stop_task(task_id)

    def get_task_status(self, task_id: str) -> str:
        """Check the current status of a task"""
        task = self.orchestrator.task_manager.get_task(task_id)
        return task.status if task else "unknown"

    def send_direct_message(self, task_id: str, message: str):
        """Send a real-time message to the user's frontend without waiting for response"""
        self.orchestrator._emit_event("agent_direct_message", {
            "task_id": task_id,
            "message": message,
            "use_tts": True
        })
