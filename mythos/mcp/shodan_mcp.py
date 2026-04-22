"""
shodan-mcp — passive recon via the Shodan REST API (§9.2).

Tools: ``host_info(ip)``, ``search(query)``, ``count(query)``.
Falls back to ``{"available": False}`` when ``SHODAN_API_KEY`` is unset.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from ._mcp_runtime import MCPServer

server = MCPServer(name="shodan-mcp")
BASE = "https://api.shodan.io"


def _key() -> str:
    return os.getenv("SHODAN_API_KEY", "")


def _get(path: str, **params) -> dict[str, Any]:
    k = _key()
    if not k:
        return {"available": False, "reason": "SHODAN_API_KEY not set"}
    params["key"] = k
    try:
        r = requests.get(f"{BASE}{path}", params=params, timeout=15)
        if r.status_code != 200:
            return {"error": r.text, "status": r.status_code}
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


@server.tool("host_info", schema={"ip": "string"})
def host_info(ip: str) -> dict[str, Any]:
    return _get(f"/shodan/host/{ip}")


@server.tool("search", schema={"query": "string", "page": "int"})
def search(query: str, page: int = 1) -> dict[str, Any]:
    return _get("/shodan/host/search", query=query, page=page)


@server.tool("count", schema={"query": "string"})
def count(query: str) -> dict[str, Any]:
    return _get("/shodan/host/count", query=query)


if __name__ == "__main__":
    server.serve_stdio()
