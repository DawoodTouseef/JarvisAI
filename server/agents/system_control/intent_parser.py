import json
import inspect
import re
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
        file_path = self._extract_path(query)
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
        if "open file" in lowered and file_path:
            return [
                ActionIntent(
                    tool_name="open_file",
                    parameters={"path": file_path},
                    reasoning="User requested to open a file",
                    permission_level=PermissionLevel.SAFE
                )
            ]
        if ("open folder" in lowered or "open directory" in lowered) and file_path:
            return [
                ActionIntent(
                    tool_name="open_folder",
                    parameters={"path": file_path},
                    reasoning="User requested to open a folder",
                    permission_level=PermissionLevel.SAFE
                )
            ]
        if ("read file" in lowered or "read the file" in lowered) and file_path:
            return [
                ActionIntent(
                    tool_name="read_file",
                    parameters={"path": file_path},
                    reasoning="User requested to read a file",
                    permission_level=PermissionLevel.SAFE
                )
            ]
        if any(k in lowered for k in ["open app", "open application", "launch app", "launch application", "open "]):
            app_name = self._extract_after_keyword(query, ["open", "launch"])
            if app_name:
                return [
                    ActionIntent(
                        tool_name="open_application",
                        parameters={"app_name": app_name},
                        reasoning="User requested to open an application",
                        permission_level=PermissionLevel.SAFE
                    )
                ]
        if any(k in lowered for k in ["close app", "close application", "quit app", "quit application", "close "]):
            app_name = self._extract_after_keyword(query, ["close", "quit"])
            if app_name:
                return [
                    ActionIntent(
                        tool_name="close_application",
                        parameters={"app_name": app_name},
                        reasoning="User requested to close an application",
                        permission_level=PermissionLevel.SAFE
                    )
                ]
        if "focus" in lowered:
            app_name = self._extract_after_keyword(query, ["focus"])
            if app_name:
                return [
                    ActionIntent(
                        tool_name="focus_window",
                        parameters={"app_name": app_name},
                        reasoning="User requested to focus a window",
                        permission_level=PermissionLevel.SAFE
                    )
                ]
        if "type " in lowered:
            text = self._extract_after_keyword(query, ["type", "enter"])
            if text:
                return [
                    ActionIntent(
                        tool_name="type_text",
                        parameters={"text": text},
                        reasoning="User requested to type text",
                        permission_level=PermissionLevel.SAFE
                    )
                ]
        if "press" in lowered:
            key = self._extract_after_keyword(query, ["press"])
            if key:
                return [
                    ActionIntent(
                        tool_name="press_key",
                        parameters={"key": key},
                        reasoning="User requested to press a key",
                        permission_level=PermissionLevel.SAFE
                    )
                ]
        if "scroll" in lowered:
            clicks = 5
            if "down" in lowered:
                clicks = -5
            amount = self._extract_int(lowered)
            if amount is not None:
                clicks = -abs(amount) if "down" in lowered else abs(amount)
            return [
                ActionIntent(
                    tool_name="scroll",
                    parameters={"clicks": clicks},
                    reasoning="User requested to scroll",
                    permission_level=PermissionLevel.SAFE
                )
            ]
        if "move mouse" in lowered or "move cursor" in lowered:
            coords = self._extract_coords(lowered)
            if coords and len(coords) >= 2:
                return [
                    ActionIntent(
                        tool_name="move_mouse",
                        parameters={"x": coords[0], "y": coords[1]},
                        reasoning="User requested to move the mouse",
                        permission_level=PermissionLevel.SAFE
                    )
                ]
        if "click" in lowered:
            coords = self._extract_coords(lowered)
            if coords and len(coords) >= 2:
                return [
                    ActionIntent(
                        tool_name="click",
                        parameters={"x": coords[0], "y": coords[1]},
                        reasoning="User requested a mouse click",
                        permission_level=PermissionLevel.SAFE
                    )
                ]
        if "drag" in lowered:
            coords = self._extract_coords(lowered)
            if coords and len(coords) >= 4:
                return [
                    ActionIntent(
                        tool_name="drag_mouse",
                        parameters={"start_x": coords[0], "start_y": coords[1], "end_x": coords[2], "end_y": coords[3]},
                        reasoning="User requested a mouse drag",
                        permission_level=PermissionLevel.SAFE
                    )
                ]
        
        if "time" in lowered:
            return [
                ActionIntent(
                    tool_name="get_system_time",
                    parameters={},
                    reasoning="User requested local time",
                    permission_level=PermissionLevel.SAFE
                )
            ]

        if "date" in lowered or "today" in lowered:
            return [
                ActionIntent(
                    tool_name="get_system_date",
                    parameters={},
                    reasoning="User requested local date",
                    permission_level=PermissionLevel.SAFE
                )
            ]

        if "os" in lowered or "operating system" in lowered or "platform" in lowered:
            return [
                ActionIntent(
                    tool_name="get_os_info",
                    parameters={},
                    reasoning="User requested OS info",
                    permission_level=PermissionLevel.SAFE
                )
            ]
        if "system info" in lowered or "system information" in lowered or "hardware" in lowered:
            return [
                ActionIntent(
                    tool_name="get_system_info",
                    parameters={},
                    reasoning="User requested system info",
                    permission_level=PermissionLevel.SAFE
                )
            ]
        return []

    async def _parse_with_llm(self, query: str) -> List[ActionIntent]:
        tools = self._describe_tools()
        tool_names = [tool["name"] for tool in tools]
        tool_descriptions = [name for name in _TOOL_DESCRIPTIONS]
        tools_ = "\n".join([f"-{i}:{j}" for i, j in zip(tool_names, tool_descriptions)])
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

    def _extract_path(self, text: str) -> str:
        windows_match = re.search(r"([A-Za-z]:\\[^\"'\s]+)", text)
        if windows_match:
            return windows_match.group(1)
        unix_match = re.search(r"(/[^\"'\s]+)", text)
        if unix_match:
            return unix_match.group(1)
        return ""

    def _extract_after_keyword(self, text: str, keywords: List[str]) -> str:
        lowered = text.lower()
        for kw in keywords:
            if kw in lowered:
                idx = lowered.find(kw) + len(kw)
                remainder = text[idx:].strip(" :,-")
                return remainder.strip()
        return ""

    def _extract_coords(self, text: str) -> List[int]:
        numbers = re.findall(r"(-?\d+)", text)
        return [int(n) for n in numbers]

    def _extract_int(self, text: str) -> Any:
        match = re.search(r"(-?\d+)", text)
        return int(match.group(1)) if match else None

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
