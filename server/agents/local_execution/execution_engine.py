"""Local execution engine with sandboxed and privileged runners."""

from __future__ import annotations

import asyncio
import contextlib
import sys
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional


EventCallback = Callable[[str, str, Dict[str, str]], Awaitable[None]]


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int


class CancellationToken:
    """Simple cancellation token shared across execution layers."""

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled


class ExecutionEngine:
    """Runs code with streaming output and optional sandboxing."""

    def __init__(self, event_callback: Optional[EventCallback] = None) -> None:
        self._event_callback = event_callback

    def set_event_callback(self, event_callback: Optional[EventCallback]) -> None:
        self._event_callback = event_callback

    async def _emit_chunk(self, task_id: str, text: str) -> None:
        if not self._event_callback or not text:
            return
        await self._event_callback("assistant_text_chunk", task_id, {"text": text})

    async def run_python_sandbox(
        self,
        task_id: str,
        code: str,
        timeout: int,
        token: CancellationToken,
    ) -> ExecutionResult:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str] = asyncio.Queue()

        def _safe_import(name: str, globals_: Optional[Dict] = None, locals_: Optional[Dict] = None, fromlist=(), level: int = 0):
            allowed = {
                "math",
                "statistics",
                "json",
                "csv",
                "re",
                "datetime",
                "itertools",
                "collections",
                "random",
            }
            if name in allowed:
                return __import__(name, globals_, locals_, fromlist, level)
            raise ImportError(f"Module '{name}' is not allowed in sandbox.")

        class StreamWriter:
            def __init__(self, prefix: str) -> None:
                self._prefix = prefix
                self._buffer: list[str] = []

            def write(self, data: str) -> None:
                if not data:
                    return
                self._buffer.append(data)
                loop.call_soon_threadsafe(queue.put_nowait, f"{self._prefix}{data}")

            def flush(self) -> None:
                return None

        def _run_exec() -> ExecutionResult:
            import builtins
            import traceback
            import sys as _sys

            start_time = time.monotonic()

            def _trace(_, __, ___):
                if token.cancelled:
                    raise RuntimeError("Execution cancelled.")
                if time.monotonic() - start_time > timeout:
                    raise TimeoutError("Sandbox execution timed out.")
                return _trace

            safe_builtins = {
                "abs": builtins.abs,
                "all": builtins.all,
                "any": builtins.any,
                "bool": builtins.bool,
                "dict": builtins.dict,
                "Exception": builtins.Exception,
                "enumerate": builtins.enumerate,
                "float": builtins.float,
                "int": builtins.int,
                "len": builtins.len,
                "list": builtins.list,
                "ValueError": builtins.ValueError,
                "TypeError": builtins.TypeError,
                "RuntimeError": builtins.RuntimeError,
                "max": builtins.max,
                "min": builtins.min,
                "print": builtins.print,
                "range": builtins.range,
                "set": builtins.set,
                "str": builtins.str,
                "sum": builtins.sum,
                "tuple": builtins.tuple,
                "zip": builtins.zip,
                "__import__": _safe_import,
            }

            globals_dict: Dict[str, object] = {
                "__builtins__": safe_builtins,
                "__name__": "__sandbox__",
            }

            stdout_writer = StreamWriter(prefix="")
            stderr_writer = StreamWriter(prefix="[stderr] ")

            try:
                _sys.settrace(_trace)
                with contextlib.redirect_stdout(stdout_writer):
                    with contextlib.redirect_stderr(stderr_writer):
                        exec(code, globals_dict, {})
            except Exception:
                traceback.print_exc(file=stderr_writer)
            finally:
                _sys.settrace(None)

            return ExecutionResult(
                stdout="".join(stdout_writer._buffer),
                stderr="".join(stderr_writer._buffer),
                exit_code=0 if not stderr_writer._buffer else 1,
            )

        async def _drain_queue(exec_task: asyncio.Task) -> None:
            while True:
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    if token.cancelled:
                        break
                    if exec_task.done() and queue.empty():
                        break
                    continue
                await self._emit_chunk(task_id, chunk)

        exec_task = asyncio.create_task(asyncio.to_thread(_run_exec))
        drain_task = asyncio.create_task(_drain_queue(exec_task))

        try:
            result = await exec_task
        finally:
            await drain_task

        return result

    async def run_python_privileged(
        self,
        task_id: str,
        code: str,
        timeout: int,
        token: CancellationToken,
    ) -> ExecutionResult:
        return await self._run_subprocess(task_id, [sys.executable, "-c", code], timeout, token)

    async def run_js(
        self,
        task_id: str,
        code: str,
        sandbox: bool,
        timeout: int,
        token: CancellationToken,
    ) -> ExecutionResult:
        if sandbox:
            try:
                import js2py  # type: ignore
            except Exception as exc:
                raise RuntimeError("JavaScript sandbox runtime is unavailable.") from exc

            def _run_js() -> ExecutionResult:
                try:
                    result = js2py.eval_js(code)
                    output = "" if result is None else str(result)
                    return ExecutionResult(stdout=output, stderr="", exit_code=0)
                except Exception as exc:
                    return ExecutionResult(stdout="", stderr=str(exc), exit_code=1)

            result = await asyncio.to_thread(_run_js)
            if result.stdout:
                await self._emit_chunk(task_id, result.stdout)
            if result.stderr:
                await self._emit_chunk(task_id, f"[stderr] {result.stderr}")
            return result

        return await self._run_subprocess(task_id, ["node", "-e", code], timeout, token)

    async def run_shell(
        self,
        task_id: str,
        command: str,
        timeout: int,
        token: CancellationToken,
    ) -> ExecutionResult:
        return await self._run_subprocess(task_id, command, timeout, token, use_shell=True)

    async def run_app_open(
        self,
        task_id: str,
        app_name: str,
        token: CancellationToken,
    ) -> ExecutionResult:
        if token.cancelled:
            return ExecutionResult(stdout="", stderr="Execution cancelled.", exit_code=1)
        try:
            from AppOpener import open as open_app_cmd  # type: ignore
        except Exception as exc:
            return ExecutionResult(stdout="", stderr=f"AppOpener not available: {exc}", exit_code=1)

        def _open() -> ExecutionResult:
            try:
                result = open_app_cmd(app_name, match_closest=True)
                output = "" if result is None else str(result)
                return ExecutionResult(stdout=output, stderr="", exit_code=0)
            except Exception as exc:
                return ExecutionResult(stdout="", stderr=str(exc), exit_code=1)

        result = await asyncio.to_thread(_open)
        if result.stdout:
            await self._emit_chunk(task_id, result.stdout)
        if result.stderr:
            await self._emit_chunk(task_id, f"[stderr] {result.stderr}")
        return result

    async def _run_subprocess(
        self,
        task_id: str,
        command,
        timeout: int,
        token: CancellationToken,
        use_shell: bool = False,
    ) -> ExecutionResult:
        if use_shell:
            process = await asyncio.create_subprocess_shell(
                command if isinstance(command, str) else " ".join(command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *command if isinstance(command, list) else [command],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )

        stdout_parts: list[str] = []
        stderr_parts: list[str] = []

        async def _read_stream(stream, prefix: str, collector: list[str]) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode(errors="replace")
                collector.append(text)
                await self._emit_chunk(task_id, f"{prefix}{text}")

        stdout_task = asyncio.create_task(_read_stream(process.stdout, "", stdout_parts))
        stderr_task = asyncio.create_task(_read_stream(process.stderr, "[stderr] ", stderr_parts))
        cancel_task = asyncio.create_task(self._watch_cancel(process, token))

        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            token.cancel()
            process.kill()
        finally:
            await stdout_task
            await stderr_task
            cancel_task.cancel()

        return ExecutionResult(
            stdout="".join(stdout_parts),
            stderr="".join(stderr_parts),
            exit_code=process.returncode if process.returncode is not None else -1,
        )

    async def _watch_cancel(self, process: asyncio.subprocess.Process, token: CancellationToken) -> None:
        while process.returncode is None:
            if token.cancelled:
                process.kill()
                return
            await asyncio.sleep(0.1)
