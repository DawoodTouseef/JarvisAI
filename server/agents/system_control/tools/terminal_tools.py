import os
import re
import shlex
import subprocess
import time
from typing import Optional
from .registry import register_tool
from ..schemas import AgentEvent


DEFAULT_ALLOWLIST = {
    "dir",
    "ls",
    "pwd",
    "whoami",
    "ipconfig",
    "ifconfig",
    "ping",
    "python",
    "pip",
    "git",
    "node",
    "npm",
    "yarn",
    "where",
    "which",
}

DEFAULT_DENYLIST = {
    "format",
    "shutdown",
    "reboot",
    "poweroff",
    "rm",
    "del",
    "erase",
    "rmdir",
    "rd",
    "taskkill",
    "kill",
    "stop-process",
    "remove-item",
}

DESTRUCTIVE_PATTERN = re.compile(r"\b(rm|del|erase|rmdir|rd|format|shutdown|reboot|poweroff|taskkill|kill|stop-process|remove-item)\b", re.IGNORECASE)


def _get_base_command(command: str) -> str:
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.strip().split()
    if not tokens:
        return ""
    base = tokens[0].strip().lower()
    return base


def _load_list_from_env(env_var: str) -> set:
    raw = os.getenv(env_var, "")
    if not raw:
        return set()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


@register_tool("run_shell", description="Run a shell command on the system.")
def run_shell(
    command: str,
    cwd: Optional[str] = None,
    timeout_sec: float = 30.0,
    allow_destructive: bool = False,
    event_callback=None,
    cancel_event=None,
) -> dict:
    """Run a shell command with allow/denylist enforcement and streaming output."""
    if not command or not command.strip():
        return {"success": False, "error": "Command is required"}

    base_cmd = _get_base_command(command)
    allowlist = DEFAULT_ALLOWLIST | _load_list_from_env("JARVIS_SHELL_ALLOWLIST")
    denylist = DEFAULT_DENYLIST | _load_list_from_env("JARVIS_SHELL_DENYLIST")

    if base_cmd in denylist:
        return {"success": False, "error": f"Command '{base_cmd}' is blocked by denylist"}

    if allowlist and base_cmd not in allowlist:
        return {"success": False, "error": f"Command '{base_cmd}' is not in allowlist"}

    if DESTRUCTIVE_PATTERN.search(command) and not allow_destructive:
        return {"success": False, "error": "Destructive command requires explicit approval"}

    try:
        start_time = time.time()
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout_lines = []
        stderr_lines = []

        while True:
            if cancel_event and cancel_event.is_set():
                process.terminate()
                return {"success": False, "error": "Execution interrupted", "exit_code": None}

            line = process.stdout.readline() if process.stdout else ""
            if line:
                stdout_lines.append(line)
                if event_callback:
                    event_callback(AgentEvent(
                        event_type="terminal_output",
                        payload={"stream": "stdout", "text": line.rstrip("\n")}
                    ))
            else:
                break

            if timeout_sec and (time.time() - start_time) > timeout_sec:
                process.terminate()
                return {"success": False, "error": "Command timed out", "exit_code": None}

        if process.stderr:
            for line in process.stderr.readlines():
                stderr_lines.append(line)
                if event_callback:
                    event_callback(AgentEvent(
                        event_type="terminal_output",
                        payload={"stream": "stderr", "text": line.rstrip("\n")}
                    ))

        exit_code = process.wait(timeout=timeout_sec)

        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "stdout": "".join(stdout_lines).strip(),
            "stderr": "".join(stderr_lines).strip()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
