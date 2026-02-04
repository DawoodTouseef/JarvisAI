import time
from .registry import register_tool

try:
    import pygetwindow as gw
    from AppOpener import open as open_app_cmd, close as close_app_cmd
except ImportError:
    gw = None
    open_app_cmd = None
    close_app_cmd = None

@register_tool("open_application")
def open_application(app_name: str) -> dict:
    if not open_app_cmd:
        return {"error": "AppOpener not installed"}
    
    try:
        open_app_cmd(app_name, match_closest=True)
        time.sleep(2)  # Wait for app to launch
        return {"success": True, "message": f"Opened {app_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("focus_window")
def focus_window(app_name: str) -> dict:
    if not gw:
        return {"error": "pygetwindow not installed"}
    
    try:
        windows = gw.getWindowsWithTitle(app_name)
        if windows:
            windows[0].activate()
            return {"success": True, "message": f"Focused {app_name}"}
        return {"success": False, "error": f"No window found for {app_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("close_application")
def close_application(app_name: str) -> dict:
    if not close_app_cmd:
        return {"error": "AppOpener not installed"}
    
    try:
        close_app_cmd(app_name, match_closest=True)
        return {"success": True, "message": f"Closed {app_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
