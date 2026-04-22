"""
ARCHITECT — EmbodiedOS bridge (§6 of the Masterplan).

Forwards every confirmed finding from Hermes / Mythos to:

  * Telegram (operator notifications)
  * OpenClaw webhook (multi-channel gateway)
  * Hermes Agent skill-extraction endpoint
  * Discord (optional, mirror channel)

All emitters are best-effort; a downstream outage never blocks the audit
pipeline.

Environment:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    OPENCLAW_WEBHOOK_URL
    HERMES_AGENT_URL  (e.g. http://localhost:8080)
    DISCORD_WEBHOOK_URL
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import requests

LOG = logging.getLogger("architect.embodied_bridge")


@dataclass
class FindingPayload:
    finding_id: str
    title: str
    severity: str            # P1 | P2 | P3 | P4 | P5
    cwe: str
    repo: str
    file_path: str
    description: str
    proof_of_concept: str
    acts_score: float
    discovered_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    extra: dict[str, Any] = field(default_factory=dict)


def _post(url: str, payload: dict[str, Any], *, timeout: int = 8) -> bool:
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        ok = 200 <= r.status_code < 300
        if not ok:
            LOG.warning("EmbodiedOS POST %s → %s", url, r.status_code)
        return ok
    except Exception as exc:  # noqa: BLE001
        LOG.warning("EmbodiedOS POST %s failed: %s", url, exc)
        return False


def _telegram(msg: str) -> bool:
    tok = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not tok or not chat:
        return False
    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    return _post(url, {"chat_id": chat, "text": msg, "parse_mode": "Markdown"})


def _discord(msg: str) -> bool:
    url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        return False
    return _post(url, {"content": msg})


def _format_for_humans(f: FindingPayload) -> str:
    return (
        f"*🛡 ARCHITECT — new finding ({f.severity})*\n"
        f"*{f.title}*\n"
        f"`{f.repo}` · `{f.file_path}` · CWE-{f.cwe}\n"
        f"ACTS: `{f.acts_score:.2f}` · ID: `{f.finding_id}`\n\n"
        f"{f.description[:600]}"
    )


def emit_finding(f: FindingPayload) -> dict[str, bool]:
    """Fan-out a finding to every wired channel. Returns per-channel success."""
    results: dict[str, bool] = {}
    msg = _format_for_humans(f)

    results["telegram"] = _telegram(msg)
    results["discord"]  = _discord(msg)

    openclaw = os.getenv("OPENCLAW_WEBHOOK_URL", "")
    if openclaw:
        results["openclaw"] = _post(openclaw, {
            "type": "architect.finding", "data": asdict(f),
        })

    hermes = os.getenv("HERMES_AGENT_URL", "")
    if hermes:
        results["hermes"] = _post(
            hermes.rstrip("/") + "/v1/skill/extract",
            {"source": "architect", "finding": asdict(f)},
        )

    LOG.info("Finding %s fanned out: %s", f.finding_id, results)
    return results


def emit_status(message: str, level: str = "info") -> bool:
    """Fire a free-form operator notice (start of nightly run, errors, etc.)."""
    msg = f"_ARCHITECT [{level.upper()}]_ — {message}"
    a = _telegram(msg)
    b = _discord(msg)
    return a or b


def channels() -> dict[str, bool]:
    return {
        "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")),
        "discord":  bool(os.getenv("DISCORD_WEBHOOK_URL")),
        "openclaw": bool(os.getenv("OPENCLAW_WEBHOOK_URL")),
        "hermes":   bool(os.getenv("HERMES_AGENT_URL")),
    }
