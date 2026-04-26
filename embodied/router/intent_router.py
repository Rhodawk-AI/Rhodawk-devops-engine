"""
EmbodiedOS — Intent Router (Section 4.1).

Classifies a natural-language command issued through *any* channel
(Telegram, Discord, Slack, WhatsApp, Gradio Web UI, OpenClaw skill call,
direct HTTP webhook) into one of three categories:

  1. ``side1.repo_hunter``       — full Side 1 pipeline on a repo URL.
  2. ``side2.bounty_hunter``     — Side 2 bounty hunt (cycle or program).
  3. ``maintenance.*``           — status / pause / resume / approve / etc.
                                   These re-use the existing
                                   ``openclaw_gateway`` intent registry
                                   verbatim.

Two classification strategies in priority order:

  * **Regex / keyword rules** — fast, deterministic, no model required.
  * **LLM fallback**          — calls the local ``llm_router.classify(...)``
                                 wrapper for ambiguous commands.  Skipped
                                 silently if no LLM endpoint is reachable.

The router never raises in production.  An unmatched command is returned
as ``IntentMatch(name="unknown", confidence=0.0, ...)`` so the caller can
respond with a help message.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable

LOG = logging.getLogger("embodied.router.intent_router")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Intent:
    name: str
    pattern: re.Pattern[str]
    handler: Callable[..., dict[str, Any]] | None
    side: str            # "side1" | "side2" | "maintenance" | "info"
    requires_human: bool = False
    help: str = ""


@dataclass
class IntentMatch:
    name: str
    side: str
    confidence: float
    args: dict[str, Any] = field(default_factory=dict)
    intent: Intent | None = None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class IntentRouter:
    def __init__(self) -> None:
        self._intents: list[Intent] = []
        self._register_defaults()

    # ----- registration ---------------------------------------------------

    def register(
        self,
        *,
        name: str,
        pattern: str,
        side: str,
        handler: Callable[..., dict[str, Any]] | None = None,
        requires_human: bool = False,
        help: str = "",
    ) -> None:
        self._intents.append(Intent(
            name=name,
            pattern=re.compile(pattern, re.I | re.S),
            handler=handler,
            side=side,
            requires_human=requires_human,
            help=help or name,
        ))

    def list_intents(self) -> list[dict[str, Any]]:
        return [
            {"name": i.name, "side": i.side, "help": i.help, "requires_human": i.requires_human}
            for i in self._intents
        ]

    # ----- classification --------------------------------------------------

    def classify(self, text: str) -> IntentMatch:
        text = (text or "").strip()
        if not text:
            return IntentMatch(name="unknown", side="info", confidence=0.0)
        for intent in self._intents:
            m = intent.pattern.search(text)
            if m:
                return IntentMatch(
                    name=intent.name,
                    side=intent.side,
                    confidence=0.99,
                    args=m.groupdict() if m.groupdict() else {"raw": text},
                    intent=intent,
                )

        # LLM fallback (best-effort, never crashes)
        guess = _llm_classify(text)
        if guess is not None:
            for intent in self._intents:
                if intent.name == guess["name"]:
                    return IntentMatch(
                        name=intent.name,
                        side=intent.side,
                        confidence=float(guess.get("confidence", 0.6)),
                        args=guess.get("args", {}),
                        intent=intent,
                    )
        return IntentMatch(name="unknown", side="info", confidence=0.0, args={"raw": text})

    # ----- dispatch --------------------------------------------------------

    def dispatch(self, text: str, *, channel: str = "embodied", user: str = "operator") -> dict[str, Any]:
        match = self.classify(text)
        if match.name == "unknown":
            return {
                "ok": True,
                "intent": "unknown",
                "reply": "Sorry, I didn't understand. Try: `mission repo <url>`, `mission bounty cycle`, `status`, or `help`.",
                "available": self.list_intents(),
            }
        if match.intent and match.intent.requires_human:
            return {
                "ok": True,
                "intent": match.name,
                "status": "pending_human_approval",
                "channel": channel,
                "user": user,
                "args": match.args,
                "message": "Operator confirmation required before execution.",
            }
        if match.intent and match.intent.handler is not None:
            try:
                result = match.intent.handler(**match.args)
                return {"ok": True, "intent": match.name, "channel": channel, "user": user, "data": result}
            except Exception as exc:  # noqa: BLE001
                LOG.exception("intent %s handler raised: %s", match.name, exc)
                return {"ok": False, "intent": match.name, "error": repr(exc)}
        # No handler — return a structured "deferred" response (the
        # unified gateway will route this to the appropriate pipeline).
        return {"ok": True, "intent": match.name, "side": match.side, "args": match.args, "deferred": True}

    # ----- defaults --------------------------------------------------------

    def _register_defaults(self) -> None:
        # ── Side 1 — Repo Hunter ──────────────────────────────────────────
        self.register(
            name="side1.repo_hunter",
            pattern=r"^\s*(?:mission\s+repo|repo[\s-]hunt(?:er)?|hunt\s+repo|side\s*1)\s+(?P<repo_url>https?://\S+|\S+/\S+)",
            side="side1",
            help="`mission repo <github-url>` — clone, fix tests, red-team, disclose.",
        )
        self.register(
            name="side1.fix_only",
            pattern=r"^\s*(?:fix\s+repo|tests?\s+fix)\s+(?P<repo_url>https?://\S+|\S+/\S+)",
            side="side1",
            help="`fix repo <url>` — only run the test-fix loop (no red-team).",
        )

        # ── Side 2 — Bounty Hunter ────────────────────────────────────────
        self.register(
            name="side2.bounty_cycle",
            pattern=r"^\s*(?:mission\s+bounty(?:\s+cycle)?|night\s+hunt|side\s*2)\s*$",
            side="side2",
            help="`mission bounty cycle` — one full Side 2 cycle.",
        )
        self.register(
            name="side2.bounty_program",
            pattern=r"^\s*(?:mission\s+bounty|hunt\s+program)\s+(?P<platform>hackerone|h1|bugcrowd|bc|intigriti|int)\s+(?P<program>\S+)",
            side="side2",
            help="`mission bounty <platform> <program>` — full audit of one program.",
        )
        self.register(
            name="side2.scrape",
            pattern=r"^\s*(?:scrape\s+(?:bounty|programs?)|refresh\s+programs?)\s*$",
            side="side2",
            help="`scrape programs` — refresh the live H1/BC/Intigriti index.",
        )

        # ── Maintenance / info — re-use OpenClaw verbatim where possible ──
        self.register(
            name="maintenance.status",
            pattern=r"^\s*(?:status|whatcha\s+doing|brief|mission\s+brief)\s*$",
            side="info",
            help="`status` — current missions, queue depth, model squad health.",
        )
        self.register(
            name="maintenance.pause",
            pattern=r"^\s*pause\s*$",
            side="maintenance",
            help="`pause` — pause all autonomous loops.",
        )
        self.register(
            name="maintenance.resume",
            pattern=r"^\s*resume\s*$",
            side="maintenance",
            help="`resume` — resume autonomous loops.",
        )
        self.register(
            name="maintenance.approve",
            pattern=r"^\s*approve\s+(?P<finding_id>[A-Za-z0-9_\-]+)",
            side="maintenance",
            requires_human=True,
            help="`approve <finding-id>` — release a held disclosure / submission.",
        )
        self.register(
            name="maintenance.reject",
            pattern=r"^\s*reject\s+(?P<finding_id>[A-Za-z0-9_\-]+)",
            side="maintenance",
            help="`reject <finding-id>` — drop a held finding.",
        )
        self.register(
            name="maintenance.explain",
            pattern=r"^\s*explain\s+(?P<finding_id>[A-Za-z0-9_\-]+)",
            side="info",
            help="`explain <finding-id>` — re-render a finding's full report.",
        )
        self.register(
            name="maintenance.help",
            pattern=r"^\s*(?:help|\?|/help)\s*$",
            side="info",
            help="`help` — show every available command.",
        )


# ---------------------------------------------------------------------------
# LLM fallback
# ---------------------------------------------------------------------------


def _llm_classify(text: str) -> dict[str, Any] | None:
    """Best-effort LLM-based classification. Returns None if unavailable."""
    try:
        from llm_router import classify as router_classify  # type: ignore
    except Exception:
        return None
    try:
        return router_classify(text, schema={
            "name": "string",
            "args": "object",
            "confidence": "number",
        })
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_DEFAULT: IntentRouter | None = None


def default_router() -> IntentRouter:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = IntentRouter()
    return _DEFAULT


def classify(text: str) -> IntentMatch:
    return default_router().classify(text)
