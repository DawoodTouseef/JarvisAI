import asyncio
import concurrent.futures
import threading
import inspect
from typing import Any, Callable, Dict, Optional
from .schemas import ActionIntent, AgentEvent

class ExecutionEngine:
    """Manages non-blocking execution of system tools."""

    def __init__(self):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self._current_task: Optional[asyncio.Task] = None
        self._stop_event = threading.Event()

    async def execute_action(self, action: ActionIntent, tool_func: Callable, on_event: Callable) -> Dict[str, Any]:
        """Executes a tool call in a separate thread."""
        
        loop = asyncio.get_running_loop()
        self._stop_event.clear()
        
        try:
            # Run the tool function in the thread pool
            result = await loop.run_in_executor(
                self._executor, 
                self._run_tool_with_safety, 
                tool_func, 
                action.parameters,
                on_event,
                self._stop_event
            )
            return result
            
        except Exception as e:
            # Emit 'step_failed' event
            raise

    def _run_tool_with_safety(self, tool_func: Callable, parameters: Dict[str, Any], on_event: Callable, stop_event: threading.Event) -> Any:
        """Wrapper for thread execution to handle potential issues."""
        if stop_event.is_set():
            raise RuntimeError("Execution interrupted")

        try:
            kwargs = dict(parameters or {})
            signature = inspect.signature(tool_func)
            if "event_callback" in signature.parameters:
                kwargs["event_callback"] = on_event
            if "cancel_event" in signature.parameters:
                kwargs["cancel_event"] = stop_event
            return tool_func(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Tool execution failed: {str(e)}")

    def shutdown(self):
        """Cleanly shutdown the executor."""
        self._stop_event.set()
        self._executor.shutdown(wait=False)

    def cancel(self):
        """Signal the current execution to stop."""
        self._stop_event.set()
