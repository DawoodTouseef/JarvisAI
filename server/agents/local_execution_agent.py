"""Local Execution Chatbot Agent - orchestrator-driven code execution with safety gates."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from .base_agent import BaseAgent, Task, AgentResponse, AgentStatus
from .local_execution.execution_engine import ExecutionEngine, CancellationToken, ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlan:
    action: str
    code: str
    needs_privilege: bool
    permission_reason: str
    risk_level: str
    response: str


class LocalExecutionChatbotAgent(BaseAgent):
    """Agent that plans and runs local code safely with permission gating."""

    def __init__(self, agent_id: str = "local_execution_agent_v1"):
        super().__init__(
            agent_id=agent_id,
            name="Local Execution Chatbot Agent",
            description="Write and run local code safely (Python/JS/Shell) with permission-gated privileges."
        )
        self._event_callback: Optional[Callable] = None
        self._execution_engine = ExecutionEngine()
        self._cancel_tokens: Dict[str, CancellationToken] = {}

    def set_event_callback(self, event_callback: Optional[Callable]) -> None:
        self._event_callback = event_callback
        self._execution_engine.set_event_callback(event_callback)

    def can_handle_task(self, task: Task) -> bool:
        task_str = str(task).lower()
        keywords = [
            "run", "execute", "script", "python", "javascript", "node",
            "shell", "terminal", "command", "install", "package",
            "csv", "code", "program", "open", "launch", "app"
        ]
        return any(k in task_str for k in keywords)

    async def process_task(self, task: Task) -> AgentResponse:
        self.status = AgentStatus.RUNNING
        task_id = task.metadata.get("parent_task_id") or task.id
        query = task.metadata.get("query", "")
        permission_callback = task.metadata.get("permission_callback")

        plan = await self._create_plan(task, query)
        if plan.action == "reasoning":
            self.status = AgentStatus.COMPLETED
            return AgentResponse(agent_id=self.agent_id, success=True, result=plan.response)

        token = CancellationToken()
        self._cancel_tokens[task_id] = token

        try:
            if plan.needs_privilege:
                summary = f"{plan.action} execution"
                if plan.permission_reason:
                    summary = f"{summary} - {plan.permission_reason}"
                approved = await self._request_permission(
                    permission_callback,
                    summary,
                    plan.code,
                    plan.risk_level,
                )
                if not approved:
                    self.status = AgentStatus.CANCELLED
                    return AgentResponse(agent_id=self.agent_id, success=False, error="Permission denied.")

            try:
                result = await self._execute_plan(task_id, plan, token)
            except RuntimeError as exc:
                if plan.action == "javascript" and "sandbox runtime is unavailable" in str(exc).lower():
                    plan.needs_privilege = True
                    summary = "javascript execution - Sandbox runtime unavailable, need Node.js."
                    approved = await self._request_permission(
                        permission_callback,
                        summary,
                        plan.code,
                        "high",
                    )
                    if not approved:
                        self.status = AgentStatus.CANCELLED
                        return AgentResponse(agent_id=self.agent_id, success=False, error="Permission denied.")
                    result = await self._execute_plan(task_id, plan, token)
                else:
                    raise
            self.status = AgentStatus.COMPLETED
            return AgentResponse(agent_id=self.agent_id, success=True, result=self._format_result(plan, result))
        except Exception as exc:
            logger.exception("Local execution failed")
            self.status = AgentStatus.FAILED
            return AgentResponse(agent_id=self.agent_id, success=False, error=str(exc))
        finally:
            self._cancel_tokens.pop(task_id, None)

    async def interrupt_task(self, task_id: str):
        token = self._cancel_tokens.get(task_id)
        if token:
            token.cancel()

    def cancel_task(self):
        for token in self._cancel_tokens.values():
            token.cancel()

    async def _create_plan(self, task: Task, query: str) -> ExecutionPlan:
        time_response = self._try_time_response(query)
        if time_response:
            return time_response

        llm = self.get_llm(task)
        system_prompt = """
You are a Local Execution Chatbot Agent.
Decide whether to respond directly or to run code locally.

Return JSON ONLY with this schema:
{
  "action": "reasoning|python|javascript|shell|app",
  "code": "code or command",
  "needs_privilege": true|false,
  "permission_reason": "short reason",
  "risk_level": "low|medium|high",
  "response": "final response if action=reasoning"
}

Rules:
- Use reasoning for simple questions (e.g., time, explanations).
- Use python for data analysis or transformations.
- Use javascript for JS-specific tasks.
- Use shell for system commands.
- Use app for launching applications.
- For app action, code should be the application name only.
- Set needs_privilege=true for any file access, system commands, app launches, or network access.
- For package installs or network access, risk_level must be "high".
- When in doubt, set needs_privilege=true.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                plan_dict = json.loads(match.group(0))
                return self._normalize_plan(plan_dict, query)
        except Exception as exc:
            logger.warning("Plan generation failed: %s", exc)

        return self._fallback_plan(query)

    def _try_time_response(self, query: str) -> Optional[ExecutionPlan]:
        lowered = query.lower()
        if "time" in lowered and any(x in lowered for x in ["what", "current", "now"]):
            now = datetime.now()
            response = f"The current local time is {now.strftime('%I:%M %p')} on {now.strftime('%B %d, %Y')}."
            return ExecutionPlan(
                action="reasoning",
                code="",
                needs_privilege=False,
                permission_reason="",
                risk_level="low",
                response=response,
            )
        return None

    def _normalize_plan(self, plan_dict: Dict[str, Any], query: str) -> ExecutionPlan:
        action = str(plan_dict.get("action", "reasoning")).strip().lower()
        code = str(plan_dict.get("code", "")).strip()
        needs_privilege = bool(plan_dict.get("needs_privilege", False))
        permission_reason = str(plan_dict.get("permission_reason", "Needs elevated access.")).strip()
        risk_level = str(plan_dict.get("risk_level", "medium")).strip().lower()
        response = str(plan_dict.get("response", "")).strip()

        if action not in {"reasoning", "python", "javascript", "shell", "app"}:
            action = "reasoning"
        if action == "app":
            code = self._extract_app_name(code or query)
        if not code and action != "reasoning":
            return self._fallback_plan(query)

        inferred_privilege = self._detect_privilege_requirements(action, code, query)
        needs_privilege = needs_privilege or inferred_privilege["needs_privilege"]
        risk_level = inferred_privilege["risk_level"] if needs_privilege else risk_level
        permission_reason = inferred_privilege["reason"] if needs_privilege else permission_reason

        if action == "reasoning" and not response:
            response = "I can help with that, but I need more specifics to proceed."

        return ExecutionPlan(
            action=action,
            code=code,
            needs_privilege=needs_privilege,
            permission_reason=permission_reason,
            risk_level=risk_level,
            response=response,
        )

    def _extract_app_name(self, text: str) -> str:
        lowered = text.lower()
        match = re.search(r"(open|launch)\s+([a-z0-9 _-]+)", lowered)
        if match:
            return match.group(2).strip()
        return text.strip()

    def _fallback_plan(self, query: str) -> ExecutionPlan:
        lowered = query.lower()
        if "shell" in lowered or "terminal" in lowered or "command" in lowered:
            return ExecutionPlan(
                action="shell",
                code=query,
                needs_privilege=True,
                permission_reason="Shell execution requires system access.",
                risk_level="high",
                response="",
            )
        if "open" in lowered or "launch" in lowered or "app" in lowered:
            return ExecutionPlan(
                action="app",
                code=query,
                needs_privilege=True,
                permission_reason="Launching applications requires system access.",
                risk_level="medium",
                response="",
            )
        if "python" in lowered or "script" in lowered or "csv" in lowered:
            return ExecutionPlan(
                action="reasoning",
                code="",
                needs_privilege=False,
                permission_reason="",
                risk_level="low",
                response="I can run Python for this. Please provide the code or the data to analyze.",
            )
        return ExecutionPlan(
            action="reasoning",
            code="",
            needs_privilege=False,
            permission_reason="",
            risk_level="low",
            response="Can you clarify what you want to run or analyze?",
        )

    def _detect_privilege_requirements(self, action: str, code: str, query: str) -> Dict[str, str]:
        lowered = f"{code}\n{query}".lower()
        if action == "app":
            return {
                "needs_privilege": True,
                "risk_level": "medium",
                "reason": "Launching applications requires system access.",
            }
        if action == "shell":
            return {
                "needs_privilege": True,
                "risk_level": "high",
                "reason": "Shell execution requires system access.",
            }
        patterns = [
            "open(",
            "write(",
            "delete",
            "remove(",
            "os.",
            "pathlib",
            "subprocess",
            "requests",
            "http",
            "pip install",
            "npm install",
            "curl",
            "wget",
        ]
        if any(p in lowered for p in patterns):
            return {
                "needs_privilege": True,
                "risk_level": "high",
                "reason": "Detected file system or network access in code.",
            }
        if ".csv" in lowered or "file" in lowered:
            return {
                "needs_privilege": True,
                "risk_level": "medium",
                "reason": "File access requires user permission.",
            }
        return {
            "needs_privilege": False,
            "risk_level": "low",
            "reason": "",
        }

    async def _request_permission(
        self,
        permission_callback: Optional[Callable],
        summary: str,
        exact_operation: str,
        risk_level: str,
    ) -> bool:
        if not permission_callback:
            raise RuntimeError("Permission callback is not available.")
        return await permission_callback(summary, exact_operation, risk_level)

    async def _execute_plan(self, task_id: str, plan: ExecutionPlan, token: CancellationToken) -> ExecutionResult:
        timeout = 120
        if plan.action == "python":
            if plan.needs_privilege:
                return await self._execution_engine.run_python_privileged(task_id, plan.code, timeout, token)
            return await self._execution_engine.run_python_sandbox(task_id, plan.code, timeout, token)
        if plan.action == "javascript":
            return await self._execution_engine.run_js(task_id, plan.code, not plan.needs_privilege, timeout, token)
        if plan.action == "shell":
            return await self._execution_engine.run_shell(task_id, plan.code, timeout, token)
        if plan.action == "app":
            return await self._execution_engine.run_app_open(task_id, plan.code, token)
        raise RuntimeError(f"Unsupported action type: {plan.action}")

    def _format_result(self, plan: ExecutionPlan, result: ExecutionResult) -> str:
        parts = []
        if result.stdout:
            parts.append(f"STDOUT:\n{result.stdout.strip()}")
        if result.stderr:
            parts.append(f"STDERR:\n{result.stderr.strip()}")
        if not parts:
            parts.append("Execution completed with no output.")
        return "\n\n".join(parts)
