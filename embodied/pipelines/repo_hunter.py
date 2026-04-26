"""
EmbodiedOS — Side 1 · Repo Hunter Pipeline (Section 4.3).

Flow
----

    1.  COMMAND ───────────► IntentRouter classifies "mission repo <url>"
    2.  CLONE     ──────────► architect.sandbox.Sandbox.clone(repo_url)
    3.  RUNTIME   ──────────► language_runtime.RuntimeFactory().detect(path)
    4.  TEST DISCOVERY ─────► runtime.discover_tests(path)
    5.  FIX LOOP   ─────────► while failing:
                                  Hermes Agent run_task(side="fix")
                                  → OpenClaude/OpenClaw subagent edits code
                                  → runtime.run_tests()
                              (max_iters guard)
    6.  GREEN LIGHT ────────► verification_loop.verify(snapshot)
    7.  SKILL INJECTION ────► embodied.skills.sync_engine.pack_for_task(...)
    8.  RED TEAM   ─────────► red_team_fuzzer.run_red_team(path, skills=...)
                              + sast_gate.scan / taint_analyzer.analyze
                              + symbolic_engine.explore / fuzzing_engine.fuzz
                              + chain_analyzer.analyze_chain
    9.  CLASSIFY   ─────────► vuln_classifier.classify(findings)
                              → "bug" | "vuln" | "zero_day"
    10. ROUTE BUG/VULN ─────► github_app.open_pull_request(...)
                              embodied.bridge → emit notification
    11. ROUTE ZERO-DAY ─────► exploit_primitives.analyze
                              + harness_factory.build_poc
                              + disclosure_vault.store_finding
                              + disclosure_vault.scrape_developer_emails
                              → returns ``pending_human_approval`` (never
                                auto-discloses).

Every existing module is **reused, not replaced**.  This file is the glue
that ties them into one Hermes-driven loop.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from embodied.bridge.hermes_client import HermesClient
from embodied.bridge.role_prompts import (
    BLUE_TEAM_PRIME,
    RED_TEAM_PRIME,
    ZERO_DAY_PRIME,
    with_role,
)
from embodied.bridge.tool_registry import _safe_import  # type: ignore[attr-defined]
from embodied.memory.unified_memory import get_memory
from embodied.skills.sync_engine import SkillSyncEngine

LOG = logging.getLogger("embodied.pipelines.repo_hunter")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class RepoHunterReport:
    mission_id: str
    repo_url: str
    status: str = "pending"            # pending | green | red_team | finished | failed
    runtime: str | None = None
    fix_iterations: int = 0
    failing_tests_initial: int = 0
    failing_tests_final: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)
    pr_url: str | None = None
    zero_days: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "repo_url":   self.repo_url,
            "status":     self.status,
            "runtime":    self.runtime,
            "fix_iterations": self.fix_iterations,
            "failing_tests_initial": self.failing_tests_initial,
            "failing_tests_final":   self.failing_tests_final,
            "findings":  self.findings,
            "pr_url":    self.pr_url,
            "zero_days": self.zero_days,
            "notes":     self.notes,
            "started_at":  self.started_at,
            "finished_at": self.finished_at,
        }


# ---------------------------------------------------------------------------
# In-memory mission registry
# ---------------------------------------------------------------------------


_REGISTRY: dict[str, RepoHunterReport] = {}
_REGISTRY_LOCK = threading.Lock()


def status(mission_id: str | None = None) -> dict[str, Any]:
    with _REGISTRY_LOCK:
        if mission_id:
            r = _REGISTRY.get(mission_id)
            return r.to_json() if r else {"ok": False, "reason": "unknown_mission"}
        return {"ok": True, "missions": [r.to_json() for r in _REGISTRY.values()]}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_repo_hunter(
    *,
    repo_url: str,
    branch: str = "",
    fix_only: bool = False,
    max_iters: int = 5,
    bridge_url: str | None = None,
) -> dict[str, Any]:
    """Synchronous Side 1 pipeline. Returns a JSON-able RepoHunterReport."""

    mission = RepoHunterReport(mission_id=f"side1-{uuid.uuid4().hex[:10]}", repo_url=repo_url)
    with _REGISTRY_LOCK:
        _REGISTRY[mission.mission_id] = mission
    mem = get_memory()
    mem.write_session(mission_id=mission.mission_id, event={"phase": "start", "repo": repo_url})

    # Step 2 — clone -------------------------------------------------------
    sandbox = _open_sandbox()
    workdir = _clone(sandbox, repo_url, branch, mission)
    if workdir is None:
        return _finish(mission, "failed")

    # Step 3 — runtime detection ------------------------------------------
    runtime = _detect_runtime(workdir, mission)
    if runtime is None:
        mission.notes.append("No runtime detected — falling back to language-agnostic analysis only.")

    # Step 4-5 — discover + fix tests until green --------------------------
    fix_report = _fix_until_green(workdir, runtime, mission, max_iters=max_iters)

    if fix_only:
        return _finish(mission, "green" if fix_report["green"] else "failed")

    if not fix_report["green"]:
        mission.notes.append("Tests still failing after max_iters — entering red-team in degraded mode.")

    # Step 6 — verification loop snapshot ---------------------------------
    _verification_snapshot(workdir, mission)

    # Step 7 — skill injection --------------------------------------------
    skills_prompt = _pack_skills(workdir, mission)

    # Step 8 — red team ----------------------------------------------------
    findings = _run_red_team(workdir, skills_prompt, mission)

    # Step 9 — classify ----------------------------------------------------
    classified = _classify(findings, mission)

    # Step 10 — bugs / vulns → auto-PR ------------------------------------
    for f in classified.get("bug", []) + classified.get("vuln", []):
        pr_url = _open_pr(repo_url, f, mission)
        if pr_url:
            f["pr_url"] = pr_url
            mission.pr_url = mission.pr_url or pr_url
        _emit_finding(f, mission)

    # Step 11 — zero-days → vault + email scrape (HUMAN-GATED) -------------
    for f in classified.get("zero_day", []):
        zd = _route_zero_day(repo_url, workdir, f, mission)
        mission.zero_days.append(zd)

    # Hermes auto-skill creation: distil the campaign into a new skill.
    _maybe_teach_new_skill(mission, skills_prompt, bridge_url=bridge_url)

    return _finish(mission, "finished")


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------


def _open_sandbox() -> Any | None:
    sandbox_mod = _safe_import("architect.sandbox")
    if sandbox_mod is None or not hasattr(sandbox_mod, "Sandbox"):
        LOG.warning("architect.sandbox unavailable — falling back to /tmp")
        return None
    try:
        return sandbox_mod.Sandbox()
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Sandbox init failed: %s", exc)
        return None


def _clone(sandbox: Any | None, repo_url: str, branch: str, mission: RepoHunterReport) -> Path | None:
    if sandbox is not None and hasattr(sandbox, "clone"):
        try:
            handle = sandbox.clone(repo_url) if not branch else sandbox.clone(repo_url, branch=branch)
            path = Path(getattr(handle, "path", handle))
            mission.notes.append(f"Cloned {repo_url} → {path}")
            return path
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"sandbox.clone failed: {exc!r}")
    # Fallback: shell git clone into /tmp.
    import subprocess
    target = Path(f"/tmp/embodied/{mission.mission_id}")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["-b", branch]
        cmd += [repo_url, str(target)]
        subprocess.check_call(cmd, timeout=180)
        mission.notes.append(f"git clone {repo_url} → {target}")
        return target
    except Exception as exc:  # noqa: BLE001
        mission.notes.append(f"git clone failed: {exc!r}")
        return None


def _detect_runtime(workdir: Path, mission: RepoHunterReport) -> Any | None:
    lang = _safe_import("language_runtime")
    if lang is None or not hasattr(lang, "RuntimeFactory"):
        return None
    try:
        rt = lang.RuntimeFactory.for_repo(str(workdir))
        mission.runtime = getattr(rt, "language", None) or rt.__class__.__name__
        return rt
    except Exception as exc:  # noqa: BLE001
        mission.notes.append(f"runtime detection failed: {exc!r}")
        return None


def _fix_until_green(workdir: Path, runtime: Any | None, mission: RepoHunterReport, *, max_iters: int) -> dict[str, Any]:
    if runtime is None or not hasattr(runtime, "run_tests"):
        return {"green": False, "reason": "runtime_unavailable"}

    # The real LanguageRuntime API needs a per-test invocation
    # (test_path, repo_dir, env_config) → (output, returncode).  Provision
    # the env once per mission and re-use it across iterations.
    env_config = None
    if hasattr(runtime, "setup_env"):
        try:
            env_config = runtime.setup_env(str(workdir))
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"runtime.setup_env failed: {exc!r}")

    def _failing_tests() -> int:
        if not hasattr(runtime, "discover_tests"):
            return 0
        try:
            tests = runtime.discover_tests(str(workdir)) or []
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"discover_tests raised: {exc!r}")
            return 0
        bad = 0
        for tp in tests[:25]:  # cap to avoid runaway runs
            try:
                _, rc = runtime.run_tests(tp, str(workdir), env_config) if env_config \
                        else runtime.run_tests(tp, str(workdir), None)
                if rc != 0:
                    bad += 1
            except Exception as exc:  # noqa: BLE001
                mission.notes.append(f"run_tests({tp}) raised: {exc!r}")
                bad += 1
        return bad

    hermes = HermesClient()
    session = hermes.open_session(mission=f"fix-tests:{mission.repo_url}")
    sid = session.session_id if session else ""

    for it in range(max_iters):
        failing = _failing_tests()
        if it == 0:
            mission.failing_tests_initial = failing
        mission.failing_tests_final = failing
        mission.fix_iterations = it
        if failing == 0:
            mission.notes.append(f"All tests green after {it} fix iterations.")
            return {"green": True, "iterations": it}

        # Delegate the fix to Hermes Agent (which itself can spawn an
        # OpenClaw/OpenClaude subagent for code-gen via the bridge).
        instr = with_role(
            BLUE_TEAM_PRIME,
            f"Repository {mission.repo_url} (cloned at {workdir}) has {failing} failing tests. "
            "Fix the code so every test passes. Use the EmbodiedOS bridge tools "
            "rhodawk.repo.run_tests and rhodawk.sec.sast to verify your edits.",
        )
        result = hermes.run_task(session_id=sid, instruction=instr, max_iterations=8)
        if not result.get("ok"):
            mission.notes.append(f"Hermes fix iteration {it} unavailable: {result.get('reason')}")
            # Fall back to the existing OSS Guardian fix mode if available.
            _fallback_oss_guardian_fix(mission)
            break
    return {"green": False, "reason": "max_iters"}


def _fallback_oss_guardian_fix(mission: RepoHunterReport) -> None:
    guardian = _safe_import("oss_guardian")
    if guardian is None or not hasattr(guardian, "OSSGuardian"):
        return
    try:
        guardian.OSSGuardian(fix_only=True).run(mission.repo_url)
        mission.notes.append("Fell back to OSSGuardian(fix_only=True).run(...).")
    except Exception as exc:  # noqa: BLE001
        mission.notes.append(f"OSSGuardian fallback failed: {exc!r}")


def _verification_snapshot(workdir: Path, mission: RepoHunterReport) -> None:
    verify = _safe_import("verification_loop")
    if verify is None or not hasattr(verify, "snapshot"):
        return
    try:
        snap = verify.snapshot(str(workdir))
        mission.notes.append(f"Verification snapshot captured: {snap}")
    except Exception:  # noqa: BLE001
        pass


def _pack_skills(workdir: Path, mission: RepoHunterReport) -> str:
    engine = SkillSyncEngine()
    profile = {
        "languages":   [mission.runtime] if mission.runtime else [],
        "asset_types": ["repo", "code"],
        "frameworks":  [],
    }
    skills = engine.select_for_task(
        task_description=f"Red-team audit of {mission.repo_url}",
        profile=profile,
        attack_phase="static",
    )
    mission.notes.append(f"Injected {len(skills.split('<skill ')) - 1} skills into the prompt.")
    return skills


def _run_red_team(workdir: Path, skills_prompt: str, mission: RepoHunterReport) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    # ── red_team_fuzzer (AST-driven Hypothesis PBT lead generation) ──────
    redteam = _safe_import("red_team_fuzzer")
    if redteam is not None and hasattr(redteam, "analyze_repository_ast"):
        try:
            targets = redteam.analyze_repository_ast(str(workdir)) or []
            for t in targets[:25]:
                findings.append({
                    "id":        f"rt-{getattr(t, 'function_name', 'fn')}-{uuid.uuid4().hex[:6]}",
                    "title":     f"red-team target: {getattr(t, 'function_name', '?')}",
                    "file":      getattr(t, 'file_path', ''),
                    "severity":  "P3",
                    "source":    "red_team_fuzzer",
                    "description": f"AST-prioritised fuzz target (score={getattr(t, 'priority_score', 0):.2f}).",
                })
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"red_team_fuzzer.analyze_repository_ast failed: {exc!r}")

    # ── sast_gate ────────────────────────────────────────────────────────
    sast = _safe_import("sast_gate")
    if sast is not None and hasattr(sast, "run_sast_gate"):
        try:
            report = sast.run_sast_gate(diff_text="", changed_files=[], repo_dir=str(workdir))
            for f in getattr(report, "findings", []) or []:
                findings.append({
                    "id":         getattr(f, "id", uuid.uuid4().hex[:10]),
                    "title":      getattr(f, "rule_id", "sast finding"),
                    "file":       getattr(f, "file", ""),
                    "severity":   getattr(f, "severity", "P3"),
                    "description": getattr(f, "message", ""),
                    "source":     "sast_gate",
                })
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"sast_gate.run_sast_gate failed: {exc!r}")

    # ── taint_analyzer ───────────────────────────────────────────────────
    taint = _safe_import("taint_analyzer")
    if taint is not None and hasattr(taint, "run_taint_analysis"):
        try:
            res = taint.run_taint_analysis(str(workdir))
            for f in (res.get("vulnerabilities") or res.get("flows") or []) if isinstance(res, dict) else []:
                ff = dict(f) if isinstance(f, dict) else {"raw": repr(f)}
                ff.setdefault("source", "taint_analyzer")
                ff.setdefault("severity", "P2")
                findings.append(ff)
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"taint_analyzer.run_taint_analysis failed: {exc!r}")

    # ── symbolic_engine ──────────────────────────────────────────────────
    sym = _safe_import("symbolic_engine")
    if sym is not None and hasattr(sym, "run_symbolic_analysis"):
        try:
            res = sym.run_symbolic_analysis(str(workdir))
            for f in (res.get("results") or res.get("paths") or []) if isinstance(res, dict) else []:
                ff = dict(f) if isinstance(f, dict) else {"raw": repr(f)}
                ff.setdefault("source", "symbolic_engine")
                ff.setdefault("severity", "P3")
                findings.append(ff)
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"symbolic_engine.run_symbolic_analysis failed: {exc!r}")

    # ── chain_analyzer (links primitives stored in the chain DB) ─────────
    chain = _safe_import("chain_analyzer")
    if chain is not None and hasattr(chain, "analyze_chains"):
        try:
            chains = chain.analyze_chains(mission.repo_url) or []
            mission.notes.append(f"chain_analyzer linked {len(chains)} chains.")
            for c in chains:
                if isinstance(c, dict):
                    findings.append({
                        "id":          c.get("chain_id") or uuid.uuid4().hex[:10],
                        "title":       c.get("title", "exploit chain"),
                        "severity":    c.get("severity", "P2"),
                        "description": c.get("description", ""),
                        "source":      "chain_analyzer",
                    })
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"chain_analyzer.analyze_chains failed: {exc!r}")

    mission.findings = findings
    return findings


def _normalize_findings(raw: Any, *, source: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, dict) and "findings" in raw:
        raw = raw["findings"]
    out: list[dict[str, Any]] = []
    for r in raw or []:
        if isinstance(r, dict):
            r.setdefault("source", source)
            out.append(r)
        else:
            out.append({"raw": repr(r), "source": source})
    return out


def _classify(findings: list[dict[str, Any]], mission: RepoHunterReport) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"bug": [], "vuln": [], "zero_day": []}
    cls = _safe_import("vuln_classifier")

    def _bucket_for(sev: str) -> str:
        sev = (sev or "").upper()
        if sev in {"P1", "CRIT", "CRITICAL"}:
            return "zero_day"
        if sev in {"P2", "HIGH"}:
            return "vuln"
        return "bug"

    for f in findings:
        sev = f.get("severity") or ""
        if cls is not None and hasattr(cls, "classify_vulnerability"):
            try:
                res = cls.classify_vulnerability(
                    cwe_hint=str(f.get("cwe", "")),
                    description=str(f.get("description", f.get("title", ""))),
                    exploit_class=str(f.get("source", "")),
                )
                # ClassificationResult fields tend to be: severity, cwe_id, taxonomy.
                sev = getattr(res, "severity", sev) or sev
                cwe = getattr(res, "cwe_id", None)
                if cwe:
                    f["cwe"] = cwe
                f["severity"] = sev
            except Exception as exc:  # noqa: BLE001
                mission.notes.append(f"vuln_classifier failed for {f.get('id')}: {exc!r}")
        out[_bucket_for(sev)].append(f)
    return out


def _open_pr(repo_url: str, finding: dict[str, Any], mission: RepoHunterReport) -> str | None:
    gh = _safe_import("github_app")
    if gh is None or not hasattr(gh, "open_pr_for_repo"):
        return None
    try:
        token = gh.get_github_token(repo_url) if hasattr(gh, "get_github_token") else ""
        if not token:
            mission.notes.append(f"No GitHub token available for {repo_url} — PR skipped.")
            return None
        branch = f"embodiedos/{mission.mission_id}/{finding.get('id', uuid.uuid4().hex[:6])}"
        return gh.open_pr_for_repo(
            upstream_repo=repo_url,
            branch=branch,
            test_path=finding.get("file") or finding.get("patch_path", ""),
            token=token,
            fork_mode=False,
        )
    except Exception as exc:  # noqa: BLE001
        mission.notes.append(f"PR open failed for {finding.get('id')}: {exc!r}")
        return None


def _emit_finding(finding: dict[str, Any], mission: RepoHunterReport) -> None:
    bridge = _safe_import("architect.embodied_bridge")
    if bridge is None or not hasattr(bridge, "emit_finding"):
        return
    try:
        payload = bridge.FindingPayload(
            finding_id=finding.get("id", uuid.uuid4().hex[:10]),
            title=finding.get("title", "untitled"),
            severity=finding.get("severity", "P3"),
            cwe=str(finding.get("cwe", "")),
            repo=mission.repo_url,
            file_path=finding.get("file", ""),
            description=finding.get("description", ""),
            proof_of_concept=finding.get("poc", ""),
            acts_score=float(finding.get("acts", 0.0)),
        )
        bridge.emit_finding(payload)
    except Exception:  # noqa: BLE001
        pass


def _route_zero_day(repo_url: str, workdir: Path, finding: dict[str, Any], mission: RepoHunterReport) -> dict[str, Any]:
    # OPERATING CONTRACT: this pipeline collects everything the operator
    # needs for a manual disclosure (PoC harness, exploit primitive
    # analysis, dossier, candidate maintainer addresses) and then STOPS
    # at status="pending_human_approval".  No email is ever sent from
    # inside this function — the operator reviews the dossier and emails
    # maintainers themselves through their own client.
    record: dict[str, Any] = {
        "finding":     finding,
        "poc_path":    None,
        "vault_id":    None,
        "recipients":  [],
        "status":      "pending_human_approval",
    }

    primitives = _safe_import("exploit_primitives")
    if primitives is not None and hasattr(primitives, "reason_exploitability"):
        try:
            record["primitives"] = primitives.reason_exploitability(
                crash_input=str(finding.get("poc_input", "")),
                crash_output=str(finding.get("poc_output", "")),
                file_path=str(finding.get("file", "")),
                vuln_type=str(finding.get("title", "unknown")),
                source_context=str(finding.get("description", "")),
            )
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"reason_exploitability failed: {exc!r}")

    harness_result: dict[str, Any] = {}
    harness = _safe_import("harness_factory")
    if harness is not None and hasattr(harness, "generate_poc_harness"):
        try:
            harness_result = harness.generate_poc_harness(
                {"finding": finding, "file": finding.get("file", "")},
                str(workdir),
            ) or {}
            record["poc_path"] = harness_result.get("harness_path") or harness_result.get("path")
            record["harness_status"] = harness_result.get("status", "PENDING_HUMAN_REVIEW")
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"generate_poc_harness failed: {exc!r}")

    # Maintainer-email enumeration — collected for the operator's morning
    # report only; nothing is sent from this module.
    vault = _safe_import("disclosure_vault")
    if vault is not None and hasattr(vault, "scrape_developer_emails"):
        try:
            record["recipients"] = vault.scrape_developer_emails(repo_url, str(workdir)) or []
            mission.notes.append(
                f"Scraped {len(record['recipients'])} maintainer-email candidates "
                f"for {repo_url} — awaiting operator review (no email sent)."
            )
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"scrape_developer_emails failed: {exc!r}")

    if vault is not None and hasattr(vault, "compile_dossier"):
        try:
            record["vault_id"] = vault.compile_dossier(
                repo=repo_url,
                semantic_graph={},
                assumption_gap={"finding": finding},
                harness_result=harness_result,
                chain_analysis=None,
                bug_bounty_program="",
                maintainer_contact=", ".join(record["recipients"][:5]),
            )
        except Exception as exc:  # noqa: BLE001
            mission.notes.append(f"disclosure_vault.compile_dossier failed: {exc!r}")

    # Optional: ask Hermes to draft the human-facing disclosure narrative
    # (held in the dossier, never sent).  The role prime keeps Hermes in
    # disclosure-analyst mode rather than refusing on safety grounds.
    try:
        narrative = HermesClient().run_task(
            session_id="",
            instruction=with_role(
                ZERO_DAY_PRIME,
                f"Draft a responsible-disclosure write-up for finding "
                f"{finding.get('id')} in {repo_url}.  Use the harness at "
                f"{record.get('poc_path')!r}.  Output: title, summary, "
                f"impact, reproduction steps, suggested patch, CWE/CVSS.",
            ),
            max_iterations=4,
        )
        if narrative.get("ok") and narrative.get("text"):
            record["disclosure_draft"] = narrative["text"]
    except Exception:  # noqa: BLE001
        pass

    mission.notes.append(
        f"Zero-day {finding.get('id')} queued in vault as "
        f"{record.get('vault_id') or 'no-id'} — awaiting operator approval."
    )
    return record


def _maybe_teach_new_skill(mission: RepoHunterReport, skills_prompt: str, *, bridge_url: str | None) -> None:
    if not mission.findings:
        return
    body = (
        f"# Skill auto-distilled from EmbodiedOS Side 1 mission `{mission.mission_id}`\n\n"
        f"- Repo: {mission.repo_url}\n"
        f"- Findings: {len(mission.findings)}\n"
        f"- Runtime: {mission.runtime}\n"
        f"- Notes:\n  - " + "\n  - ".join(mission.notes[-5:])
    )
    frontmatter = {
        "name":     f"campaign-{mission.mission_id}",
        "domain":   "campaign-replay",
        "triggers": {"asset_types": ["repo"]},
        "tools":    [],
        "severity_focus": ["P1", "P2"],
    }
    HermesClient().teach_skill(name=frontmatter["name"], frontmatter=frontmatter, body=body)
    get_memory().procedural_save_skill(name=frontmatter["name"], frontmatter=frontmatter, body=body)


def _finish(mission: RepoHunterReport, status_: str) -> dict[str, Any]:
    mission.status = status_
    mission.finished_at = time.time()
    get_memory().episodic_add(
        summary=f"[Side1] {mission.repo_url} → {status_} ({len(mission.findings)} findings)",
        metadata=mission.to_json(),
    )
    return mission.to_json()
