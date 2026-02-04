from .registry import register_tool

try:
    import pyautogui
except ImportError:
    pyautogui = None

@register_tool("type_text")
def type_text(text: str, interval: float = 0.05) -> dict:
    if not pyautogui:
        return {"error": "pyautogui not installed"}
    
    try:
        pyautogui.write(text, interval=interval)
        return {"success": True, "message": f"Typed '{text}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("click")
def click(x: int, y: int, clicks: int = 1) -> dict:
    if not pyautogui:
        return {"error": "pyautogui not installed"}
    
    try:
        pyautogui.click(x, y, clicks=clicks)
        return {"success": True, "message": f"Clicked at ({x}, {y})"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("move_mouse")
def move_mouse(x: int, y: int) -> dict:
    if not pyautogui:
        return {"error": "pyautogui not installed"}
    
    try:
        pyautogui.moveTo(x, y)
        return {"success": True, "message": f"Moved mouse to ({x}, {y})"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("press_key")
def press_key(key: str) -> dict:
    if not pyautogui:
        return {"error": "pyautogui not installed"}
    
    try:
        pyautogui.press(key)
        return {"success": True, "message": f"Pressed key '{key}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}
