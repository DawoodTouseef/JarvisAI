from typing import Dict, Callable, Optional

_TOOL_REGISTRY: Dict[str, Callable] = {}
_TOOL_DESCRIPTIONS: Dict[str, str] = {}

def register_tool(name: str, description: Optional[str] = None):
    """Decorator to register a tool function."""
    def decorator(func: Callable):
        _TOOL_REGISTRY[name] = func
        if description:
            _TOOL_DESCRIPTIONS[name] = description
        return func
    return decorator

def get_tool(name: str) -> Callable:
    """Retrieve a tool function by name."""
    if name not in _TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' not found in registry")
    return _TOOL_REGISTRY[name]

def get_description(name:str)->str:
    if name not in _TOOL_DESCRIPTIONS:
        raise ValueError(f"Tool '{name}' not found in registry")
    return _TOOL_DESCRIPTIONS[name]
