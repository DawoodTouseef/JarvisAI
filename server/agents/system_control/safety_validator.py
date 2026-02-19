from typing import Dict, Any, List
from .schemas import PermissionLevel

class SafetyValidator:
    """Multi-layer safety validator for system actions."""

    # Actions that are always safe (read-only)
    SAFE_ACTIONS = {
        "get_window_list",
        "get_active_window",
        "read_file",
        "get_system_info",
        "get_system_time",
        "get_system_date",
        "get_os_info",
        "get_volume",
        "get_brightness",
        "open_application",
        "close_application",
        "open_file",
        "open_folder",
        "focus_window",
        "move_mouse",
        "click",
        "scroll",
        "drag_mouse",
        "press_key",
        "type_text",
    }

    # Actions that require explicit confirmation
    CONFIRM_ACTIONS = {
        "run_shell",
        "write_file",
        "delete_file",
        "adjust_volume",
        "adjust_brightness",
    }

    # Forbidden actions
    BLOCKED_ACTIONS = {
        "shutdown",
        "restart",
        "format_drive",
        "delete_system_dir",
        "modify_registry",
        "install_package",
        "run_raw_shell"
    }

    # Blocked paths/patterns
    BLOCKED_PATHS = [
        "C:\\Windows",
        "/etc",
        "/bin",
        "/sbin",
        ".env"
    ]

    def validate_action(self, tool_name: str, parameters: Dict[str, Any]) -> PermissionLevel:
        """Determines the permission level for a given action."""
        
        # 1. Check if action is fundamentally blocked
        if tool_name in self.BLOCKED_ACTIONS:
            return PermissionLevel.BLOCKED

        # 2. Check for sensitive file paths in parameters
        if "path" in parameters:
            path = str(parameters["path"])
            for blocked in self.BLOCKED_PATHS:
                if blocked.lower() in path.lower():
                    return PermissionLevel.BLOCKED

        # 3. Check if action requires confirmation
        if tool_name in self.CONFIRM_ACTIONS:
            return PermissionLevel.CONFIRM

        # 4. Check if action is safe
        if tool_name in self.SAFE_ACTIONS:
            return PermissionLevel.SAFE

        # Default to BLOCKED if unknown
        return PermissionLevel.BLOCKED

    def assess_risk(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Return a coarse risk level for a given action."""
        tool = (tool_name or "").lower()

        if tool in {"delete_file", "run_shell", "shutdown", "restart", "format_drive"}:
            return "high"
        if tool in {"write_file", "close_application", "open_application", "adjust_volume", "adjust_brightness"}:
            return "medium"
        if tool in {"type_text", "click", "move_mouse", "press_key"}:
            return "medium"
        if tool in {"read_file", "get_system_info", "get_volume", "get_brightness", "get_window_list", "get_active_window"}:
            return "low"
        if tool in {"get_system_time", "get_system_date", "get_os_info"}:
            return "low"

        return "unknown"

    def is_safe_path(self, path: str) -> bool:
        """Additional helper for path validation."""
        for blocked in self.BLOCKED_PATHS:
            if blocked.lower() in path.lower():
                return False
        return True
