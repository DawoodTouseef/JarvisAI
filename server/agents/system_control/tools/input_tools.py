import time
from .registry import register_tool

try:
    import pyautogui
    import pynput
except ImportError:
    pyautogui = None
    pynput = None

def _get_pynput_controllers():
    if not pynput:
        return None, None, None
    from pynput import mouse, keyboard
    return mouse.Controller(), keyboard.Controller(), keyboard

@register_tool("type_text", description="Type text into the active application.")
def type_text(text: str, interval: float = 0.05) -> dict:
    if not pyautogui and not pynput:
        return {"error": "pyautogui or pynput not installed"}
    
    try:
        if pyautogui:
            pyautogui.write(text, interval=interval)
        else:
            _, keyboard_controller, _ = _get_pynput_controllers()
            for ch in text:
                keyboard_controller.type(ch)
                if interval:
                    time.sleep(interval)
        return {"success": True, "message": f"Typed '{text}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("click", description="Click the mouse at screen coordinates.")
def click(x: int, y: int, clicks: int = 1) -> dict:
    if not pyautogui and not pynput:
        return {"error": "pyautogui or pynput not installed"}
    
    try:
        if pyautogui:
            pyautogui.click(x, y, clicks=clicks)
        else:
            mouse_controller, _, _ = _get_pynput_controllers()
            from pynput.mouse import Button
            mouse_controller.position = (x, y)
            for _ in range(max(1, clicks)):
                mouse_controller.click(Button.left, 1)
        return {"success": True, "message": f"Clicked at ({x}, {y})"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("move_mouse", description="Move the mouse cursor to screen coordinates.")
def move_mouse(x: int, y: int) -> dict:
    if not pyautogui and not pynput:
        return {"error": "pyautogui or pynput not installed"}
    
    try:
        if pyautogui:
            pyautogui.moveTo(x, y)
        else:
            mouse_controller, _, _ = _get_pynput_controllers()
            mouse_controller.position = (x, y)
        return {"success": True, "message": f"Moved mouse to ({x}, {y})"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("press_key", description="Press a keyboard key.")
def press_key(key: str) -> dict:
    if not pyautogui and not pynput:
        return {"error": "pyautogui or pynput not installed"}
    
    try:
        if pyautogui:
            pyautogui.press(key)
        else:
            _, keyboard_controller, keyboard_module = _get_pynput_controllers()
            key_lower = key.lower()
            if len(key) == 1:
                keyboard_controller.press(key)
                keyboard_controller.release(key)
            else:
                special = getattr(keyboard_module.Key, key_lower, None)
                if not special:
                    return {"success": False, "error": f"Unsupported key '{key}'"}
                keyboard_controller.press(special)
                keyboard_controller.release(special)
        return {"success": True, "message": f"Pressed key '{key}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}
