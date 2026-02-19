import os
import subprocess
import sys
from .registry import register_tool

@register_tool("read_file", description="Read a text file from disk.")
def read_file(path: str) -> dict:
    try:
        if not os.path.exists(path):
            return {"success": False, "error": f"File not found: {path}"}
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("write_file", description="Write text content to a file on disk.")
def write_file(path: str, content: str) -> dict:
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "message": f"File written to {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("delete_file", description="Delete a file from disk.")
def delete_file(path: str) -> dict:
    try:
        if not os.path.exists(path):
            return {"success": False, "error": f"File not found: {path}"}
        
        os.remove(path)
        return {"success": True, "message": f"File deleted: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("open_file", description="Open a file with the default application.")
def open_file(path: str) -> dict:
    try:
        if not os.path.exists(path):
            return {"success": False, "error": f"File not found: {path}"}
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return {"success": True, "message": f"Opened file: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool("open_folder", description="Open a folder in the system file manager.")
def open_folder(path: str) -> dict:
    try:
        if not os.path.isdir(path):
            return {"success": False, "error": f"Folder not found: {path}"}
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return {"success": True, "message": f"Opened folder: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
