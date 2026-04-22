"""
Tiny in-process MCP-compatible runtime used by every Mythos MCP server.

Real production deployments will swap this for the official ``mcp`` Python
SDK.  Keeping a local shim means the Mythos servers can be exercised
end-to-end inside the existing HuggingFace Space without pulling extra
binary deps.

Wire protocol on stdio:

    >>> {"id": 1, "method": "tools/list"}
    <<< {"id": 1, "result": [{"name": "...", "schema": {...}}]}
    >>> {"id": 2, "method": "tools/call", "params": {"name": "...", "args": {...}}}
    <<< {"id": 2, "result": {...}}
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Callable

LOG = logging.getLogger("mythos.mcp")


class MCPServer:
    def __init__(self, name: str):
        self.name = name
        self._tools: dict[str, dict[str, Any]] = {}

    def tool(self, name: str, schema: dict[str, Any] | None = None):
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[name] = {"fn": fn, "schema": schema or {}}
            return fn
        return decorator

    # -- introspection ------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": n, "schema": meta["schema"]} for n, meta in self._tools.items()]

    def call(self, name: str, args: dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]["fn"](**(args or {}))

    # -- transports ---------------------------------------------------------

    def serve_stdio(self) -> None:  # pragma: no cover - manual transport
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                method = req.get("method")
                rid = req.get("id")
                if method == "tools/list":
                    resp = {"id": rid, "result": self.list_tools()}
                elif method == "tools/call":
                    params = req.get("params", {})
                    resp = {"id": rid,
                            "result": self.call(params.get("name"), params.get("args", {}))}
                else:
                    resp = {"id": rid, "error": {"code": -32601, "message": "unknown method"}}
            except Exception as exc:  # noqa: BLE001
                resp = {"id": req.get("id") if isinstance(req, dict) else None,
                        "error": {"code": -32000, "message": str(exc)}}
            sys.stdout.write(json.dumps(resp, default=str) + "\n")
            sys.stdout.flush()
