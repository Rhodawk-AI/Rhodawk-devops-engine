"""
EmbodiedOS — Side 2 · Bounty Hunter Pipeline (Section 4.4).

Flow
----

    1.  CONTINUOUS SCRAPE ─► bounty_gateway.scrape_programs(platform=...)
                              + mythos.mcp.scope_parser_mcp parses the
                              public scope into in-scope domains + repos.
    2.  PROGRAM SCORING ───► oss_target_scorer + bugbounty_checklist.score
                              → highest payout × shallow competition first.
    3.  SANDBOX DEPLOY ────► architect.sandbox.Sandbox.deploy_target(...)
                              (clone repo OR provision the live software
                              from a Dockerfile / docker-compose if the
                              program ships one).
    4.  SKILL INJECTION ───► embodied.skills.sync_engine packs the most
                              relevant skills for the program's tech-stack.
    5.  FULL AUDIT ────────► night_hunt_orchestrator.run_night_cycle(...)
                              with target=program → fans out to the
                              same engines used by Side 1 plus the
                              network-reachable Mythos MCP servers.
    6.  P1/P2 REPORTS ─────► architect.skills.report-quality templates
                              + bugbounty_checklist.draft_submission(...)
    7.  HUMAN APPROVAL ────► held in disclosure_vault → Telegram /
                              OpenClaw alert → operator runs
                              ``approve <finding-id>``.
    8.  SUBMISSION ────────► bounty_gateway.submit(platform, program, report)
                              (only when ``EMBODIED_AUTOSUBMIT=1`` AND the
                              finding has been operator-approved).

The first 50 cycles are forced into "review-only" mode regardless of
``EMBODIED_AUTOSUBMIT`` so the operator builds confidence in the system.
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from embodied.bridge.tool_registry import _safe_import  # type: ignore[attr-defined]
from embodied.memory.unified_memory import get_memory
from embodied.skills.sync_engine import SkillSyncEngine

LOG = logging.getLogger("embodied.pipelines.bounty_hunter")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class BountyHunterReport:
    mission_id: str
    platform: str
    program: str
    status: str = "pending"
    score: float = 0.0
    findings: list[dict[str, Any]] = field(default_factory=list)
    held_for_review: list[dict[str, Any]] = field(default_factory=list)
    submitted: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "platform":   self.platform,
            "program":    self.program,
            "status":     self.status,
            "score":      self.score,
            "findings":   self.findings,
            "held_for_review": self.held_for_review,
            "submitted":  self.submitted,
            "notes":      self.notes,
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
        }


# ---------------------------------------------------------------------------
# Mission registry + cycle counter (for the 50-cycle review-only window)
# ---------------------------------------------------------------------------


_REGISTRY: dict[str, BountyHunterReport] = {}
_REGISTRY_LOCK = threading.Lock()
_CYCLE_COUNT = 0


def status(mission_id: str | None = None) -> dict[str, Any]:
    with _REGISTRY_LOCK:
        if mission_id:
            r = _REGISTRY.get(mission_id)
            return r.to_json() if r else {"ok": False, "reason": "unknown_mission"}
        return {"ok": True, "missions": [r.to_json() for r in _REGISTRY.values()],
                "cycle_count": _CYCLE_COUNT}


# ---------------------------------------------------------------------------
# Step 1 — continuous scrape
# ---------------------------------------------------------------------------


def scrape_programs(*, platform: str | None = None, min_payout: int = 0) -> dict[str, Any]:
    bg = _safe_import("bounty_gateway")
    if bg is None or not hasattr(bg, "scrape_programs"):
        return {"ok": False, "reason": "bounty_gateway_unavailable"}
    try:
        progs = bg.scrape_programs(platform=platform, min_payout=min_payout) or []
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": "scrape_failed", "exception": repr(exc)}

    # Enrich with scope parser if available.
    scope_mod = _safe_import("mythos.mcp.scope_parser_mcp")
    if scope_mod is not None and hasattr(scope_mod, "parse_scope"):
        for p in progs:
            try:
                p["scope"] = scope_mod.parse_scope(p.get("scope_url") or p.get("url") or "")
            except Exception:  # noqa: BLE001
                p["scope"] = {"in_scope": [], "out_of_scope": []}

    return {"ok": True, "count": len(progs), "programs": progs}


# ---------------------------------------------------------------------------
# Step 2-7 — full audit of a single program
# ---------------------------------------------------------------------------


def scan_bounty_program(*, platform: str, program: str) -> dict[str, Any]:
    global _CYCLE_COUNT
    mission = BountyHunterReport(
        mission_id=f"side2-{uuid.uuid4().hex[:10]}",
        platform=platform,
        program=program,
    )
    with _REGISTRY_LOCK:
        _REGISTRY[mission.mission_id] = mission
        _CYCLE_COUNT += 1
        cycle = _CYCLE_COUNT
    mem = get_memory()
    mem.write_session(mission_id=mission.mission_id, event={"phase": "start", "platform": platform, "program": program})

    # Step 2 — score & decide whether to proceed.
    mission.score = _score_program(platform, program, mission)
    if mission.score <= 0:
        mission.notes.append("Score ≤ 0 — skipping audit.")
        return _finish(mission, "skipped")

    # Step 3 — sandbox deploy (clone or docker-compose up).
    target = _deploy_target(platform, program, mission)
    if target is None:
        return _finish(mission, "failed")

    # Step 4 — skill injection.
    skills_prompt = _pack_skills(target, mission)

    # Step 5 — full audit via Night Hunt orchestrator.
    findings = _run_full_audit(target, skills_prompt, mission)

    # Step 6 — generate platform-ready P1/P2 reports.
    reports = _generate_reports(platform, program, findings, mission)

    # Step 7 — hold for human approval (always for first 50 cycles).
    auto = os.getenv("EMBODIED_AUTOSUBMIT", "0") == "1" and cycle > 50
    for r in reports:
        if auto and r.get("approved"):
            sub = _submit_report(platform, program, r, mission)
            mission.submitted.append(sub)
        else:
            r["status"] = "pending_human_approval"
            mission.held_for_review.append(r)
            _alert_operator(platform, program, r, mission)
    return _finish(mission, "finished")


# ---------------------------------------------------------------------------
# Step 8 (optional) — operator-approved submission
# ---------------------------------------------------------------------------


def submit_approved(*, mission_id: str, finding_id: str) -> dict[str, Any]:
    with _REGISTRY_LOCK:
        mission = _REGISTRY.get(mission_id)
    if not mission:
        return {"ok": False, "reason": "unknown_mission"}
    target = next((r for r in mission.held_for_review if r.get("finding_id") == finding_id), None)
    if target is None:
        return {"ok": False, "reason": "unknown_finding"}
    sub = _submit_report(mission.platform, mission.program, target, mission)
    mission.submitted.append(sub)
    mission.held_for_review.remove(target)
    return {"ok": True, "submission": sub}


# ---------------------------------------------------------------------------
# Continuous-cycle entry point — picks the highest-scoring program & runs.
# ---------------------------------------------------------------------------


def run_bounty_hunter(*, platform: str | None = None, min_payout: int = 1000) -> dict[str, Any]:
    progs = scrape_programs(platform=platform, min_payout=min_payout)
    if not progs.get("ok"):
        return progs
    candidates = sorted(progs.get("programs", []),
                        key=lambda p: p.get("payout", 0),
                        reverse=True)
    if not candidates:
        return {"ok": True, "reason": "no_candidates"}
    pick = candidates[0]
    return scan_bounty_program(platform=pick.get("platform", platform or "hackerone"),
                               program=pick.get("handle") or pick.get("name") or "")


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------


def _score_program(platform: str, program: str, mission: BountyHunterReport) -> float:
    score = 0.0
    scorer = _safe_import("oss_target_scorer")
    if scorer is not None and hasattr(scorer, "score"):
        try:
            score = float(scorer.score({"platform": platform, "program": program}))
        except Exception:  # noqa: BLE001
            pass
    cl = _safe_import("bugbounty_checklist")
    if cl is not None and hasattr(cl, "score"):
        try:
            score += float(cl.score(program))
        except Exception:  # noqa: BLE001
            pass
    mission.notes.append(f"Program score: {score:.2f}")
    return score


def _deploy_target(platform: str, program: str, mission: BountyHunterReport) -> Any | None:
    sandbox_mod = _safe_import("architect.sandbox")
    if sandbox_mod is None or not hasattr(sandbox_mod, "Sandbox"):
        mission.notes.append("Sandbox unavailable — cannot deploy target.")
        return None
    try:
        s = sandbox_mod.Sandbox()
        if hasattr(s, "deploy_target"):
            return s.deploy_target(platform=platform, program=program)
        # Fallback: just allocate an empty workdir for the audit.
        if hasattr(s, "fresh"):
            return s.fresh()
    except Exception as exc:  # noqa: BLE001
        mission.notes.append(f"deploy_target failed: {exc!r}")
    return None


def _pack_skills(target: Any, mission: BountyHunterReport) -> str:
    eng = SkillSyncEngine()
    profile = {
        "asset_types": ["http", "web", "domain"],
        "languages":   getattr(target, "languages", []) or [],
        "frameworks":  getattr(target, "frameworks", []) or [],
    }
    return eng.select_for_task(
        task_description=f"Side 2 bounty audit of {mission.platform}/{mission.program}",
        profile=profile,
        attack_phase="recon",
    )


def _run_full_audit(target: Any, skills_prompt: str, mission: BountyHunterReport) -> list[dict[str, Any]]:
    night = _safe_import("night_hunt_orchestrator")
    findings: list[dict[str, Any]] = []
    if night is not None and hasattr(night, "run_night_cycle"):
        try:
            report = night.run_night_cycle(
                target=getattr(target, "url", str(target)),
                skills_prompt=skills_prompt,
            )
            findings = (report.get("findings") if isinstance(report, dict) else
                        getattr(report, "findings", []) or [])
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"night_hunt_orchestrator failed: {exc!r}")
    mission.findings = findings
    return findings


def _generate_reports(platform: str, program: str, findings: list[dict[str, Any]], mission: BountyHunterReport) -> list[dict[str, Any]]:
    cl = _safe_import("bugbounty_checklist")
    out: list[dict[str, Any]] = []
    for f in findings:
        sev = (f.get("severity") or "").upper()
        if sev not in {"P1", "P2", "CRITICAL", "HIGH"}:
            continue
        rep: dict[str, Any] = {
            "finding_id": f.get("id", uuid.uuid4().hex[:10]),
            "platform":   platform,
            "program":    program,
            "title":      f.get("title", "untitled"),
            "severity":   sev,
            "summary":    f.get("description", ""),
            "steps":      f.get("steps", []),
            "impact":     f.get("impact", ""),
            "poc":        f.get("poc", ""),
            "remediation": f.get("remediation", ""),
            "approved":    False,
        }
        if cl is not None and hasattr(cl, "draft_submission"):
            try:
                rep["draft"] = cl.draft_submission(rep)
            except Exception:  # noqa: BLE001
                pass
        out.append(rep)
    mission.notes.append(f"Drafted {len(out)} P1/P2 reports.")
    return out


def _alert_operator(platform: str, program: str, report: dict[str, Any], mission: BountyHunterReport) -> None:
    bridge = _safe_import("architect.embodied_bridge")
    if bridge is None or not hasattr(bridge, "emit_finding"):
        return
    try:
        payload = bridge.FindingPayload(
            finding_id=report["finding_id"],
            title=report["title"],
            severity=report["severity"],
            cwe="",
            repo=f"{platform}/{program}",
            file_path="",
            description=report.get("summary", ""),
            proof_of_concept=report.get("poc", ""),
            acts_score=0.0,
        )
        bridge.emit_finding(payload)
    except Exception:  # noqa: BLE001
        pass


def _submit_report(platform: str, program: str, report: dict[str, Any], mission: BountyHunterReport) -> dict[str, Any]:
    bg = _safe_import("bounty_gateway")
    if bg is None or not hasattr(bg, "submit"):
        mission.notes.append("bounty_gateway.submit unavailable — submission skipped.")
        return {"ok": False, "reason": "submit_unavailable"}
    try:
        return bg.submit(platform=platform, program=program, report=report)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": "submit_failed", "exception": repr(exc)}


def _finish(mission: BountyHunterReport, status_: str) -> dict[str, Any]:
    mission.status = status_
    mission.finished_at = time.time()
    get_memory().episodic_add(
        summary=f"[Side2] {mission.platform}/{mission.program} → {status_} ({len(mission.findings)} findings)",
        metadata=mission.to_json(),
    )
    return mission.to_json()
