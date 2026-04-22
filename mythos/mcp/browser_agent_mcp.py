"""
browser-agent-mcp — Playwright-driven live browser for web app testing (§9.3).

Tools
-----
* ``navigate(url)``                       → headers, status, title, dom_snippet
* ``click(selector)``                     → result
* ``fill_form(selector, value)``          → result
* ``intercept_requests()``                → HAR-like list of recent requests
* ``inject_payload(selector, payload)``   → response analysis
* ``screenshot()``                        → base64 PNG (vision-model ready)

If Playwright is unavailable we fall back to a ``requests``-based stub so the
tool surface stays callable for unit tests and operator smoke runs.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from ._mcp_runtime import MCPServer

server = MCPServer(name="browser-agent-mcp")

try:
    from playwright.sync_api import sync_playwright  # type: ignore
    _PW = True
except Exception:  # noqa: BLE001
    _PW = False

_CONTEXT: dict[str, Any] = {"page": None, "ctx": None, "pw": None, "requests": []}


def _ensure_browser():
    if not _PW:
        return None
    if _CONTEXT["page"] is not None:
        return _CONTEXT["page"]
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )
    ctx = browser.new_context(
        ignore_https_errors=True,
        user_agent=os.getenv("ARCHITECT_BROWSER_UA",
                             "Mozilla/5.0 ARCHITECT-Bounty/1.0 (security-research)"),
    )
    page = ctx.new_page()

    def _on_req(req):
        _CONTEXT["requests"].append({
            "url": req.url, "method": req.method, "headers": dict(req.headers)})
    page.on("request", _on_req)
    _CONTEXT.update({"pw": pw, "ctx": ctx, "page": page})
    return page


@server.tool("navigate", schema={"url": "string"})
def navigate(url: str) -> dict[str, Any]:
    page = _ensure_browser()
    if page is None:
        import requests
        try:
            r = requests.get(url, timeout=15, allow_redirects=True)
            return {"backend": "requests", "status": r.status_code,
                    "headers": dict(r.headers), "title": "", "dom_snippet": r.text[:1500]}
        except Exception as exc:  # noqa: BLE001
            return {"backend": "requests", "error": str(exc)}
    resp = page.goto(url, timeout=20_000, wait_until="domcontentloaded")
    return {
        "backend": "playwright", "status": resp.status if resp else None,
        "headers": dict(resp.headers) if resp else {},
        "title": page.title(), "dom_snippet": page.content()[:1500],
    }


@server.tool("click", schema={"selector": "string"})
def click(selector: str) -> dict[str, Any]:
    page = _ensure_browser()
    if page is None:
        return {"available": False, "reason": "playwright-not-installed"}
    page.click(selector, timeout=10_000)
    return {"clicked": selector, "url": page.url}


@server.tool("fill_form", schema={"selector": "string", "value": "string"})
def fill_form(selector: str, value: str) -> dict[str, Any]:
    page = _ensure_browser()
    if page is None:
        return {"available": False, "reason": "playwright-not-installed"}
    page.fill(selector, value, timeout=10_000)
    return {"filled": selector, "len": len(value)}


@server.tool("intercept_requests", schema={})
def intercept_requests() -> dict[str, Any]:
    return {"requests": list(_CONTEXT["requests"])[-200:]}


@server.tool("inject_payload", schema={"selector": "string", "payload": "string"})
def inject_payload(selector: str, payload: str) -> dict[str, Any]:
    page = _ensure_browser()
    if page is None:
        return {"available": False, "reason": "playwright-not-installed"}
    page.fill(selector, payload, timeout=10_000)
    page.keyboard.press("Enter")
    return {"injected_into": selector, "payload_len": len(payload),
            "url_after": page.url, "snippet": page.content()[:1200]}


@server.tool("screenshot", schema={})
def screenshot() -> dict[str, Any]:
    page = _ensure_browser()
    if page is None:
        return {"available": False, "reason": "playwright-not-installed"}
    png = page.screenshot(full_page=True)
    return {"png_b64": base64.b64encode(png).decode(), "url": page.url}


if __name__ == "__main__":
    server.serve_stdio()
