"""
Rhodawk AI — OpenClaw / Telegram gateway (Masterplan §6 EmbodiedOS).

A small, self-contained HTTP + Telegram bridge that lets the operator talk
to Rhodawk in natural language from anywhere:

    Telegram message      ──┐
    Slack /command        ──┤
    OpenClaw skill call   ──┴──►  parse intent  ──►  dispatch to:
                                                      • OSSGuardian.run(repo)
                                                      • night_hunt_orchestrator
                                                      • status / pause / resume
                                                      • approve / reject finding
                                                      • explain finding

Public surface:

    handle_command(text, *, user="operator") -> dict
        Pure function. Parses ``text`` into an intent and executes it.
        Returns {"ok": bool, "intent": str, "reply": str, "data": ...}.

    create_app() -> flask.Flask
        FastAPI/Flask-compatible app exposing:
            POST /openclaw/command   {"text": "..."}        → handle_command
            POST /telegram/webhook   Telegram Update payload → handle_command
            GET  /openclaw/status                            → liveness JSON

    start_in_background(host="0.0.0.0", port=8765) -> Thread
        Convenience: starts the Flask server in a daemon thread.

The module degrades gracefully when neither Flask nor python-telegram-bot
is installed: ``handle_command`` always works (no IO), and ``create_app``
returns ``None`` with a logged warning.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from typing import Any, Callable

LOG = logging.getLogger("rhodawk.openclaw_gateway")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
OPENCLAW_SHARED_SECRET = os.getenv("OPENCLAW_SHARED_SECRET", "")

# ── intent registry ────────────────────────────────────────────────────────
@dataclass
class Intent:
    name: str
    pattern: re.Pattern[str]
    handler: Callable[[re.Match[str]], dict[str, Any]]
    help: str


_INTENTS: list[Intent] = []


def register(name: str, pattern: str, *, help: str = "") -> Callable[[Callable], Callable]:
    def deco(fn: Callable[[re.Match[str]], dict[str, Any]]) -> Callable:
        _INTENTS.append(Intent(name=name, pattern=re.compile(pattern, re.I),
                               handler=fn, help=help or name))
        return fn
    return deco


# ── handler implementations ─────────────────────────────────────────────────
@register(
    "scan_repo",
    r"^\s*(?:scan(?:\s+repo)?|audit)\s+(?P<target>\S+)",
    help="scan <repo-url-or-org/name> — queue an OSS Guardian scan",
)
def _scan_repo(m: re.Match[str]) -> dict[str, Any]:
    target = m.group("target").strip()
    try:
        from oss_guardian import OSSGuardian
        camp = OSSGuardian().run(target)
        return {
            "ok": True,
            "intent": "scan_repo",
            "reply": f"Scan queued for {target}. Mode={camp.mode}, "
                     f"findings={len(camp.findings)}.",
            "data": {"repo": target, "mode": camp.mode,
                     "findings": len(camp.findings)},
        }
    except Exception as exc:  # noqa: BLE001
        LOG.exception("scan_repo failed: %s", exc)
        return {"ok": False, "intent": "scan_repo",
                "reply": f"Scan failed: {exc}", "data": None}


@register(
    "night_run_now",
    r"^\s*(?:night\s+(?:run|hunt)|run\s+night|hunt\s+now)\b",
    help="night run — execute one Night Hunter cycle immediately",
)
def _night_now(_: re.Match[str]) -> dict[str, Any]:
    try:
        import night_hunt_orchestrator as nh
        rep = nh.run_night_cycle()
        return {"ok": True, "intent": "night_run_now",
                "reply": f"Night cycle {rep.cycle_id} done. "
                         f"{len(rep.findings)} findings across "
                         f"{len(rep.targets)} targets.",
                "data": rep.summary()}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "intent": "night_run_now",
                "reply": f"Night run failed: {exc}", "data": None}


@register(
    "pause_night",
    r"^\s*(?:pause|stop)\s+(?:night|hunting|hunt)\b",
    help="pause night — disable tonight's hunt cycle",
)
def _pause_night(_: re.Match[str]) -> dict[str, Any]:
    os.environ["NIGHT_HUNTER_PAUSED"] = "1"
    return {"ok": True, "intent": "pause_night",
            "reply": "Night Hunter paused. Resume with 'resume night'.",
            "data": {"paused": True}}


@register(
    "resume_night",
    r"^\s*(?:resume|start)\s+(?:night|hunting|hunt)\b",
    help="resume night — re-enable hunt cycle",
)
def _resume_night(_: re.Match[str]) -> dict[str, Any]:
    os.environ.pop("NIGHT_HUNTER_PAUSED", None)
    return {"ok": True, "intent": "resume_night",
            "reply": "Night Hunter resumed.",
            "data": {"paused": False}}


@register(
    "status",
    r"^\s*(?:status|what(?:'s|\s+is)?\s+up|what\s+are\s+you\s+doing)\b",
    help="status — show what Rhodawk is working on right now",
)
def _status(_: re.Match[str]) -> dict[str, Any]:
    info: dict[str, Any] = {"version": "rhodawk-v5"}
    try:
        import job_queue  # type: ignore
        if hasattr(job_queue, "snapshot"):
            info["jobs"] = job_queue.snapshot()
    except Exception:  # noqa: BLE001
        pass
    try:
        from architect import skill_selector
        info["skills"] = skill_selector.stats()
    except Exception:  # noqa: BLE001
        pass
    info["paused"] = bool(os.getenv("NIGHT_HUNTER_PAUSED"))
    return {"ok": True, "intent": "status",
            "reply": _format_status(info), "data": info}


def _format_status(info: dict[str, Any]) -> str:
    lines = ["Rhodawk status:"]
    if "skills" in info:
        s = info["skills"]
        lines.append(f"  skills: {s.get('total_skills', '?')} loaded ({s.get('engine', '?')})")
    if info.get("paused"):
        lines.append("  night-hunt: PAUSED")
    else:
        lines.append("  night-hunt: armed")
    if "jobs" in info:
        lines.append(f"  jobs: {info['jobs']}")
    return "\n".join(lines)


@register(
    "approve_finding",
    r"^\s*approve\s+(?:finding\s+)?(?P<id>[a-zA-Z0-9_-]+)\b",
    help="approve <id> — submit a queued finding to its bounty platform",
)
def _approve_finding(m: re.Match[str]) -> dict[str, Any]:
    fid = m.group("id")
    try:
        import bounty_gateway  # type: ignore
        if hasattr(bounty_gateway, "submit_finding"):
            res = bounty_gateway.submit_finding(fid)  # type: ignore[attr-defined]
            return {"ok": True, "intent": "approve_finding",
                    "reply": f"Finding {fid} submitted.",
                    "data": res}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "intent": "approve_finding",
                "reply": f"Submission failed: {exc}", "data": None}
    return {"ok": False, "intent": "approve_finding",
            "reply": "bounty_gateway.submit_finding not available — "
                     "operator must submit manually for now.",
            "data": {"finding_id": fid}}


@register(
    "reject_finding",
    r"^\s*reject\s+(?:finding\s+)?(?P<id>[a-zA-Z0-9_-]+)\b",
    help="reject <id> — drop the finding (becomes a negative training signal)",
)
def _reject_finding(m: re.Match[str]) -> dict[str, Any]:
    fid = m.group("id")
    try:
        import training_store  # type: ignore
        if hasattr(training_store, "record_negative"):
            training_store.record_negative(fid)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        LOG.debug("training_store negative record failed: %s", exc)
    return {"ok": True, "intent": "reject_finding",
            "reply": f"Finding {fid} rejected. Logged for negative training.",
            "data": {"finding_id": fid}}


@register(
    "explain_finding",
    r"^\s*explain\s+(?:finding\s+)?(?P<id>[a-zA-Z0-9_-]+)\b",
    help="explain <id> — plain-English description of a finding",
)
def _explain_finding(m: re.Match[str]) -> dict[str, Any]:
    fid = m.group("id")
    payload: dict[str, Any] | None = None
    try:
        from pathlib import Path
        for p in Path(os.getenv("NIGHT_HUNTER_REPORTS", "/data/night_reports")).glob("*.json"):
            data = json.loads(p.read_text())
            for f in data.get("findings", []):
                if f.get("id") == fid:
                    payload = f
                    break
            if payload:
                break
    except Exception as exc:  # noqa: BLE001
        LOG.debug("explain lookup failed: %s", exc)
    if not payload:
        return {"ok": False, "intent": "explain_finding",
                "reply": f"No finding with id={fid} on record.", "data": None}
    txt = (
        f"{payload.get('title')} on {payload.get('target')} "
        f"(severity={payload.get('severity')}, CVSS={payload.get('cvss')}). "
        f"{payload.get('description', '')[:400]}"
    )
    return {"ok": True, "intent": "explain_finding",
            "reply": txt, "data": payload}


@register(
    "help",
    r"^\s*(?:help|\?|commands)\b",
    help="help — list available commands",
)
def _help(_: re.Match[str]) -> dict[str, Any]:
    lines = ["Available commands:"]
    for it in _INTENTS:
        lines.append(f"  • {it.help}")
    return {"ok": True, "intent": "help", "reply": "\n".join(lines), "data": None}


# ── core dispatcher ─────────────────────────────────────────────────────────
def handle_command(text: str, *, user: str = "operator") -> dict[str, Any]:
    """Match a freeform command to an intent and execute its handler."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "intent": "noop",
                "reply": "Empty command.", "data": None}
    for it in _INTENTS:
        m = it.pattern.match(text)
        if m:
            LOG.info("openclaw cmd from %s → %s", user, it.name)
            try:
                return it.handler(m)
            except Exception as exc:  # noqa: BLE001
                LOG.exception("intent %s crashed: %s", it.name, exc)
                return {"ok": False, "intent": it.name,
                        "reply": f"Handler crashed: {exc}", "data": None}
    return {"ok": False, "intent": "unknown",
            "reply": "Unrecognised command. Try 'help'.",
            "data": {"text": text}}


# ── outbound Telegram ───────────────────────────────────────────────────────
def telegram_send(text: str, *, chat_id: str | None = None) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        LOG.debug("telegram_send: TELEGRAM_BOT_TOKEN not configured")
        return False
    cid = chat_id or TELEGRAM_CHAT_ID
    if not cid:
        LOG.debug("telegram_send: no chat id")
        return False
    try:
        import requests  # type: ignore
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": cid, "text": text[:4000]},
            timeout=8,
        )
        return r.status_code == 200
    except Exception as exc:  # noqa: BLE001
        LOG.warning("telegram_send failed: %s", exc)
        return False


# ── HTTP gateway (Flask) ────────────────────────────────────────────────────
def create_app():
    """Returns a Flask app or ``None`` if Flask is not available."""
    try:
        from flask import Flask, request, jsonify  # type: ignore
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Flask unavailable — gateway HTTP disabled (%s)", exc)
        return None

    app = Flask("rhodawk_openclaw_gateway")

    @app.get("/openclaw/status")
    def _status_route():
        try:
            from architect import skill_selector
            stats = skill_selector.stats()
        except Exception:  # noqa: BLE001
            stats = {}
        return jsonify({"ok": True, "service": "rhodawk-openclaw",
                        "intents": [i.name for i in _INTENTS],
                        "skills": stats})

    @app.post("/openclaw/command")
    def _cmd_route():
        if OPENCLAW_SHARED_SECRET and \
           request.headers.get("X-OpenClaw-Token") != OPENCLAW_SHARED_SECRET:
            return jsonify({"ok": False, "reply": "unauthorized"}), 401
        body = request.get_json(silent=True) or {}
        return jsonify(handle_command(str(body.get("text", "")),
                                      user=str(body.get("user", "openclaw"))))

    @app.post("/telegram/webhook")
    def _tg_route():
        update = request.get_json(silent=True) or {}
        msg = (update.get("message") or {}).get("text", "")
        chat = ((update.get("message") or {}).get("chat") or {}).get("id")
        result = handle_command(msg, user=f"telegram:{chat}")
        if chat:
            telegram_send(result.get("reply") or "(no reply)", chat_id=str(chat))
        return jsonify(result)

    return app


_THREAD: threading.Thread | None = None


def start_in_background(host: str = "0.0.0.0", port: int = 8765) -> threading.Thread | None:
    global _THREAD
    if _THREAD and _THREAD.is_alive():
        return _THREAD
    app = create_app()
    if app is None:
        return None
    def _run() -> None:
        try:
            app.run(host=host, port=port, debug=False, use_reloader=False)
        except Exception as exc:  # noqa: BLE001
            LOG.exception("openclaw gateway crashed: %s", exc)
    _THREAD = threading.Thread(target=_run, name="openclaw-gateway", daemon=True)
    _THREAD.start()
    LOG.info("openclaw gateway listening on %s:%d", host, port)
    return _THREAD


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    import sys
    cmd = " ".join(sys.argv[1:]) or "help"
    print(json.dumps(handle_command(cmd), indent=2))
