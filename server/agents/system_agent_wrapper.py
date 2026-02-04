"""System Agent Wrapper - Integrates the SystemControlAgent into the JARVIS orchestration system"""

import asyncio
from typing import Dict, Any, Optional, Callable
from .base_agent import BaseAgent, AgentResponse, Task

from .system_control.agent  import SystemControlAgent

class SystemAgentWrapper(BaseAgent):
    """Wrapper for the safe, non-blocking SystemControlAgent with OS control capabilities"""
    
    def __init__(self, agent_id: str = "system_control_agent_v1"):
        super().__init__(
            agent_id=agent_id,
            name="System Control Agent",
            description="Safe OS control, file management, and system task automation"
        )
        self._event_callback:Optional[Callable] = None
        self.system_agent = SystemControlAgent(event_callback=self._handle_orchestrator_event)
    def set_event_callback(self,event_callback:Optional[Callable]):
        self._event_callback = event_callback
    def _handle_orchestrator_event(self, event_type: str, task_id: str, payload: Dict[str, Any]):
        """Emit system agent events to the orchestration system for observability."""
        if not self._event_callback:
            return None
        result = self._event_callback(event_type, task_id, payload)
        return result

    def can_handle_task(self, task) -> bool:
        task_str = str(task).lower()
        return any(x in task_str for x in ["system", "os", "computer", "control"])

    async def process_task(self, task: Task) -> AgentResponse:
        """Process OS-level and system tasks using the safe Control Agent"""
        
        try:
            # Extract query string if input is a Task object
            input_query = task.metadata.get("query")
            task_id = task.metadata.get("parent_task_id") or task.id
            self.system_agent.intent_parser.llm_client=self.get_llm(task)
            # Process the command thru the system agent
            result = await self.system_agent.handle_command(
                task_id=task_id,
                query=input_query,
                permission_callback=self._handle_orchestrator_event,
                )
            
            if not result.get("success"):
                return AgentResponse(
                    agent_id=self.agent_id,
                    success=False,
                    error=result.get("error")
                )

            return AgentResponse(
                agent_id=self.agent_id,
                success=True,
                result=result.get("results")
            )
        except Exception as e:
            return AgentResponse(
                agent_id=self.agent_id,
                success=False,
                error=f"System control task failed: {str(e)}"
            )

    async def interrupt_task(self, task_id: str):
        """Handle immediate interruption request"""
        await self.system_agent.interrupt_task(task_id)

    async def cleanup(self):
        """Cleanup resources"""
        await self.system_agent.cleanup()
