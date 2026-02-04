import json
import inspect
from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from .schemas import ActionIntent, PermissionLevel
from .safety_validator import SafetyValidator
from . import tools  # ensure tool registration
from .tools.registry import _TOOL_REGISTRY, _TOOL_DESCRIPTIONS

class IntentParser:
    """Parses natural language commands into structured ActionIntents."""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.safety_validator = SafetyValidator()

    async def parse(self, query: str) -> List[ActionIntent]:
        """
        In a real implementation, this would call an LLM to parse the query.
        For now, we'll implement a Mock/Simplified version or assume the prompt
        is engineered to return structured JSON.
        """
        if not query or not query.strip():
            return []

        if self.llm_client:
            parsed = await self._parse_with_llm(query)
            if parsed:
                return parsed
    
        lowered = query.lower().strip()
        if lowered.startswith("run "):
            command = query.strip()[4:]
            return [
                ActionIntent(
                    tool_name="run_shell",
                    parameters={"command": command},
                    reasoning="User requested a shell command",
                    permission_level=PermissionLevel.CONFIRM
                )
            ]

        if lowered.startswith("execute "):
            command = query.strip()[8:]
            return [
                ActionIntent(
                    tool_name="run_shell",
                    parameters={"command": command},
                    reasoning="User requested a shell command",
                    permission_level=PermissionLevel.CONFIRM
                )
            ]
        

    async def _parse_with_llm(self, query: str) -> List[ActionIntent]:
        tools = self._describe_tools()
        tool_names = [tool["name"] for tool in tools]
        tool_description = [tool['name'] for tool in _TOOL_DESCRIPTIONS]
        tools_= "\n".join([f"-{i}:{j}" for i,j in zip(tool_name,tool_description)])
        system_prompt = (
            "You are a system-control intent parser. "
            "Return ONLY valid JSON with a list of steps. "
            "Each step must select a tool from the allowed list and include parameters."
        )

        user_prompt = f"""
Allowed tools (name and parameters):
{json.dumps(tools, indent=2)}

Available tools:
{tools_}
User request:
{query}

Output JSON format:
[
  {{
    "tool_name": "tool",
    "parameters": {{"key": "value"}},
    "reasoning": "short explanation"
  }}
]

Rules:
- Use only tools from the allowed list.
- For shell or script execution, use tool_name "run_shell".
- Do not include extra keys.
"""

        try:
            response = await self.llm_client.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            text = response.content if hasattr(response, "content") else str(response)
            data = json.loads(self._extract_json(text))

            intents: List[ActionIntent] = []
            for item in data:
                tool_name = item.get("tool_name")
                if tool_name not in tool_names:
                    continue
                parameters = item.get("parameters", {})
                reasoning = item.get("reasoning", "")
                permission = self._determine_permission(tool_name, parameters)
                intents.append(ActionIntent(
                    tool_name=tool_name,
                    parameters=parameters,
                    reasoning=reasoning,
                    permission_level=permission
                ))
            return intents
        except Exception:
            return []

    def _extract_json(self, text: str) -> str:
        """Best-effort JSON extraction."""
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]
        return text

    def _describe_tools(self) -> List[Dict[str, Any]]:
        tools = []
        for name, func in _TOOL_REGISTRY.items():
            params = []
            try:
                signature = inspect.signature(func)
                for param_name in signature.parameters:
                    if param_name in {"event_callback", "cancel_event"}:
                        continue
                    params.append(param_name)
            except (TypeError, ValueError):
                params = []
            tools.append({
                "name": name,
                "description": _TOOL_DESCRIPTIONS.get(name, ""),
                "parameters": params,
            })
        return tools

    def _determine_permission(self, tool_name: str, parameters: Dict[str, Any]) -> PermissionLevel:
        return self.safety_validator.validate_action(tool_name, parameters)
