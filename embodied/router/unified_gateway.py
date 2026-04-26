"""
EmbodiedOS — Unified Gateway (Section 4.1).

Funnels every inbound channel into a single dispatch point.

Inbound surfaces:

  * ``POST /embodied/command``  — JSON ``{"text": "...", "user": "..."}``.
                                  This is the canonical entry point.
  * ``POST /telegram/webhook``  — Telegram Update payload (parsed).
  * ``POST /discord/webhook``   — Discord interaction payload (parsed).
  * ``POST /slack/events``      — Slack Events API envelope (parsed).
  * ``POST /openclaw/command``  — re-uses the existing
                                  ``openclaw_gateway.handle_command`` so
                                  the legacy intent set still works.
  * ``embodied.router.dispatch`` — direct in-process Python call.

The gateway intentionally **wraps** ``openclaw_gateway`` rather than
replacing it.  Any command that the new EmbodiedOS intent router does
not recognise is forwarded to the legacy gateway, so no behaviour is
lost.

Outbound notifications go through ``embodied.bridge.openclaw_client`` so
operators see EmbodiedOS replies on whichever channel they originally
spoke from.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Callable

from embodied.config import get_config
from embodied.router.intent_router import IntentRouter, default_router

LOG = logging.getLogger("embodied.router.unified_gateway")


# ---------------------------------------------------------------------------
# Channel adapters — pure functions: payload → (text, user, channel_id)
# ---------------------------------------------------------------------------


def _adapt_telegram(payload: dict[str, Any]) -> tuple[str, str, str]:
    msg = payload.get("message") or payload.get("edited_message") or {}
    text = msg.get("text", "")
    chat = msg.get("chat", {}) or {}
    user = (msg.get("from", {}) or {}).get("username", "telegram-user")
    return text, user, f"telegram:{chat.get('id', '')}"


def _adapt_discord(payload: dict[str, Any]) -> tuple[str, str, str]:
    data = payload.get("data") or {}
    text = data.get("name", "") + " " + " ".join(
        str(o.get("value", "")) for o in data.get("options", []) or []
    )
    user = (payload.get("member", {}) or {}).get("nick") or (payload.get("user", {}) or {}).get("username", "discord-user")
    return text.strip(), user, f"discord:{payload.get('channel_id', '')}"


def _adapt_slack(payload: dict[str, Any]) -> tuple[str, str, str]:
    event = payload.get("event") or {}
    text = event.get("text", "")
    user = event.get("user", "slack-user")
    return text, user, f"slack:{event.get('channel', '')}"


def _adapt_openclaw(payload: dict[str, Any]) -> tuple[str, str, str]:
    return payload.get("text", ""), payload.get("user", "openclaw-user"), f"openclaw:{payload.get('skill', 'cli')}"


# ---------------------------------------------------------------------------
# UnifiedGateway
# ---------------------------------------------------------------------------


@dataclass
class UnifiedGateway:
    router: IntentRouter
    pipeline_dispatcher: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None

    # ----- in-process API ------------------------------------------------------

    def dispatch(self, text: str, *, user: str = "operator", channel: str = "embodied") -> dict[str, Any]:
        result = self.router.dispatch(text, channel=channel, user=user)

        # If the intent had no inline handler, route it to a pipeline.
        if result.get("deferred") and self.pipeline_dispatcher is not None:
            try:
                pipeline_resp = self.pipeline_dispatcher(result["intent"], result.get("args") or {})
                result["data"] = pipeline_resp
                result.pop("deferred", None)
            except Exception as exc:  # noqa: BLE001
                LOG.exception("pipeline dispatch failed: %s", exc)
                result["ok"] = False
                result["error"] = repr(exc)

        # Mirror reply on the originating channel via OpenClaw if reachable.
        try:
            from embodied.bridge.openclaw_client import OpenClawClient
            client = OpenClawClient()
            if channel and channel != "embodied":
                client.push_message(channel=channel, text=_summarise(result))
        except Exception:  # noqa: BLE001
            pass

        return result

    def handle(self, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        adapter = {
            "telegram": _adapt_telegram,
            "discord":  _adapt_discord,
            "slack":    _adapt_slack,
            "openclaw": _adapt_openclaw,
        }.get(channel)
        if adapter is None:
            text = payload.get("text", "")
            user = payload.get("user", "operator")
            return self.dispatch(text, user=user, channel=channel)
        text, user, channel_id = adapter(payload)
        # Forward unknown intents to legacy openclaw_gateway, preserving behaviour.
        result = self.dispatch(text, user=user, channel=channel_id)
        if result.get("intent") == "unknown":
            try:
                import openclaw_gateway  # type: ignore
                legacy = openclaw_gateway.handle_command(text, user=user)
                if legacy.get("ok"):
                    return legacy
            except Exception:  # noqa: BLE001
                pass
        return result

    # ----- HTTP transport (single Flask app for every channel) -----------------

    def serve_http(self, host: str, port: int) -> None:
        try:
            from flask import Flask, jsonify, request
        except Exception:
            LOG.error("Flask not installed — UnifiedGateway HTTP transport disabled")
            return

        app = Flask("embodied-gateway")

        @app.get("/healthz")
        def _healthz():  # type: ignore[unused-ignore]
            return jsonify({"ok": True, "service": "embodied-unified-gateway"})

        @app.post("/embodied/command")
        def _cmd():  # type: ignore[unused-ignore]
            body = request.get_json(force=True, silent=True) or {}
            return jsonify(self.dispatch(body.get("text", ""),
                                         user=body.get("user", "operator"),
                                         channel=body.get("channel", "embodied")))

        @app.post("/telegram/webhook")
        def _tg():  # type: ignore[unused-ignore]
            return jsonify(self.handle("telegram", request.get_json(force=True, silent=True) or {}))

        @app.post("/discord/webhook")
        def _dc():  # type: ignore[unused-ignore]
            return jsonify(self.handle("discord", request.get_json(force=True, silent=True) or {}))

        @app.post("/slack/events")
        def _sl():  # type: ignore[unused-ignore]
            payload = request.get_json(force=True, silent=True) or {}
            if payload.get("type") == "url_verification":
                return jsonify({"challenge": payload.get("challenge", "")})
            return jsonify(self.handle("slack", payload))

        @app.post("/openclaw/command")
        def _oc():  # type: ignore[unused-ignore]
            return jsonify(self.handle("openclaw", request.get_json(force=True, silent=True) or {}))

        LOG.info("EmbodiedOS unified gateway listening at http://%s:%s", host, port)
        app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _summarise(result: dict[str, Any]) -> str:
    intent = result.get("intent", "?")
    if not result.get("ok"):
        return f"[EmbodiedOS] ✗ {intent} — {result.get('error') or result.get('reply') or 'failed'}"
    if result.get("status") == "pending_human_approval":
        return f"[EmbodiedOS] ⏸ {intent} — awaiting your approval."
    return f"[EmbodiedOS] ✓ {intent} dispatched."


def _default_pipeline_dispatcher(intent: str, args: dict[str, Any]) -> dict[str, Any]:
    """Map an intent name onto the matching Side 1 / Side 2 pipeline."""
    if intent.startswith("side1.repo_hunter") or intent == "side1.fix_only":
        from embodied.pipelines.repo_hunter import run_repo_hunter
        return run_repo_hunter(repo_url=args["repo_url"], fix_only=intent == "side1.fix_only")
    if intent == "side2.bounty_cycle":
        from embodied.pipelines.bounty_hunter import run_bounty_hunter
        return run_bounty_hunter()
    if intent == "side2.bounty_program":
        from embodied.pipelines.bounty_hunter import scan_bounty_program
        return scan_bounty_program(platform=args["platform"], program=args["program"])
    if intent == "side2.scrape":
        from embodied.pipelines.bounty_hunter import scrape_programs
        return scrape_programs()
    if intent == "campaign.start":
        from embodied.pipelines.campaign_runner import start_campaign_in_background
        stacks_arg = (args.get("stacks") or "").strip()
        stacks = [s for s in stacks_arg.split(",") if s] if stacks_arg else None
        start_campaign_in_background(stacks=stacks, bounty_only=False)
        return {"ok": True, "intent": intent, "started": True, "stacks": stacks or "all"}
    if intent == "campaign.bounty":
        from embodied.pipelines.campaign_runner import start_campaign_in_background
        start_campaign_in_background(bounty_only=True)
        return {"ok": True, "intent": intent, "started": True, "bounty_only": True}
    if intent == "campaign.stop":
        from embodied.pipelines.campaign_runner import request_stop
        request_stop()
        return {"ok": True, "intent": intent, "stop_requested": True}
    if intent == "campaign.reset":
        from embodied.pipelines.campaign_runner import reset_cursor
        reset_cursor()
        return {"ok": True, "intent": intent, "cursor_reset": True}
    if intent == "campaign.status":
        import json as _json, os as _os
        path = _os.getenv("RHODAWK_CAMPAIGN_STATE", "/data/campaign_state.json")
        try:
            with open(path) as fh:
                return {"ok": True, "intent": intent, "state": _json.load(fh)}
        except Exception:
            return {"ok": True, "intent": intent, "state": {"cursor": 0, "completed": []}}
    if intent == "maintenance.status":
        from embodied.pipelines.bounty_hunter import status as side2_status
        from embodied.pipelines.repo_hunter import status as side1_status
        return {"side1": side1_status(), "side2": side2_status()}
    return {"ok": False, "reason": "no_pipeline_for_intent", "intent": intent}


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def build_gateway(router: IntentRouter | None = None) -> UnifiedGateway:
    return UnifiedGateway(
        router=router or default_router(),
        pipeline_dispatcher=_default_pipeline_dispatcher,
    )


def serve_in_background(host: str | None = None, port: int | None = None) -> threading.Thread:
    cfg = get_config().bridge
    gw = build_gateway()
    t = threading.Thread(
        target=gw.serve_http,
        args=(host or cfg.host, (port or cfg.port) + 1),  # +1 keeps it on a separate port
        name="embodied-unified-gateway-http",
        daemon=True,
    )
    t.start()
    return t


def dispatch(text: str, *, user: str = "operator", channel: str = "embodied") -> dict[str, Any]:
    return build_gateway().dispatch(text, user=user, channel=channel)
