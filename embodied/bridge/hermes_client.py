"""
EmbodiedOS Bridge — Hermes Agent client.

Thin HTTP client for the Nous Research Hermes Agent.  Used by the unified
gateway and pipelines to:

  * Open a session with the EmbodiedOS bridge MCP server registered.
  * Send a structured task (instruction + injected skills + memory hints).
  * Stream the agent's reasoning/tool-call loop back as events.
  * Trigger Hermes' built-in auto-skill creation after a successful campaign.

Every method returns ``{"ok": bool, ...}`` and never raises in the happy
path — callers can treat the result as data, not control flow.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

try:
    import requests
except Exception:  # noqa: BLE001
    requests = None  # type: ignore[assignment]

from embodied.config import HermesConfig, get_config

LOG = logging.getLogger("embodied.bridge.hermes_client")


@dataclass
class HermesSession:
    session_id: str
    base_url: str
    skills: list[str]


class HermesClient:
    """Tiny client for the Hermes Agent HTTP surface."""

    def __init__(self, cfg: HermesConfig | None = None) -> None:
        self.cfg = cfg or get_config().hermes

    # ----- low level -------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.cfg.api_key:
            h["Authorization"] = f"Bearer {self.cfg.api_key}"
        return h

    def _post(self, path: str, payload: dict[str, Any], *, timeout: int = 60) -> dict[str, Any]:
        if requests is None:
            return {"ok": False, "reason": "requests_unavailable"}
        if not self.cfg.enabled:
            return {"ok": False, "reason": "hermes_disabled"}
        url = f"{self.cfg.base_url.rstrip('/')}{path}"
        try:
            r = requests.post(url, json=payload, headers=self._headers(), timeout=timeout)
            data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {"raw": r.text}
            return {"ok": 200 <= r.status_code < 300, "status": r.status_code, **data}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": "hermes_request_failed", "exception": repr(exc)}

    def _get(self, path: str, *, timeout: int = 30) -> dict[str, Any]:
        if requests is None:
            return {"ok": False, "reason": "requests_unavailable"}
        if not self.cfg.enabled:
            return {"ok": False, "reason": "hermes_disabled"}
        try:
            r = requests.get(f"{self.cfg.base_url.rstrip('/')}{path}", headers=self._headers(), timeout=timeout)
            data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {"raw": r.text}
            return {"ok": 200 <= r.status_code < 300, "status": r.status_code, **data}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": "hermes_request_failed", "exception": repr(exc)}

    # ----- high level ------------------------------------------------------

    def healthz(self) -> dict[str, Any]:
        return self._get("/healthz")

    def open_session(self, *, mission: str, skills: Iterable[str] = ()) -> HermesSession | None:
        resp = self._post("/v1/session", {"mission": mission, "skills": list(skills)})
        if not resp.get("ok"):
            LOG.warning("Hermes open_session failed: %s", resp)
            return None
        return HermesSession(
            session_id=resp.get("session_id", ""),
            base_url=self.cfg.base_url,
            skills=list(skills),
        )

    def run_task(
        self,
        *,
        session_id: str,
        instruction: str,
        skills_prompt: str = "",
        memory_hints: list[dict[str, Any]] | None = None,
        max_iterations: int = 20,
        bridge_url: str | None = None,
    ) -> dict[str, Any]:
        cfg = get_config().bridge
        bridge_url = bridge_url or f"http://{cfg.host}:{cfg.port}"
        payload: dict[str, Any] = {
            "session_id":     session_id,
            "instruction":    instruction,
            "skills_prompt":  skills_prompt,
            "memory_hints":   memory_hints or [],
            "max_iterations": max_iterations,
            "mcp_servers":    [{"name": "embodied-os-bridge", "url": bridge_url}],
        }
        return self._post("/v1/run", payload, timeout=600)

    def teach_skill(self, *, name: str, frontmatter: dict[str, Any], body: str) -> dict[str, Any]:
        """Push an auto-created skill back to Hermes' skill store."""
        return self._post("/v1/skills/auto", {"name": name, "frontmatter": frontmatter, "body": body})

    def request_subagent(
        self,
        *,
        parent_session: str,
        role: str,
        instruction: str,
        skills: Iterable[str] = (),
    ) -> dict[str, Any]:
        return self._post("/v1/subagent", {
            "parent": parent_session,
            "role":   role,
            "instruction": instruction,
            "skills": list(skills),
        })

    def remember_episode(self, *, summary: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._post("/v1/memory/episode", {"summary": summary, "metadata": metadata or {}})
