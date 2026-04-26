"""
EmbodiedOS Bridge — OpenClaw client.

Thin HTTP client for the OpenClaw multi-channel gateway.  Lets the
unified router push outbound notifications to any registered channel
(Telegram, Discord, Slack, WhatsApp, …) without owning a token per
channel — OpenClaw multiplexes that for us.

Also exposes the ClawHub skill catalogue + Chrome Relay browser bridge.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

try:
    import requests
except Exception:  # noqa: BLE001
    requests = None  # type: ignore[assignment]

from embodied.config import OpenClawConfig, get_config

LOG = logging.getLogger("embodied.bridge.openclaw_client")


@dataclass
class OpenClawChannel:
    name: str
    kind: str       # "telegram" | "discord" | "slack" | "whatsapp" | "webhook"
    handle: str     # chat-id / channel-id / webhook-url


class OpenClawClient:
    def __init__(self, cfg: OpenClawConfig | None = None) -> None:
        self.cfg = cfg or get_config().openclaw

    # ----- low level -------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            h["Authorization"] = f"Bearer {self.cfg.api_key}"
        return h

    def _post(self, path: str, payload: dict[str, Any], *, timeout: int = 30) -> dict[str, Any]:
        if requests is None:
            return {"ok": False, "reason": "requests_unavailable"}
        if not self.cfg.enabled:
            return {"ok": False, "reason": "openclaw_disabled"}
        try:
            r = requests.post(f"{self.cfg.base_url.rstrip('/')}{path}",
                              json=payload, headers=self._headers(), timeout=timeout)
            data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {"raw": r.text}
            return {"ok": 200 <= r.status_code < 300, "status": r.status_code, **data}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": "openclaw_request_failed", "exception": repr(exc)}

    def _get(self, path: str, *, timeout: int = 30) -> dict[str, Any]:
        if requests is None:
            return {"ok": False, "reason": "requests_unavailable"}
        if not self.cfg.enabled:
            return {"ok": False, "reason": "openclaw_disabled"}
        try:
            r = requests.get(f"{self.cfg.base_url.rstrip('/')}{path}",
                             headers=self._headers(), timeout=timeout)
            data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {"raw": r.text}
            return {"ok": 200 <= r.status_code < 300, "status": r.status_code, **data}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": "openclaw_request_failed", "exception": repr(exc)}

    # ----- gateway ---------------------------------------------------------

    def healthz(self) -> dict[str, Any]:
        return self._get("/healthz")

    def list_channels(self) -> list[OpenClawChannel]:
        resp = self._get("/v1/channels")
        if not resp.get("ok"):
            return []
        return [OpenClawChannel(**c) for c in resp.get("channels", [])]

    def push_message(self, *, channel: str, text: str, attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return self._post("/v1/messages", {
            "channel":     channel,
            "text":        text,
            "attachments": attachments or [],
        })

    def broadcast(self, *, text: str, severity: str = "info") -> dict[str, Any]:
        return self._post("/v1/broadcast", {"text": text, "severity": severity})

    # ----- skills (ClawHub) -----------------------------------------------

    def list_skills(self, *, query: str = "", limit: int = 50) -> list[dict[str, Any]]:
        resp = self._get(f"/v1/skills?q={query}&limit={limit}")
        return resp.get("skills", []) if resp.get("ok") else []

    def install_skill(self, *, skill_id: str) -> dict[str, Any]:
        return self._post("/v1/skills/install", {"id": skill_id})

    # ----- Chrome Relay (browser automation) -------------------------------

    def browser_navigate(self, *, url: str, render: bool = True) -> dict[str, Any]:
        return self._post("/v1/browser/navigate", {"url": url, "render": render})

    def browser_extract(self, *, url: str, selector: str = "") -> dict[str, Any]:
        return self._post("/v1/browser/extract", {"url": url, "selector": selector})

    # ----- cron / background jobs ------------------------------------------

    def schedule_job(self, *, name: str, cron: str, command: str) -> dict[str, Any]:
        return self._post("/v1/jobs", {"name": name, "cron": cron, "command": command})

    def list_jobs(self) -> list[dict[str, Any]]:
        resp = self._get("/v1/jobs")
        return resp.get("jobs", []) if resp.get("ok") else []
