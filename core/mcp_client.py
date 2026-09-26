"""Minimal JSON-RPC stdio client for the Model Context Protocol (MCP).

Talks to a locally running MCP server (e.g. powerbi-modeling-mcp.exe) over
stdin/stdout using newline-delimited JSON-RPC 2.0 messages, per the MCP
stdio transport spec.

All pipe I/O happens on background reader threads; the public methods
block the *calling* thread until a matching response arrives or the
timeout expires. Callers (Streamlit's main script thread) therefore never
need their own worker threads for this, which sidesteps the classic bug of
mutating st.session_state from a background thread.
"""
from __future__ import annotations

import json
import subprocess
import threading
from itertools import count
from pathlib import Path
from typing import Any, Optional


class MCPError(RuntimeError):
    """Raised when the MCP server returns an error, times out, or is unreachable."""


class MCPClient:
    def __init__(self, executable_path: str, args: Optional[list[str]] = None):
        self._executable_path = executable_path
        self._args = args or []
        self._process: Optional[subprocess.Popen] = None
        self._id_counter = count(1)
        self._pending: dict[int, threading.Event] = {}
        self._results: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._reader_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stderr_lines: list[str] = []

    # -- lifecycle -----------------------------------------------------
    def start(self) -> None:
        if self._process is not None:
            return
        if not Path(self._executable_path).exists():
            raise MCPError(f"MCP executable not found at: {self._executable_path}")

        self._process = subprocess.Popen(
            [self._executable_path, *self._args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
            encoding="utf-8",
        )
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "qrar", "version": "1.0"},
            },
        )
        self._notify("notifications/initialized", {})

    def stop(self) -> None:
        if self._process is None:
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except Exception:
            self._process.kill()
        finally:
            self._process = None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # -- background I/O -------------------------------------------------
    def _read_loop(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        for line in self._process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                # The server may print plain-text logs on stdout; ignore them
                # instead of crashing the reader thread.
                continue
            msg_id = message.get("id")
            if msg_id is None:
                continue  # server-initiated notification, nothing to route it to
            with self._lock:
                self._results[msg_id] = message
                event = self._pending.get(msg_id)
            if event is not None:
                event.set()

    def _drain_stderr(self) -> None:
        assert self._process is not None and self._process.stderr is not None
        for line in self._process.stderr:
            self._stderr_lines.append(line.rstrip())
            del self._stderr_lines[:-200]  # keep only the last 200 lines

    # -- request/response -------------------------------------------------
    def _request(self, method: str, params: dict[str, Any], timeout: float = 60.0) -> Any:
        if self._process is None or self._process.stdin is None:
            raise MCPError("MCP process is not running")

        req_id = next(self._id_counter)
        event = threading.Event()
        with self._lock:
            self._pending[req_id] = event

        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        try:
            self._process.stdin.write(json.dumps(payload) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            with self._lock:
                self._pending.pop(req_id, None)
            raise MCPError(f"Failed to write to MCP server: {exc}") from exc

        if not event.wait(timeout):
            with self._lock:
                self._pending.pop(req_id, None)
            raise MCPError(
                f"Timed out waiting for MCP response to '{method}' after {timeout}s. "
                f"Last server stderr: {self._stderr_lines[-5:]}"
            )

        with self._lock:
            self._pending.pop(req_id, None)
            message = self._results.pop(req_id, {})

        if "error" in message:
            raise MCPError(f"MCP server error on '{method}': {message['error']}")
        return message.get("result")

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            return
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self._process.stdin.write(json.dumps(payload) + "\n")
        self._process.stdin.flush()

    # -- public MCP surface -------------------------------------------------
    def list_tools(self, timeout: float = 30.0) -> list[dict[str, Any]]:
        result = self._request("tools/list", {}, timeout=timeout)
        return result.get("tools", []) if result else []

    def call_tool(self, name: str, arguments: dict[str, Any], timeout: float = 60.0) -> Any:
        result = self._request(
            "tools/call", {"name": name, "arguments": arguments}, timeout=timeout
        )
        if not result:
            return None
        content = result.get("content", [])
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        return "\n".join(texts) if texts else result
