"""
camofox_client.py
─────────────────
Python client for the embedded camofox-browser anti-detection browser server
(https://github.com/jo-inc/camofox-browser).

camofox-browser wraps the Camoufox engine — a Firefox fork with fingerprint
spoofing patched at the C++ implementation level — behind a small REST API
designed for AI agents:

  * accessibility snapshots with stable element refs (e1, e2, e3 …)
  * session isolation per userId / sessionKey
  * Netscape-format cookie import for authenticated browsing
  * residential-proxy + GeoIP routing
  * search macros (@google_search, @youtube_search, …)
  * download capture, DOM image extraction, screenshot snapshots

Inside the Rhodawk container the camofox node server is launched by
`entrypoint.sh` on 127.0.0.1:9377.  This module is the thin Python
adapter the orchestrator and other engines (repo_harvester, cve_intel,
red_team_fuzzer, knowledge_rag, …) use to drive it.

Design goals
────────────
1. Zero hard dependency — if the camofox server is not running the
   client raises ``CamofoxUnavailable`` and the caller can degrade
   gracefully (e.g. fall back to plain ``requests.get``).
2. No ``console.print``-style side effects — pure return values + the
   structured ``audit_logger`` for production observability.
3. Safe defaults — every browsing call carries a ``userId`` and an
   optional ``sessionKey`` so different research jobs cannot leak
   cookies into each other.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

log = logging.getLogger("rhodawk.camofox")

# ─── Configuration ─────────────────────────────────────────────────────
CAMOFOX_BASE_URL = os.environ.get("CAMOFOX_BASE_URL", "http://127.0.0.1:9377").rstrip("/")
CAMOFOX_API_KEY = os.environ.get("CAMOFOX_API_KEY", "")
CAMOFOX_DEFAULT_TIMEOUT = float(os.environ.get("CAMOFOX_TIMEOUT", "60"))
CAMOFOX_HEALTH_TIMEOUT = float(os.environ.get("CAMOFOX_HEALTH_TIMEOUT", "3"))


# ─── Errors ────────────────────────────────────────────────────────────
class CamofoxError(RuntimeError):
    """Base class for any camofox-browser interaction failure."""


class CamofoxUnavailable(CamofoxError):
    """Raised when the camofox server is not reachable.

    Callers should treat this as a soft failure and fall back to a
    non-browser code path (e.g. plain HTTP fetch) instead of aborting.
    """


class CamofoxAPIError(CamofoxError):
    """Raised when the server is reachable but returns a non-2xx response."""

    def __init__(self, status: int, body: str, *, endpoint: str = ""):
        super().__init__(f"[{endpoint}] HTTP {status}: {body[:512]}")
        self.status = status
        self.body = body
        self.endpoint = endpoint


# ─── Session handle ────────────────────────────────────────────────────
@dataclass
class CamofoxTab:
    """Lightweight handle to a single tab inside the camofox server.

    Tabs are owned by ``(userId, sessionKey)``.  Two researchers using
    different ``userId`` values get fully isolated cookie jars and
    storage state — important when one job is logged-in to GitHub and
    the other is performing CVE intel scraping anonymously.
    """
    tab_id: str
    user_id: str
    session_key: str = "default"
    url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


# ─── Client ────────────────────────────────────────────────────────────
class CamofoxClient:
    """Thin REST wrapper around the local camofox-browser server."""

    def __init__(
        self,
        base_url: str = CAMOFOX_BASE_URL,
        api_key: str = CAMOFOX_API_KEY,
        timeout: float = CAMOFOX_DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()

    # ── Internal ──────────────────────────────────────────────────────
    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(
                method,
                url,
                json=json_body,
                params=params,
                headers=self._headers(),
                timeout=timeout or self.timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            raise CamofoxUnavailable(
                f"camofox server not reachable at {self.base_url}: {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise CamofoxError(f"camofox request timed out: {exc}") from exc

        if resp.status_code >= 400:
            raise CamofoxAPIError(resp.status_code, resp.text, endpoint=path)

        if not resp.content:
            return {}
        ct = resp.headers.get("content-type", "")
        if "application/json" not in ct:
            return {"raw": resp.text}
        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise CamofoxError(f"invalid JSON from {path}: {exc}") from exc

    # ── Health ────────────────────────────────────────────────────────
    def is_available(self) -> bool:
        """Return True if the camofox server is up.  Never raises."""
        try:
            self._request("GET", "/health", timeout=CAMOFOX_HEALTH_TIMEOUT)
            return True
        except CamofoxError:
            return False

    def wait_ready(self, max_wait: float = 30.0, poll_interval: float = 0.5) -> bool:
        """Block until the server responds to /health or ``max_wait`` elapses."""
        deadline = time.time() + max_wait
        while time.time() < deadline:
            if self.is_available():
                return True
            time.sleep(poll_interval)
        return False

    # ── Tab lifecycle ────────────────────────────────────────────────
    def create_tab(
        self,
        user_id: str,
        url: str,
        *,
        session_key: str = "default",
        wait_until: str = "domcontentloaded",
    ) -> CamofoxTab:
        body = {
            "userId": user_id,
            "sessionKey": session_key,
            "url": url,
            "waitUntil": wait_until,
        }
        out = self._request("POST", "/tabs", json_body=body)
        tab_id = out.get("tabId") or out.get("id")
        if not tab_id:
            raise CamofoxError(f"create_tab returned no tabId: {out}")
        return CamofoxTab(
            tab_id=tab_id,
            user_id=user_id,
            session_key=session_key,
            url=out.get("url", url),
            extra={k: v for k, v in out.items() if k not in {"tabId", "id", "url"}},
        )

    def list_tabs(self, user_id: str) -> List[Dict[str, Any]]:
        out = self._request("GET", "/tabs", params={"userId": user_id})
        return out.get("tabs", []) if isinstance(out, dict) else []

    def close_tab(self, tab: CamofoxTab) -> None:
        self._request(
            "DELETE",
            f"/tabs/{tab.tab_id}",
            params={"userId": tab.user_id},
        )

    # ── Snapshot / interaction ───────────────────────────────────────
    def snapshot(
        self,
        tab: CamofoxTab,
        *,
        include_screenshot: bool = False,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Accessibility snapshot — ~90% smaller than raw HTML,
        annotated with stable element refs (e1, e2, …)."""
        params: Dict[str, Any] = {"userId": tab.user_id}
        if include_screenshot:
            params["screenshot"] = "true"
        if offset:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        return self._request("GET", f"/tabs/{tab.tab_id}/snapshot", params=params)

    def click(self, tab: CamofoxTab, ref: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/tabs/{tab.tab_id}/click",
            json_body={"userId": tab.user_id, "ref": ref},
        )

    def type_text(
        self,
        tab: CamofoxTab,
        ref: str,
        text: str,
        *,
        press_enter: bool = False,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/tabs/{tab.tab_id}/type",
            json_body={
                "userId": tab.user_id,
                "ref": ref,
                "text": text,
                "pressEnter": press_enter,
            },
        )

    def navigate(
        self,
        tab: CamofoxTab,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/tabs/{tab.tab_id}/navigate",
            json_body={
                "userId": tab.user_id,
                "url": url,
                "waitUntil": wait_until,
            },
        )

    def scroll(
        self,
        tab: CamofoxTab,
        *,
        direction: str = "down",
        amount: int = 1,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/tabs/{tab.tab_id}/scroll",
            json_body={
                "userId": tab.user_id,
                "direction": direction,
                "amount": amount,
            },
        )

    def screenshot(
        self,
        tab: CamofoxTab,
        *,
        full_page: bool = False,
    ) -> bytes:
        """Return raw PNG bytes for ``tab``."""
        url = f"{self.base_url}/tabs/{tab.tab_id}/screenshot"
        try:
            resp = self._session.get(
                url,
                params={"userId": tab.user_id, "fullPage": str(full_page).lower()},
                headers={k: v for k, v in self._headers().items() if k != "Content-Type"},
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            raise CamofoxUnavailable(str(exc)) from exc
        if resp.status_code >= 400:
            raise CamofoxAPIError(resp.status_code, resp.text, endpoint="/screenshot")
        return resp.content

    # ── Cookies / auth ───────────────────────────────────────────────
    def import_cookies(
        self,
        user_id: str,
        cookies: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Inject pre-exported cookies into a session.

        Requires ``CAMOFOX_API_KEY`` to be set; without it the camofox
        server rejects cookie writes with 403 by design.
        """
        if not self.api_key:
            raise CamofoxError(
                "CAMOFOX_API_KEY env var is required for cookie import"
            )
        return self._request(
            "POST",
            f"/sessions/{user_id}/cookies",
            json_body={"cookies": cookies},
        )

    # ── YouTube transcript (optional, ships with camofox) ────────────
    def youtube_transcript(self, video_url: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/youtube/transcript",
            json_body={"url": video_url},
        )


# ─── Module-level convenience singleton ────────────────────────────────
_default_client: Optional[CamofoxClient] = None


def get_client() -> CamofoxClient:
    """Lazy module-wide singleton — most callers just want this."""
    global _default_client
    if _default_client is None:
        _default_client = CamofoxClient()
    return _default_client


def fetch_snapshot(
    url: str,
    *,
    user_id: str = "rhodawk",
    session_key: str = "default",
    include_screenshot: bool = False,
    close_when_done: bool = True,
) -> Dict[str, Any]:
    """One-shot helper: open ``url`` in a fresh tab, return its snapshot,
    then close the tab.  Returns ``{"available": False}`` if the camofox
    server is not running so the caller can fall back gracefully.
    """
    client = get_client()
    if not client.is_available():
        return {"available": False, "reason": "camofox server not reachable"}
    tab = client.create_tab(user_id, url, session_key=session_key)
    try:
        snap = client.snapshot(tab, include_screenshot=include_screenshot)
        snap["available"] = True
        snap["tabId"] = tab.tab_id
        return snap
    finally:
        if close_when_done:
            try:
                client.close_tab(tab)
            except CamofoxError as exc:
                log.warning("close_tab failed for %s: %s", tab.tab_id, exc)


__all__ = [
    "CamofoxClient",
    "CamofoxTab",
    "CamofoxError",
    "CamofoxUnavailable",
    "CamofoxAPIError",
    "get_client",
    "fetch_snapshot",
]
