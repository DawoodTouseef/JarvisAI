import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from .schemas import AgentState, ActionIntent, PermissionLevel, AgentEvent
from .intent_parser import IntentParser
from .safety_validator import SafetyValidator
from .execution_engine import ExecutionEngine

class SystemControlAgent:
    """Manages the lifecycle and execution of system control commands."""

    def __init__(self, llm_client=None, event_callback: Optional[Callable] = None):
        self.state = AgentState.IDLE
        self.intent_parser = IntentParser(llm_client)
        self.safety_validator = SafetyValidator()
        self.execution_engine = ExecutionEngine()
        self.event_callback = event_callback
        self.current_plan: List[ActionIntent] = []
        self._is_cancelled = False

    def emit_event(self, event):
        """Helper to emit events through callback."""
        if self.event_callback:
            self.event_callback(event)

    async def handle_command(
        self,
        query: str,
        permission_callback: Optional[Callable] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Entry point for natural language command processing."""
        self._is_cancelled = False

        # 1. Parsing Phase
        self.state = AgentState.PLANNING
        try:
            self.current_plan = await self.intent_parser.parse(query)
            if not self.current_plan:
                self.state = AgentState.FAILED
                return {"success": False, "error": "Could not understand command"}

            # 2. Safety & Execution Phase
            results = []
            for step in self.current_plan:
                # Validate safety
                permission = self.safety_validator.validate_action(step.tool_name, step.parameters)
                risk_level = self.safety_validator.assess_risk(step.tool_name, step.parameters)

                if permission == PermissionLevel.BLOCKED:
                    self.state = AgentState.FAILED
                    return {"success": False, "text": f"Action {step.tool_name} is BLOCKED"}

                if permission == PermissionLevel.CONFIRM:
                    self.state = AgentState.WAITING_CONFIRMATION
                    self.emit_event(AgentEvent(event_type="confirmation_requested", payload={"step": step.model_dump(),  "risk_level": risk_level},task_id=task_id))
                    if permission_callback:
                        approved = await permission_callback(
                            f"{step.tool_name}({step.parameters})",
                            step.tool_name,
                            risk_level
                        )
                        if not approved:
                            self.state = AgentState.CANCELLED
                            return {"success": False, "error": "Permission denied", "status": "CANCELLED"}
                    

                # Execute step
                self.state = AgentState.EXECUTING
                # Dynamically get tool function (to be implemented in tools layer)
                tool_func = self._get_tool_func(step.tool_name)
                result = await self.execution_engine.execute_action(step, tool_func, self.emit_event)
                results.append(result)

            self.state = AgentState.COMPLETED
            return {"success": True, "results": results}

        except Exception as e:
            self.state = AgentState.FAILED
            return {"success": False, "error": str(e)}


    def _get_tool_func(self, tool_name: str) -> Callable:
        """Resolves tool name to function."""
        # This will be linked to the tools implemented in the next step
        from . import tools  # ensure tool registration
        from .tools.registry import get_tool
        return get_tool(tool_name)
