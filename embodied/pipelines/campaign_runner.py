"""
EmbodiedOS — Continuous Campaign Runner.

Round-robins the curated high-value-target list, runs ``run_repo_hunter``
on each target inside the sandbox, stages every finding behind the
human-approval gate, and persists campaign progress so a restart
resumes where it left off.

The runner exists so the operator can issue ONE short command
("go hunt" / "start campaign") and walk away — the system then grinds
through the top OSS projects autonomously, leaving a morning report of
PR drafts, dossier-staged zero-days with maintainer-email candidates,
and bounty submissions awaiting click-to-send.

Hard limits:
  * Per-target wall-clock budget (default 30 min) so a single repo
    can't stall the loop.
  * Concurrent-target cap (default 1 — most analysers are CPU-heavy).
  * Stop-flag honoured between targets.
  * Every finding stays gated behind the disclosure_vault human gate.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from embodied.bridge.role_prompts import CAMPAIGN_PRIME  # imported for parity / future Hermes drive
from embodied.config import get_config
from embodied.memory.unified_memory import get_memory
from embodied.pipelines.repo_hunter import run_repo_hunter
from embodied.targets.high_value_repos import ALL_TARGETS, Target

LOG = logging.getLogger("embodied.pipelines.campaign_runner")

CAMPAIGN_STATE = Path(os.getenv("RHODAWK_CAMPAIGN_STATE", "/data/campaign_state.json"))
DEFAULT_TARGET_BUDGET_S = int(os.getenv("RHODAWK_TARGET_BUDGET_S", "1800"))   # 30 min
DEFAULT_CYCLE_PAUSE_S   = int(os.getenv("RHODAWK_CYCLE_PAUSE_S", "60"))        # 1 min between
DEFAULT_MAX_TARGETS     = int(os.getenv("RHODAWK_MAX_TARGETS",   "0"))         # 0 = no limit


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


@dataclass
class CampaignReport:
    started_at:      float = field(default_factory=time.time)
    finished_at:     float | None = None
    targets_run:     int   = 0
    targets_skipped: int   = 0
    findings_total:  int   = 0
    zero_days_total: int   = 0
    pr_drafts_total: int   = 0
    notes:           list[str] = field(default_factory=list)
    per_target:      list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at":      self.started_at,
            "finished_at":     self.finished_at,
            "targets_run":     self.targets_run,
            "targets_skipped": self.targets_skipped,
            "findings_total":  self.findings_total,
            "zero_days_total": self.zero_days_total,
            "pr_drafts_total": self.pr_drafts_total,
            "notes":           self.notes,
            "per_target":      self.per_target,
        }


def _load_state() -> dict[str, Any]:
    try:
        return json.loads(CAMPAIGN_STATE.read_text())
    except Exception:
        return {"cursor": 0, "completed": [], "stop_requested": False}


def _save_state(state: dict[str, Any]) -> None:
    try:
        CAMPAIGN_STATE.parent.mkdir(parents=True, exist_ok=True)
        CAMPAIGN_STATE.write_text(json.dumps(state, indent=2))
    except Exception as exc:  # noqa: BLE001
        LOG.warning("could not persist campaign state: %s", exc)


def request_stop() -> None:
    """Operator-facing: ask the running campaign to stop after the current target."""
    state = _load_state()
    state["stop_requested"] = True
    _save_state(state)


def reset_cursor() -> None:
    state = _load_state()
    state["cursor"] = 0
    state["completed"] = []
    state["stop_requested"] = False
    _save_state(state)


# ---------------------------------------------------------------------------
# Target selection
# ---------------------------------------------------------------------------


def _resolve_targets(
    *,
    targets: Iterable[Target] | None,
    stacks:  Iterable[str]    | None,
    bounty_only: bool,
) -> list[Target]:
    if targets:
        return list(targets)
    pool = list(ALL_TARGETS)
    if stacks:
        wanted = {s.lower() for s in stacks}
        pool = [t for t in pool if any(s in wanted for s in t.stack)]
    if bounty_only:
        pool = [t for t in pool if t.bounty]
    return pool


# ---------------------------------------------------------------------------
# Per-target runner with wall-clock budget
# ---------------------------------------------------------------------------


def _run_target_with_budget(target: Target, budget_s: int) -> dict[str, Any]:
    """Run one repo_hunter pass with a watchdog-enforced wall-clock budget."""
    result_box: dict[str, Any] = {"ok": False, "reason": "not_started"}

    def _go() -> None:
        try:
            out = run_repo_hunter(repo_url=target.url, fix_only=False)
            result_box.update({"ok": True, "report": out})
        except Exception as exc:  # noqa: BLE001
            result_box.update({"ok": False, "reason": "exception", "exception": repr(exc)})

    th = threading.Thread(target=_go, name=f"hunter-{target.name}", daemon=True)
    started = time.time()
    th.start()
    th.join(timeout=budget_s)
    elapsed = time.time() - started
    if th.is_alive():
        # Watchdog tripped — we let the daemon thread continue but record a timeout.
        return {
            "ok":      False,
            "reason":  "timeout",
            "elapsed": elapsed,
            "target":  target.name,
        }
    result_box["elapsed"] = elapsed
    result_box["target"]  = target.name
    return result_box


# ---------------------------------------------------------------------------
# Public entrypoints
# ---------------------------------------------------------------------------


def run_campaign(
    *,
    targets:         Iterable[Target] | None = None,
    stacks:          Iterable[str]    | None = None,
    bounty_only:     bool             = False,
    target_budget_s: int              = DEFAULT_TARGET_BUDGET_S,
    cycle_pause_s:   int              = DEFAULT_CYCLE_PAUSE_S,
    max_targets:     int              = DEFAULT_MAX_TARGETS,
    resume:          bool             = True,
) -> CampaignReport:
    """Run the continuous campaign synchronously and return a report.

    The function never raises in production — every per-target failure
    is captured in the report so the loop continues to the next target.
    """
    pool = _resolve_targets(targets=targets, stacks=stacks, bounty_only=bounty_only)
    if not pool:
        report = CampaignReport()
        report.notes.append("No targets matched the supplied filters.")
        report.finished_at = time.time()
        return report

    state = _load_state() if resume else {"cursor": 0, "completed": [], "stop_requested": False}
    state["stop_requested"] = False
    _save_state(state)

    report = CampaignReport()
    LOG.info("Campaign starting — pool=%d budget/target=%ds resume_cursor=%d",
             len(pool), target_budget_s, state.get("cursor", 0))

    try:
        memory = get_memory()
    except Exception:  # noqa: BLE001
        memory = None

    cursor = state.get("cursor", 0) % len(pool)
    completed = set(state.get("completed", []))
    processed_this_run = 0

    while True:
        # Re-read stop flag every iteration so it can be set out-of-band.
        latest = _load_state()
        if latest.get("stop_requested"):
            report.notes.append("Stop flag honoured — exiting cleanly.")
            break
        if max_targets and processed_this_run >= max_targets:
            report.notes.append(f"Reached max_targets={max_targets}.")
            break

        target = pool[cursor]
        if target.name in completed and resume:
            # Already done this pass — advance cursor and continue.
            cursor = (cursor + 1) % len(pool)
            if cursor == state.get("cursor", 0):
                report.notes.append("Full lap completed; stopping.")
                break
            continue

        LOG.info("Campaign target %d/%d → %s", cursor + 1, len(pool), target.name)
        per = _run_target_with_budget(target, target_budget_s)
        per["category"] = target.category
        per["stack"]    = list(target.stack)
        per["bounty"]   = target.bounty

        if per.get("ok"):
            rep = per.get("report") or {}
            findings = rep.get("findings") if isinstance(rep, dict) else None
            zerodays = rep.get("zero_days") if isinstance(rep, dict) else None
            prs      = rep.get("pr_drafts") if isinstance(rep, dict) else None
            report.findings_total  += len(findings or [])
            report.zero_days_total += len(zerodays or [])
            report.pr_drafts_total += len(prs or [])
            report.targets_run     += 1
        else:
            report.targets_skipped += 1

        report.per_target.append(per)
        completed.add(target.name)

        # Persist after every target so a crash resumes cleanly.
        cursor = (cursor + 1) % len(pool)
        _save_state({
            "cursor":         cursor,
            "completed":      sorted(completed),
            "stop_requested": False,
            "last_target":    target.name,
            "last_at":        time.time(),
        })

        if memory is not None:
            try:
                memory.remember_episode(
                    summary=f"campaign:{target.name}:{'ok' if per.get('ok') else per.get('reason')}",
                    metadata={"per_target": per, "campaign_run_so_far": report.to_dict()},
                )
            except Exception:  # noqa: BLE001
                pass

        processed_this_run += 1

        if cursor == state.get("cursor", 0):
            # Lap complete — report and exit (the operator can restart).
            report.notes.append(f"Full lap of {len(pool)} targets complete.")
            break

        time.sleep(max(0, cycle_pause_s))

    report.finished_at = time.time()
    LOG.info("Campaign done — run=%d skip=%d findings=%d zero=%d pr=%d",
             report.targets_run, report.targets_skipped, report.findings_total,
             report.zero_days_total, report.pr_drafts_total)
    return report


def start_campaign_in_background(**kwargs: Any) -> threading.Thread:
    """Fire a campaign on a daemon thread and return immediately."""
    th = threading.Thread(
        target=lambda: run_campaign(**kwargs),
        name="embodied-campaign",
        daemon=True,
    )
    th.start()
    return th


__all__ = [
    "CampaignReport",
    "run_campaign",
    "start_campaign_in_background",
    "request_stop",
    "reset_cursor",
]
