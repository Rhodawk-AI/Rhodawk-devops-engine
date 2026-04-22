"""
wayback-mcp — Wayback Machine + URLScan historical-URL miner (§9.2).
"""

from __future__ import annotations

import os
from typing import Any

import requests

from ._mcp_runtime import MCPServer

server = MCPServer(name="wayback-mcp")


@server.tool("snapshots", schema={"domain": "string", "limit": "int"})
def snapshots(domain: str, limit: int = 5000) -> dict[str, Any]:
    url = ("https://web.archive.org/cdx/search/cdx"
           f"?url=*.{domain}/*&output=json&fl=original&collapse=urlkey&limit={limit}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        rows = r.json()
        urls = [row[0] for row in rows[1:]] if len(rows) > 1 else []
        return {"domain": domain, "urls": urls, "count": len(urls)}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "urls": []}


@server.tool("urlscan_search", schema={"query": "string"})
def urlscan_search(query: str) -> dict[str, Any]:
    key = os.getenv("URLSCAN_API_KEY", "")
    headers = {"API-Key": key} if key else {}
    try:
        r = requests.get("https://urlscan.io/api/v1/search/",
                         params={"q": query, "size": 100},
                         headers=headers, timeout=20)
        r.raise_for_status()
        d = r.json()
        return {"query": query, "results": d.get("results", []),
                "total": d.get("total", 0)}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


if __name__ == "__main__":
    server.serve_stdio()
