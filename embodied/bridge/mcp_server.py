"""
EmbodiedOS Bridge — Custom MCP Server (Section 4.2).

A single Model-Context-Protocol server that exposes every Rhodawk
capability to **both** Hermes Agent and OpenClaw via three transports:

  * stdio       — one-shot subprocess MCP (Hermes' default).
  * HTTP        — long-running daemon at ``${EMBODIED_BRIDGE_HOST}:${EMBODIED_BRIDGE_PORT}``
                  for OpenClaw / web UIs.
  * Python API  — direct ``call(name, args)`` for in-process callers
                  (the unified gateway, the pipelines, tests).

The server reuses ``mythos.mcp._mcp_runtime.MCPServer`` for stdio so the
wire-format is identical to the existing Mythos MCP servers.  HTTP is
served by Flask if available, else by the stdlib ``http.server``.

Registration files emitted on demand:

  * ``mcp_runtime.embodied.json`` — for Hermes Agent.
  * ``openclaw_mcp.embodied.json`` — for OpenClaw.

Both files are written to ``/tmp`` by default so the entrypoint can wire
them into the agents' configurations on container start-up.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from embodied.config import get_config
from embodied.bridge.tool_registry import ToolRegistry, default_registry

LOG = logging.getLogger("embodied.bridge.mcp_server")


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------


@dataclass
class EmbodiedBridgeServer:
    """Cross-transport MCP server backed by a shared ToolRegistry."""

    registry: ToolRegistry
    name: str = "embodied-os-bridge"

    # ----- Python API ------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        return self.registry.list()

    def call(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.registry.call(name, args or {})

    # ----- stdio (MCP wire protocol) ---------------------------------------

    def serve_stdio(self) -> None:  # pragma: no cover - manual transport
        """Speak the same JSON-line protocol as Mythos MCP servers."""
        try:
            from mythos.mcp._mcp_runtime import MCPServer  # type: ignore
        except Exception:
            MCPServer = None  # noqa: N806

        if MCPServer is not None:
            shim = MCPServer(self.name)
            for spec in self.registry.list():
                tool_name = spec["name"]
                shim.tool(tool_name, spec["schema"])(
                    lambda __t=tool_name, **kw: self.call(__t, kw)
                )
            shim.serve_stdio()
            return

        import sys
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except Exception as exc:  # noqa: BLE001
                sys.stdout.write(json.dumps({"error": f"bad json: {exc}"}) + "\n")
                sys.stdout.flush()
                continue
            method = req.get("method")
            rid = req.get("id")
            if method == "tools/list":
                resp = {"id": rid, "result": self.list_tools()}
            elif method == "tools/call":
                p = req.get("params") or {}
                resp = {"id": rid, "result": self.call(p.get("name", ""), p.get("args"))}
            else:
                resp = {"id": rid, "error": f"unknown method: {method}"}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

    # ----- HTTP transport --------------------------------------------------

    def serve_http(self, host: str, port: int) -> None:
        try:
            from flask import Flask, jsonify, request
        except Exception:
            return self._serve_http_stdlib(host, port)

        cfg = get_config().bridge
        app = Flask("embodied-bridge")

        def _check_secret() -> bool:
            if not cfg.shared_secret:
                return True
            return request.headers.get("X-Embodied-Secret", "") == cfg.shared_secret

        @app.get("/healthz")
        def _healthz():  # type: ignore[unused-ignore]
            return jsonify({"ok": True, "name": self.name, "tools": len(self.registry.list())})

        @app.get("/tools")
        def _tools():  # type: ignore[unused-ignore]
            if not _check_secret():
                return jsonify({"ok": False, "error": "forbidden"}), 403
            return jsonify({"ok": True, "tools": self.list_tools()})

        @app.post("/call")
        def _call():  # type: ignore[unused-ignore]
            if not _check_secret():
                return jsonify({"ok": False, "error": "forbidden"}), 403
            body = request.get_json(force=True, silent=True) or {}
            return jsonify(self.call(body.get("name", ""), body.get("args") or {}))

        LOG.info("EmbodiedOS bridge listening at http://%s:%s", host, port)
        app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)

    def _serve_http_stdlib(self, host: str, port: int) -> None:  # pragma: no cover
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        srv = self  # capture

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, code: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802
                if self.path == "/healthz":
                    return self._send_json(200, {"ok": True, "name": srv.name})
                if self.path == "/tools":
                    return self._send_json(200, {"ok": True, "tools": srv.list_tools()})
                return self._send_json(404, {"ok": False, "error": "not_found"})

            def do_POST(self):  # noqa: N802
                if self.path != "/call":
                    return self._send_json(404, {"ok": False, "error": "not_found"})
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw or b"{}")
                except Exception as exc:  # noqa: BLE001
                    return self._send_json(400, {"ok": False, "error": f"bad json: {exc}"})
                return self._send_json(200, srv.call(body.get("name", ""), body.get("args") or {}))

            def log_message(self, *args, **kwargs):  # silence default access log
                return

        srv_http = ThreadingHTTPServer((host, port), Handler)
        LOG.info("EmbodiedOS bridge listening (stdlib) at http://%s:%s", host, port)
        srv_http.serve_forever()

    # ----- Registration emitters -------------------------------------------

    def emit_hermes_registration(self, path: str | os.PathLike[str]) -> Path:
        """Emit a JSON file Hermes Agent can load via ``--mcp-config``."""
        cfg = get_config()
        payload = {
            "mcpServers": {
                "embodied-os-bridge": {
                    "transport": "http",
                    "url":       f"http://{cfg.bridge.host}:{cfg.bridge.port}",
                    "headers":   {"X-Embodied-Secret": cfg.bridge.shared_secret} if cfg.bridge.shared_secret else {},
                }
            }
        }
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2))
        return out

    def emit_openclaw_registration(self, path: str | os.PathLike[str]) -> Path:
        """Emit a JSON snippet for ``openclaw register-mcp``."""
        cfg = get_config()
        payload = {
            "name":    "embodied-os-bridge",
            "type":    "http",
            "url":     f"http://{cfg.bridge.host}:{cfg.bridge.port}",
            "auth":    {"header": "X-Embodied-Secret", "value": cfg.bridge.shared_secret},
            "tools":   [t["name"] for t in self.registry.list()],
        }
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2))
        return out


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def build_server() -> EmbodiedBridgeServer:
    return EmbodiedBridgeServer(registry=default_registry())


def serve(transport: str | None = None, *, host: str | None = None, port: int | None = None) -> None:
    """Start the bridge in the foreground using the configured transport."""
    cfg = get_config().bridge
    transport = (transport or cfg.transport or "http").lower()
    server = build_server()
    if transport == "stdio":
        server.serve_stdio()
    else:
        server.serve_http(host or cfg.host, port or cfg.port)


def serve_in_background() -> threading.Thread:
    """Spawn the HTTP transport in a daemon thread (for embedding)."""
    cfg = get_config().bridge
    server = build_server()
    t = threading.Thread(
        target=server.serve_http,
        args=(cfg.host, cfg.port),
        name="embodied-bridge-http",
        daemon=True,
    )
    t.start()
    return t
