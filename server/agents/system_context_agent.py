"""System Context Agent - OS snapshot and environment awareness."""

from __future__ import annotations

from .base_agent import BaseAgent, Task, AgentResponse
from server.services.context.system_context import get_snapshot


class SystemContextAgent(BaseAgent):
    def __init__(self, agent_id: str = "system_context_agent_v1"):
        super().__init__(
            agent_id=agent_id,
            name="System Context Agent",
            description="Provides system state (CPU, memory, uptime, platform)."
        )

    def can_handle_task(self, task: Task) -> bool:
        query = str(task.metadata.get("query", "")).lower()
        keywords = ["system", "cpu", "memory", "ram", "uptime", "context", "environment", "os state"]
        return any(k in query for k in keywords)

    async def process_task(self, task: Task) -> AgentResponse:
        try:
            snapshot = get_snapshot()
            return AgentResponse(agent_id=self.agent_id, success=True, result=snapshot)
        except Exception as exc:
            return AgentResponse(agent_id=self.agent_id, success=False, error=str(exc))
