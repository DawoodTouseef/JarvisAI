"""Knowledge Agent - fallback factual retrieval."""

from __future__ import annotations

from typing import Any, Dict

from .base_agent import BaseAgent, Task, AgentResponse
from .tools.tool_system import registry as tool_registry


class KnowledgeAgent(BaseAgent):
    def __init__(self, agent_id: str = "knowledge_agent_v1"):
        super().__init__(
            agent_id=agent_id,
            name="Knowledge Agent",
            description="Retrieves factual information from internal knowledge or web search."
        )

    def can_handle_task(self, task: Task) -> bool:
        query = str(task.metadata.get("query", "")).lower()
        keywords = ["lookup", "fact", "define", "what is", "who is", "explain", "knowledge"]
        return any(k in query for k in keywords)

    async def process_task(self, task: Task) -> AgentResponse:
        query = task.metadata.get("query", "")
        if not query:
            await self.emit_event("error_event", task.metadata.get("parent_task_id") or task.id, {
                "source": "knowledge",
                "agent": self.name,
                "message": "No query provided."
            })
            return AgentResponse(agent_id=self.agent_id, success=False, error="No query provided.")

        try:
            task_id = task.metadata.get("parent_task_id") or task.id
            # Prefer internal knowledge lookup when available.
            kb_tool = tool_registry.get_tool("knowledge_lookup")
            if kb_tool:
                kb_result = await kb_tool.run(query=query)
                return AgentResponse(agent_id=self.agent_id, success=True, result={"source": "knowledge_base", "data": kb_result})

            # Fallback to web search tool if present.
            web_tool = tool_registry.get_tool("web_search")
            if web_tool:
                web_result = await web_tool.run(query=query)
                return AgentResponse(agent_id=self.agent_id, success=True, result={"source": "web_search", "data": web_result})

            await self.emit_event("error_event", task_id, {
                "source": "knowledge",
                "agent": self.name,
                "message": "No knowledge tools available."
            })
            return AgentResponse(agent_id=self.agent_id, success=False, error="No knowledge tools available.")
        except Exception as exc:
            await self.emit_event("error_event", task.metadata.get("parent_task_id") or task.id, {
                "source": "knowledge",
                "agent": self.name,
                "message": str(exc)
            })
            return AgentResponse(agent_id=self.agent_id, success=False, error=str(exc))
