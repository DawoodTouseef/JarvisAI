from typing import Dict, Callable

_TOOL_REGISTRY: Dict[str, Callable] = {}

def register_tool(name: str):
    """Decorator to register a tool function."""
    def decorator(func: Callable):
        _TOOL_REGISTRY[name] = func
        return func
    return decorator

def get_tool(name: str) -> Callable:
    """Retrieve a tool function by name."""
    if name not in _TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' not found in registry")
    return _TOOL_REGISTRY[name]
