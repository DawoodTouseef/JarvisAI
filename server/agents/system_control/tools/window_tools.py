import time
from .registry import register_tool

try:
    import pygetwindow as gw
    from AppOpener import open as open_app_cmd, close as close_app_cmd
except ImportError:
    gw = None
    open_app_cmd = None
    close_app_cmd = None

@register_tool("open_application", description="Open an application by name.")
def open_application(app_name: str) -> dict:
    if not open_app_cmd:
        return {"error": "AppOpener not installed"}
    
    try:
        open_app_cmd(app_name, match_closest=True)
        time.sleep(2)  # Wait for app to launch
        return {"success": True, "message": f"Opened {app_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("focus_window", description="Focus an application window by title.")
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

@register_tool("close_application", description="Close an application by name.")
def close_application(app_name: str) -> dict:
    if not close_app_cmd:
        return {"error": "AppOpener not installed"}
    
    try:
        close_app_cmd(app_name, match_closest=True)
        return {"success": True, "message": f"Closed {app_name}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("get_window_list", description="List titles of open windows.")
def get_window_list() -> dict:
    if not gw:
        return {"success": False, "error": "pygetwindow not installed"}
    try:
        titles = [t for t in gw.getAllTitles() if t]
        return {"success": True, "windows": titles}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("get_active_window", description="Get the currently active window title.")
def get_active_window() -> dict:
    if not gw:
        return {"success": False, "error": "pygetwindow not installed"}
    try:
        active = gw.getActiveWindow()
        title = active.title if active else None
        return {"success": True, "title": title}
    except Exception as e:
        return {"success": False, "error": str(e)}
