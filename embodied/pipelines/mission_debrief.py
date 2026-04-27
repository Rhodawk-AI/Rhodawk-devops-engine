"""
EmbodiedOS — Autonomous Mission Debrief generator (Playbook §4).

At the end of every Side-1 (repo_hunter) and Side-2 (bounty_hunter)
mission, render a structured Markdown narrative report and (best-effort)
upload it to the Telegram / OpenClaw chat as an investor-ready debrief.

The report is saved to ``/data/vault/MISSION_REPORT_<job_id_hash>.md`` so
it survives container restarts and can be snapshotted alongside the
Hermes memory.

The timeline section is reconstructed from the mission's ``notes`` list
and any fields the pipeline already populates (cloning, env meta-healing,
logic patching via OpenClaude, SAST checks, PR submission, etc.).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

LOG = logging.getLogger("embodied.pipelines.mission_debrief")

VAULT_DIR = Path(os.getenv("EMBODIED_VAULT_DIR", "/data/vault"))


# ──────────────────────────────────────────────────────────────────────
# Markdown rendering
# ──────────────────────────────────────────────────────────────────────


def _hash_id(mission_id: str) -> str:
    return hashlib.blake2s(mission_id.encode("utf-8"), digest_size=6).hexdigest()


def _ts(epoch: float | None) -> str:
    if not epoch:
        return "—"
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(epoch))


def _bucket_notes(notes: list[str]) -> dict[str, list[str]]:
    """Group the mission's free-form notes into the 5 timeline phases the
    investor debrief expects."""
    buckets: dict[str, list[str]] = {
        "cloning":            [],
        "env_meta_healing":   [],
        "logic_patching":     [],
        "sast_checks":        [],
        "pr_submission":      [],
        "other":              [],
    }
    for n in notes or []:
        low = n.lower()
        if any(k in low for k in ("clone", "cloned", "git clone", "deploy_target")):
            buckets["cloning"].append(n)
        elif any(k in low for k in ("meta-heal", "pre-flight", "collection error",
                                     "setup_env", "uv pip", "venv", "requirements")):
            buckets["env_meta_healing"].append(n)
        elif any(k in low for k in ("hermes", "openclaude", "openclaw", "fix iteration",
                                     "fix_only", "patch", "aider", "skill")):
            buckets["logic_patching"].append(n)
        elif any(k in low for k in ("sast", "taint", "symbolic", "fuzz", "red_team",
                                     "chain_analyzer", "bandit", "semgrep")):
            buckets["sast_checks"].append(n)
        elif any(k in low for k in ("pr", "pull request", "submission", "submit",
                                     "disclosure", "vault")):
            buckets["pr_submission"].append(n)
        else:
            buckets["other"].append(n)
    return buckets


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}\n"


def render_mission_report(mission: Any, *, side: str) -> str:
    """Render a Markdown debrief from a Side-1 or Side-2 mission object.

    ``side`` is the human label ("Side 1 — Repo Hunter" or
    "Side 2 — Bounty Hunter"). The mission object only needs
    ``mission_id``, ``notes``, ``started_at``, ``finished_at`` and any
    side-specific fields it already exposes.
    """
    mission_id   = getattr(mission, "mission_id", "unknown")
    started_at   = getattr(mission, "started_at", None)
    finished_at  = getattr(mission, "finished_at", None) or time.time()
    status       = getattr(mission, "status", "unknown")
    notes        = list(getattr(mission, "notes", []) or [])
    findings     = list(getattr(mission, "findings", []) or [])

    # Side-specific extras (defensive)
    repo_url     = getattr(mission, "repo_url", None)
    runtime      = getattr(mission, "runtime", None)
    fix_iters    = getattr(mission, "fix_iterations", None)
    init_red     = getattr(mission, "failing_tests_initial", None)
    final_red    = getattr(mission, "failing_tests_final", None)
    pr_url       = getattr(mission, "pr_url", None)
    zero_days    = list(getattr(mission, "zero_days", []) or [])
    platform     = getattr(mission, "platform", None)
    program      = getattr(mission, "program", None)
    score        = getattr(mission, "score", None)
    held         = list(getattr(mission, "held_for_review", []) or [])
    submitted    = list(getattr(mission, "submitted", []) or [])

    duration_s = max(0.0, (finished_at or time.time()) - (started_at or finished_at or time.time()))
    buckets = _bucket_notes(notes)

    lines: list[str] = []
    lines.append(f"# Mission Debrief — {side}\n")
    lines.append(f"_Investor-ready autonomous report. Generated: {_ts(time.time())}._\n")
    lines.append("")
    lines.append("## Mission Summary\n")
    lines.append(f"- **Mission ID:** `{mission_id}`")
    lines.append(f"- **Status:** `{status}`")
    lines.append(f"- **Started:** {_ts(started_at)}")
    lines.append(f"- **Finished:** {_ts(finished_at)}")
    lines.append(f"- **Duration:** {duration_s:.1f} s")
    if repo_url:
        lines.append(f"- **Repository:** {repo_url}")
    if runtime:
        lines.append(f"- **Runtime detected:** `{runtime}`")
    if platform or program:
        lines.append(f"- **Bounty target:** `{platform}/{program}`")
        if score is not None:
            lines.append(f"- **Program score:** `{score}`")
    lines.append(f"- **Findings:** `{len(findings)}`")
    if zero_days:
        lines.append(f"- **Zero-days held in vault:** `{len(zero_days)}`")
    if held:
        lines.append(f"- **Held for human review:** `{len(held)}`")
    if submitted:
        lines.append(f"- **Auto-submitted:** `{len(submitted)}`")
    lines.append("")

    # Timeline
    timeline_blocks = []
    phase_labels = [
        ("cloning",          "1. Cloning"),
        ("env_meta_healing", "2. Environment meta-healing"),
        ("logic_patching",   "3. Logic patching via OpenClaude"),
        ("sast_checks",      "4. SAST / taint / symbolic checks"),
        ("pr_submission",    "5. PR / disclosure submission"),
    ]
    for key, label in phase_labels:
        items = buckets.get(key) or []
        if not items:
            timeline_blocks.append(f"### {label}\n\n_No telemetry recorded for this phase._\n")
            continue
        body = "\n".join(f"- {n}" for n in items)
        timeline_blocks.append(f"### {label}\n\n{body}\n")
    lines.append(_section("Timeline", "\n".join(timeline_blocks)))

    # Patching / verification stats (Side 1 only)
    if init_red is not None or final_red is not None or fix_iters is not None:
        body = (
            f"- **Failing tests at start:** `{init_red if init_red is not None else '—'}`\n"
            f"- **Failing tests at end:** `{final_red if final_red is not None else '—'}`\n"
            f"- **Fix iterations consumed:** `{fix_iters if fix_iters is not None else '—'}`"
        )
        lines.append(_section("Verification Loop", body))

    # Findings table
    if findings:
        rows = ["| Severity | Source | Title |", "| --- | --- | --- |"]
        for f in findings[:25]:
            sev = (f.get("severity") if isinstance(f, dict) else "P3") or "P3"
            src = (f.get("source") if isinstance(f, dict) else "?") or "?"
            ttl = (f.get("title")  if isinstance(f, dict) else str(f))[:80]
            rows.append(f"| `{sev}` | `{src}` | {ttl} |")
        if len(findings) > 25:
            rows.append(f"| … | … | _{len(findings) - 25} more findings — see vault payload_ |")
        lines.append(_section("Findings", "\n".join(rows)))

    # Zero-days
    if zero_days:
        body = "\n".join(
            f"- `{(z or {}).get('finding_id') or (z or {}).get('id') or '—'}` "
            f"→ vault id `{(z or {}).get('vault_id') or '—'}`"
            for z in zero_days
        )
        lines.append(_section("Zero-Days (Operator Approval Required)", body))

    # PR / submission outcomes
    pr_lines: list[str] = []
    if pr_url:
        pr_lines.append(f"- **Primary PR opened:** {pr_url}")
    for f in findings:
        if isinstance(f, dict) and f.get("pr_url"):
            pr_lines.append(f"- `{f.get('id')}` → {f['pr_url']}")
    for s in submitted:
        if isinstance(s, dict) and s.get("url"):
            pr_lines.append(f"- Submitted: {s['url']}")
    if pr_lines:
        lines.append(_section("Submissions & Pull Requests", "\n".join(pr_lines)))

    # Held-for-review (Side 2)
    if held:
        body = "\n".join(
            f"- `{h.get('finding_id', '?')}` ({h.get('severity', '?')}) — {h.get('title', 'untitled')}"
            for h in held if isinstance(h, dict)
        )
        lines.append(_section("Held for Human Approval", body))

    # Other notes
    if buckets.get("other"):
        lines.append(_section("Additional Telemetry", "\n".join(f"- {n}" for n in buckets["other"])))

    # Footer
    lines.append("\n---\n")
    lines.append("_Generated autonomously by the Rhodawk EmbodiedOS DevSecOps Engine._")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# Persistence + delivery
# ──────────────────────────────────────────────────────────────────────


def write_mission_report(markdown: str, *, mission_id: str) -> Path:
    """Persist the Markdown debrief under /data/vault."""
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    path = VAULT_DIR / f"MISSION_REPORT_{_hash_id(mission_id)}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def upload_debrief(report_path: Path, *, caption: str) -> dict[str, Any]:
    """Best-effort upload to Telegram (and the OpenClaw bridge if wired).

    Returns ``{"ok": True, "channels": [...]}`` on success and never
    raises — debriefs must never break the mission finish path.
    """
    delivered: list[str] = []
    errors: list[str] = []

    # ── Telegram (sendDocument) ───────────────────────────────────────
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if token and chat_id and report_path.exists():
        try:
            import requests  # local import — keep notifier-free dependency surface
            with report_path.open("rb") as fh:
                resp = requests.post(
                    f"https://api.telegram.org/bot{token}/sendDocument",
                    data={
                        "chat_id": chat_id,
                        "caption": caption[:1024],
                        "parse_mode": "Markdown",
                    },
                    files={"document": (report_path.name, fh, "text/markdown")},
                    timeout=20,
                )
            if resp.ok:
                delivered.append("telegram")
            else:
                errors.append(f"telegram:{resp.status_code}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"telegram:{exc!r}")

    # ── OpenClaw bridge (best-effort, optional) ───────────────────────
    try:
        from embodied.bridge import openclaw_client  # type: ignore
        if hasattr(openclaw_client, "upload_document"):
            try:
                openclaw_client.upload_document(
                    path=str(report_path),
                    caption=caption,
                )
                delivered.append("openclaw")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"openclaw:{exc!r}")
    except Exception:
        pass

    return {"ok": bool(delivered), "channels": delivered, "errors": errors}


def emit_mission_debrief(mission: Any, *, side: str) -> dict[str, Any]:
    """Render → persist → upload. Used by both Side-1 and Side-2 pipelines.

    Returns a JSON-able status dict; never raises.
    """
    try:
        markdown = render_mission_report(mission, side=side)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("mission_debrief render failed: %s", exc)
        return {"ok": False, "stage": "render", "error": repr(exc)}

    try:
        path = write_mission_report(markdown, mission_id=getattr(mission, "mission_id", "unknown"))
    except Exception as exc:  # noqa: BLE001
        LOG.warning("mission_debrief write failed: %s", exc)
        return {"ok": False, "stage": "write", "error": repr(exc)}

    caption = (
        f"*Rhodawk EmbodiedOS — {side}*\n"
        f"Mission `{getattr(mission, 'mission_id', '?')}` → "
        f"`{getattr(mission, 'status', '?')}`"
    )
    upload_status = upload_debrief(path, caption=caption)

    return {
        "ok": True,
        "report_path": str(path),
        "upload": upload_status,
        "bytes": path.stat().st_size,
    }


__all__ = [
    "render_mission_report",
    "write_mission_report",
    "upload_debrief",
    "emit_mission_debrief",
]
