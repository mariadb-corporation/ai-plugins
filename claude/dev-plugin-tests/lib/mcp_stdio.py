"""A tiny MCP stdio client — just enough to call a single tool.

Speaks JSON-RPC 2.0 over newline-delimited stdio, which is the framing the
mariadb-shell MCP server uses when launched as

    mariadb-shell -- mcp start-server --transport=stdio

(i.e. exactly what ``scripts/mariadb-mcp-launcher.sh`` execs). Used by the e2e
tier to tear the sandbox down via a real ``sandbox.delete`` MCP call, and to
discover that tool's exact name/argument schema at runtime (the server is the
authority — we don't hardcode a guess).

This is intentionally minimal: one request in flight at a time, no batching,
generous timeouts, best-effort cleanup. It is a test helper, not a client lib.
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any


class MCPStdioError(RuntimeError):
    pass


class MCPStdioClient:
    """Spawn an MCP server over stdio and issue a handful of requests to it."""

    def __init__(self, command: list[str], env: dict | None = None, timeout: float = 30.0):
        self._command = command
        self._env = env
        self._timeout = timeout
        self._proc: subprocess.Popen | None = None
        self._next_id = 0

    # -- lifecycle -----------------------------------------------------------
    def __enter__(self) -> "MCPStdioClient":
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=self._env,
            text=True,
            bufsize=1,
        )
        self._initialize()
        return self

    def __exit__(self, *exc) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    # -- JSON-RPC plumbing ---------------------------------------------------
    def _send(self, payload: dict) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

    def _read_result(self, expected_id: int) -> Any:
        assert self._proc and self._proc.stdout
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            line = self._proc.stdout.readline()
            if line == "":
                raise MCPStdioError("MCP server closed the stream before responding")
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue  # ignore any non-JSON log noise on stdout
            if msg.get("id") != expected_id:
                continue  # a notification or an unrelated response
            if "error" in msg:
                raise MCPStdioError(f"MCP error: {msg['error']}")
            return msg.get("result")
        raise MCPStdioError(f"timed out waiting {self._timeout}s for response id={expected_id}")

    def _request(self, method: str, params: dict | None = None) -> Any:
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        return self._read_result(rid)

    def _initialize(self) -> None:
        self._request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "ai-plugins-e2e", "version": "0"},
            },
        )
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # -- high level ----------------------------------------------------------
    def list_tools(self) -> list[dict]:
        result = self._request("tools/list") or {}
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> Any:
        return self._request("tools/call", {"name": name, "arguments": arguments})
