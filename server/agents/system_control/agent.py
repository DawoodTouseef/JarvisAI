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
        self._current_task_id: Optional[str] = None

    def emit_event(self, event):
        """Helper to emit events through callback."""
        if not self.event_callback:
            return
        if isinstance(event, AgentEvent):
            if not getattr(event, "task_id", None):
                event.task_id = self._current_task_id  # type: ignore[attr-defined]
            result = self.event_callback(event)
        else:
            result = self.event_callback(event, None, None)
        if asyncio.iscoroutine(result):
            asyncio.create_task(result)

    def emit_event_payload(self, event_type: str, task_id: Optional[str], payload: Dict[str, Any]):
        if not self.event_callback:
            return
        result = self.event_callback(event_type, task_id, payload)
        if asyncio.iscoroutine(result):
            asyncio.create_task(result)

    async def handle_command(
        self,
        query: str,
        permission_callback: Optional[Callable] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Entry point for natural language command processing."""
        self._is_cancelled = False
        self._current_task_id = task_id

        # 1. Parsing Phase
        self.state = AgentState.PLANNING
        self.emit_event_payload("agent_activity", task_id, {"agent": "System Control Agent", "message": "Planning system actions"})
        try:
            self.current_plan = await self.intent_parser.parse(query)
            if not self.current_plan:
                self.state = AgentState.FAILED
                self.emit_event_payload("error_event", task_id, {
                    "source": "system_control",
                    "agent": "System Control Agent",
                    "message": "Could not understand command"
                })
                return {"success": False, "error": "Could not understand command"}

            # 2. Safety & Execution Phase
            results = []
            for step in self.current_plan:
                # Validate safety
                permission = self.safety_validator.validate_action(step.tool_name, step.parameters)
                risk_level = self.safety_validator.assess_risk(step.tool_name, step.parameters)

                if permission == PermissionLevel.BLOCKED:
                    self.state = AgentState.FAILED
                    self.emit_event_payload("error_event", task_id, {
                        "source": "system_control",
                        "agent": "System Control Agent",
                        "message": f"Action {step.tool_name} is blocked"
                    })
                    return {"success": False, "text": f"Action {step.tool_name} is BLOCKED"}

                if permission == PermissionLevel.CONFIRM:
                    self.state = AgentState.WAITING_CONFIRMATION
                    self.emit_event_payload("agent_state", task_id, {"state": "waiting_for_permission", "agent": "System Control Agent"})
                    self.emit_event(AgentEvent(event_type="confirmation_requested", payload={"step": step.model_dump(),  "risk_level": risk_level},task_id=task_id))
                    if permission_callback:
                        approved = await permission_callback(
                            f"{step.tool_name}({step.parameters})",
                            step.tool_name,
                            risk_level
                        )
                        if not approved:
                            self.state = AgentState.CANCELLED
                            self.emit_event_payload("error_event", task_id, {
                                "source": "system_control",
                                "agent": "System Control Agent",
                                "message": "Permission denied"
                            })
                            return {"success": False, "error": "Permission denied", "status": "CANCELLED"}
                    

                # Execute step
                self.state = AgentState.EXECUTING
                self.emit_event_payload("agent_state", task_id, {"state": "executing", "agent": "System Control Agent"})
                self.emit_event_payload("tool_called", task_id, {"agent": "System Control Agent", "tool": step.tool_name})
                self.emit_event_payload("agent_activity", task_id, {"agent": "System Control Agent", "message": f"Executing {step.tool_name}"})
                # Dynamically get tool function (to be implemented in tools layer)
                tool_func = self._get_tool_func(step.tool_name)
                result = await self.execution_engine.execute_action(step, tool_func, self.emit_event)
                success = bool(result.get("success", True)) and not result.get("error")
                if not success:
                    self.emit_event_payload("error_event", task_id, {
                        "source": "system_control",
                        "agent": "System Control Agent",
                        "message": result.get("error") or f"{step.tool_name} failed"
                    })
                results.append(result)
                self.emit_event_payload("tool_result", task_id, {"agent": "System Control Agent", "tool": step.tool_name, "success": success})

            self.state = AgentState.COMPLETED
            self.emit_event_payload("agent_state", task_id, {"state": "executing", "agent": "System Control Agent"})
            return {"success": True, "results": results}

        except Exception as e:
            self.state = AgentState.FAILED
            self.emit_event_payload("error_event", task_id, {
                "source": "system_control",
                "agent": "System Control Agent",
                "message": str(e)
            })
            return {"success": False, "error": str(e)}
        finally:
            self._current_task_id = None


    def _get_tool_func(self, tool_name: str) -> Callable:
        """Resolves tool name to function."""
        # This will be linked to the tools implemented in the next step
        from . import tools  # ensure tool registration
        from .tools.registry import get_tool
        return get_tool(tool_name)
