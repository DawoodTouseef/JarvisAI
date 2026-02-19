from .registry import register_tool
from datetime import datetime
import platform
import socket

try:
    import psutil
except ImportError:
    psutil = None

try:
    import screen_brightness_control as sbc
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
except ImportError:
    sbc = None
    AudioUtilities = None

@register_tool("adjust_volume", description="Set system volume level (0.0 to 1.0).")
def adjust_volume(level: float) -> dict:
    """Adjust system volume (0.0 to 1.0)."""
    if not AudioUtilities:
        return {"error": "pycaw not installed"}
    
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level, None)
        return {"success": True, "message": f"Volume set to {level*100}%"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("get_volume", description="Get the current system volume level.")
def get_volume() -> dict:
    if not AudioUtilities:
        return {"error": "pycaw not installed"}
    
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        level = volume.GetMasterVolumeLevelScalar()
        return {"success": True, "level": level}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("adjust_brightness", description="Set screen brightness level (0 to 100).")
def adjust_brightness(level: int) -> dict:
    """Adjust screen brightness (0 to 100)."""
    if not sbc:
        return {"error": "screen_brightness_control not installed"}
    
    try:
        sbc.set_brightness(level)
        return {"success": True, "message": f"Brightness set to {level}%"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("get_brightness", description="Get the current screen brightness level.")
def get_brightness() -> dict:
    if not sbc:
        return {"error": "screen_brightness_control not installed"}
    
    try:
        level = sbc.get_brightness()
        return {"success": True, "level": level}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("get_system_time", description="Get the current local time.")
def get_system_time() -> dict:
    try:
        now = datetime.now()
        return {"success": True, "time": now.strftime("%H:%M:%S"), "timestamp": now.isoformat()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("get_system_date", description="Get the current local date.")
def get_system_date() -> dict:
    try:
        today = datetime.now()
        return {"success": True, "date": today.strftime("%Y-%m-%d"), "timestamp": today.isoformat()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("get_os_info", description="Get basic operating system info.")
def get_os_info() -> dict:
    try:
        return {
            "success": True,
            "os": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "platform": platform.platform()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("get_system_info", description="Get system summary info (CPU, memory, hostname).")
def get_system_info() -> dict:
    try:
        info = {
            "success": True,
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "platform": platform.platform(),
        }
        if psutil:
            info.update({
                "cpu_count": psutil.cpu_count(logical=True),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "uptime_seconds": int(datetime.now().timestamp() - psutil.boot_time()),
            })
        return info
    except Exception as e:
        return {"success": False, "error": str(e)}
