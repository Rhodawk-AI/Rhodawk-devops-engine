"""
Rhodawk AI — EmbodiedOS (Masterplan §6, fully realised)
========================================================

EmbodiedOS is the unified front-of-house brain that fuses the two existing
agents in this codebase into a single coordinator:

  • **Hermes** (`hermes_orchestrator.py`)   — the autonomous deep-research
    loop.  Runs phases (recon → static → dynamic → exploit), dispatches
    `HermesTool`s, computes VES + ACTS, and yields `VulnerabilityFinding`s.

  • **OpenClaw** (`openclaw_gateway.py`)    — the operator-facing
    natural-language command bus (HTTP + Telegram + Slack) that already
    routes "scan repo X", "night run", "approve finding Y", etc.

EmbodiedOS does **not** replace either of them.  It sits *on top* and:

  1. Re-exports every existing OpenClaw intent verbatim — so the HTTP
     endpoint at ``POST /openclaw/command`` and the Telegram webhook
     keep working with zero behavioural change.

  2. Adds three high-level **mission** intents that an investor-grade
     operator can issue in one English sentence — each one orchestrates
     several existing subsystems end-to-end:

       • ``mission repo <github-url>``
            ─ Clone → detect runtime → run tests → if failing tests:
              Hermes fix-mode → open PR.  If all tests pass: enter
              **Adversarial Mutation pass** (break the tests, re-fix,
              keep the diff as a regression-resilience patch) → then
              run a **Zero-Day pass** (full Hermes attack mode with
              max_iterations=20).  Any P1/P2 finding is auto-routed
              through ``oss_guardian`` → ``disclosure_vault`` →
              ``embodied_bridge`` exactly like the existing pipeline.

       • ``mission bounty <hackerone-or-bugcrowd-url>``
            ─ Fetch the program page (via the camofox-browser MCP if
              available, falling back to ``requests``), extract the
              public scope (in-scope GitHub repos + domains), then
              queue each repo through ``mission repo`` and stream the
              results back as a single PhD-level Markdown briefing
              that lists every confirmed P1/P2 in submission-ready
              form (template copied from ``bounty_gateway`` /
              ``bugbounty_checklist``).

       • ``mission brief``
            ─ Reads ``openclaw_schedule.yaml``, ``job_queue``, the
              skill-selector stats and the meta-learner log to produce
              a single-screen "what is Rhodawk doing right now" status.

  3. Registers all three missions with ``openclaw_gateway.register(...)``
     at import time so they instantly appear over **every** existing
     channel (HTTP, Telegram, Slack) without changing the gateway code.

Design principles
-----------------
* **Additive only.**  No existing function is modified or moved.  All
  cross-module calls are guarded with try/except so a missing optional
  dependency degrades gracefully — the worst case is a structured
  error reply, never a crash.
* **Single dispatch.**  One public entry point, ``EmbodiedOS.dispatch``,
  is the only thing the Gradio UI / Telegram / HTTP need to call.
* **Long missions are non-blocking.**  Heavy missions
  (``mission_repo`` / ``mission_bounty``) run in a daemon thread and
  return a ``mission_id`` immediately; the operator polls
  ``mission status <id>`` for the live transcript.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

LOG = logging.getLogger("rhodawk.embodied_os")

# ── Constants ───────────────────────────────────────────────────────────────
ROOT_DIR        = Path(__file__).resolve().parent
SKILLS_DIR      = ROOT_DIR / "architect" / "skills"
MISSIONS_DIR    = Path(os.getenv("EMBODIED_MISSIONS_DIR", "/tmp/embodied_missions"))
MISSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Severity floors.  P1/P2 are what bug-bounty programs actually pay for.
P_SEVERITY_FLOOR = {"P1", "P2", "CRITICAL", "HIGH"}

# Public scope extraction patterns — used by mission_bounty to find
# in-scope GitHub repos on a HackerOne / Bugcrowd / Intigriti / YesWeHack
# program page.  Conservative on purpose: we only auto-target sources
# we can clone and review locally.
_GH_REPO_RE   = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+?)(?:\.git)?(?=[\s\"'<)\],]|$)",
    re.I,
)
_DOMAIN_RE    = re.compile(
    r"\b((?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,24})\b",
    re.I,
)


# ── Data classes ────────────────────────────────────────────────────────────
@dataclass
class MissionState:
    """Live state for a long-running mission (repo / bounty)."""
    mission_id : str
    kind       : str                     # "repo" | "bounty"
    target     : str
    status     : str = "queued"          # queued | running | done | error
    started_at : float = field(default_factory=time.time)
    ended_at   : float | None = None
    transcript : list[str] = field(default_factory=list)
    artifacts  : dict[str, Any] = field(default_factory=dict)
    error      : str | None = None

    def log(self, msg: str, level: str = "MISSION") -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] [{level}] {msg}"
        self.transcript.append(line)
        LOG.info("[%s] %s", self.mission_id, msg)
        # Best-effort persist after every log line so a crash never
        # loses the trail.
        try:
            self._persist()
        except Exception:  # noqa: BLE001
            pass

    def _persist(self) -> None:
        path = MISSIONS_DIR / f"{self.mission_id}.json"
        path.write_text(
            json.dumps(
                {
                    "mission_id": self.mission_id,
                    "kind"      : self.kind,
                    "target"    : self.target,
                    "status"    : self.status,
                    "started_at": self.started_at,
                    "ended_at"  : self.ended_at,
                    "error"     : self.error,
                    "artifacts" : self.artifacts,
                    "transcript": self.transcript[-500:],   # cap on disk
                },
                indent=2, default=str,
            ),
            encoding="utf-8",
        )

    def summary(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "kind"      : self.kind,
            "target"    : self.target,
            "status"    : self.status,
            "tail"      : self.transcript[-12:],
            "artifacts" : {k: v for k, v in self.artifacts.items()
                            if not isinstance(v, (bytes, bytearray))},
            "error"     : self.error,
        }


# ── In-process mission registry ─────────────────────────────────────────────
class _MissionRegistry:
    def __init__(self) -> None:
        self._lock     = threading.Lock()
        self._missions : dict[str, MissionState] = {}

    def create(self, kind: str, target: str) -> MissionState:
        mid = f"{kind}-{uuid.uuid4().hex[:10]}"
        ms = MissionState(mission_id=mid, kind=kind, target=target)
        with self._lock:
            self._missions[mid] = ms
        ms.log(f"mission created kind={kind} target={target}", "BOOT")
        return ms

    def get(self, mid: str) -> MissionState | None:
        with self._lock:
            ms = self._missions.get(mid)
        if ms:
            return ms
        # Try disk recovery so the operator can poll old missions even
        # after a process restart.
        path = MISSIONS_DIR / f"{mid}.json"
        if path.is_file():
            try:
                d = json.loads(path.read_text(encoding="utf-8"))
                ms = MissionState(
                    mission_id=d["mission_id"], kind=d["kind"],
                    target=d["target"], status=d.get("status", "?"),
                    started_at=d.get("started_at", 0.0),
                    ended_at=d.get("ended_at"),
                    transcript=list(d.get("transcript", [])),
                    artifacts=dict(d.get("artifacts", {})),
                    error=d.get("error"),
                )
                with self._lock:
                    self._missions[mid] = ms
                return ms
            except Exception:  # noqa: BLE001
                return None
        return None

    def list_recent(self, n: int = 20) -> list[MissionState]:
        with self._lock:
            items = sorted(self._missions.values(),
                           key=lambda m: m.started_at, reverse=True)
        return items[:n]


_REGISTRY = _MissionRegistry()


# ── Mission: REPO ───────────────────────────────────────────────────────────
def _run_mission_repo(ms: MissionState) -> None:
    """
    End-to-end repo mission.  Order of operations follows the user's
    spec verbatim:

      1. Clone (delegated to OSSGuardian → repo_harvester sandbox).
      2. Run failing tests → fix them via Hermes (`fix-failing-tests`).
      3. If tests already pass → adversarial mutation pass:
         break-then-refix (`adversarial-mutation:harden`).
      4. Open PR for any diffs produced (Hermes does this when its
         tools include the github MCP — already in /tmp/mcp_runtime.json).
      5. Zero-day pass: full Hermes attack mode (max 20 iterations).
      6. Route findings through the existing oss_guardian /
         disclosure_vault / embodied_bridge plumbing — *we do not
         re-implement it*; we just call ``OSSGuardian.run()`` which
         already covers steps 1-2 and 5+6 — then layer steps 3-4 on
         top via direct Hermes calls.
    """
    ms.status = "running"
    target = ms.target

    # --- Step A: delegate to OSSGuardian ------------------------------------
    try:
        from oss_guardian import OSSGuardian
    except Exception as exc:  # noqa: BLE001
        ms.status = "error"
        ms.error  = f"oss_guardian unavailable: {exc}"
        ms.log(ms.error, "ERR")
        ms.ended_at = time.time()
        return

    try:
        ms.log("Phase A: OSSGuardian().run() — clone + tests + fix/attack", "PHASE")
        camp = OSSGuardian().run(target)
        ms.artifacts["oss_campaign"] = camp.to_json() \
            if hasattr(camp, "to_json") else dataclasses.asdict(camp)
        ms.log(f"OSSGuardian done: mode={camp.mode} "
               f"findings={len(camp.findings)} "
               f"error={getattr(camp, 'error', None)}", "OK")
    except Exception as exc:  # noqa: BLE001
        ms.log(f"OSSGuardian crashed: {exc}", "ERR")
        ms.log(traceback.format_exc(), "ERR")
        camp = None

    # --- Step B: adversarial mutation pass (only meaningful if tests passed)
    if camp is not None and getattr(camp, "mode", "") == "attack":
        try:
            from hermes_orchestrator import run_hermes_research
            ms.log("Phase B: adversarial-mutation pass (break tests → re-fix)",
                   "PHASE")
            session = run_hermes_research(
                target_repo=target,
                repo_dir=getattr(camp, "repo_path", str(ROOT_DIR)),
                focus_area=(
                    "adversarial-mutation:harden — mutate the existing test "
                    "suite to break it, then re-fix the production code so "
                    "every mutated assertion still passes.  Submit the diff "
                    "as a regression-resilience patch."
                ),
                max_iterations=int(os.getenv("EMBODIED_MUTATION_ITER", "8")),
                progress_callback=lambda m: ms.log(m, "HERMES"),
            )
            ms.artifacts["mutation_session"] = getattr(session, "session_id", "?")
            ms.log("mutation pass done", "OK")
        except Exception as exc:  # noqa: BLE001
            ms.log(f"mutation pass failed: {exc}", "WARN")

    # --- Step C: explicit zero-day deep pass (in addition to OSSGuardian's)
    try:
        from hermes_orchestrator import run_hermes_research, get_session_summary
        ms.log("Phase C: zero-day deep pass (Hermes attack mode, 20 iter)",
               "PHASE")
        repo_dir = getattr(camp, "repo_path", str(ROOT_DIR)) if camp else str(ROOT_DIR)
        session = run_hermes_research(
            target_repo=target,
            repo_dir=repo_dir,
            focus_area=(
                "zero-day:exhaustive — prioritise unauthenticated RCE, "
                "deserialisation, prototype pollution, SSRF chains and "
                "supply-chain (lockfile / pre-commit) abuses.  Only return "
                "findings with ACTS ≥ 0.7 and a working PoC."
            ),
            max_iterations=int(os.getenv("EMBODIED_ZERODAY_ITER", "20")),
            progress_callback=lambda m: ms.log(m, "HERMES"),
        )
        try:
            ms.artifacts["zero_day_summary"] = get_session_summary(session)
        except Exception:  # noqa: BLE001
            ms.artifacts["zero_day_summary"] = {
                "session_id": getattr(session, "session_id", "?"),
                "findings"  : len(getattr(session, "findings", []) or []),
            }
        ms.log("zero-day deep pass done", "OK")
    except Exception as exc:  # noqa: BLE001
        ms.log(f"zero-day pass failed: {exc}", "WARN")

    ms.status   = "done"
    ms.ended_at = time.time()
    ms.log("mission complete", "DONE")


# ── Mission: BOUNTY ─────────────────────────────────────────────────────────
def _fetch_bounty_page(url: str, ms: MissionState) -> str:
    """
    Try the camofox-browser MCP first (anti-detection — preferred for
    HackerOne / Bugcrowd which sometimes 403 raw curl).  Fall back to
    plain ``requests`` so the mission still completes in dev.
    """
    # Camofox HTTP server is started by entrypoint.sh on :9377.  We hit
    # its sync /scrape endpoint if it exists; otherwise we just go to
    # plain requests.
    try:
        from camofox_client import CamofoxClient    # in-repo
        cli = CamofoxClient()
        if hasattr(cli, "scrape"):
            ms.log(f"camofox scrape → {url}", "CAMOFOX")
            html = cli.scrape(url)                  # type: ignore[attr-defined]
            if html:
                return html
    except Exception as exc:  # noqa: BLE001
        ms.log(f"camofox unavailable, falling back to requests: {exc}",
               "WARN")

    try:
        import requests
        ms.log(f"requests.get → {url}", "HTTP")
        r = requests.get(url, timeout=20, headers={
            "User-Agent": "Rhodawk-EmbodiedOS/1.0 (+bug-bounty research)",
        })
        r.raise_for_status()
        return r.text
    except Exception as exc:  # noqa: BLE001
        ms.log(f"page fetch failed: {exc}", "ERR")
        return ""


def _extract_scope(html: str) -> dict[str, list[str]]:
    """
    Crude but conservative scope extraction.  Returns:
        {"repos": ["owner/name", ...], "domains": ["foo.com", ...]}
    Repo extraction is exact (regex on github.com URLs).  Domain
    extraction is best-effort and de-duplicated; the operator can
    always trim it after the fact.
    """
    repos = []
    seen_repos: set[str] = set()
    for m in _GH_REPO_RE.finditer(html or ""):
        owner, name = m.group(1), m.group(2)
        # filter github's own static asset host etc.
        if owner.lower() in {"assets-cdn", "github-production-release-asset",
                              "raw.githubusercontent.com"}:
            continue
        slug = f"{owner}/{name}"
        if slug not in seen_repos:
            seen_repos.add(slug)
            repos.append(slug)

    domains: list[str] = []
    seen_dom: set[str] = set()
    for m in _DOMAIN_RE.finditer(html or ""):
        d = m.group(1).lower()
        # filter chrome/cdn/social noise
        if d.endswith((".png", ".jpg", ".svg", ".css", ".js")):
            continue
        if d in {"www.w3.org", "schema.org", "github.com", "hackerone.com",
                 "bugcrowd.com", "intigriti.com", "yeswehack.com"}:
            continue
        if d not in seen_dom:
            seen_dom.add(d)
            domains.append(d)

    # Hard cap to keep missions bounded; the operator can re-run with
    # a tighter URL if they want exhaustive coverage.
    return {"repos": repos[:25], "domains": domains[:50]}


def _phd_bounty_report(ms: MissionState, scope: dict[str, list[str]],
                       per_repo: list[dict[str, Any]]) -> str:
    """Render a submission-ready PhD-level Markdown briefing."""
    lines: list[str] = []
    lines.append(f"# Bug-Bounty Mission Report — `{ms.mission_id}`\n")
    lines.append(f"- **Source program:** {ms.target}")
    lines.append(f"- **Started:** "
                 f"{datetime.fromtimestamp(ms.started_at, timezone.utc).isoformat()}")
    if ms.ended_at:
        lines.append(f"- **Finished:** "
                     f"{datetime.fromtimestamp(ms.ended_at, timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## 1. Extracted Scope\n")
    lines.append(f"- **In-scope GitHub repos ({len(scope['repos'])}):** "
                 + (", ".join(f"`{r}`" for r in scope['repos']) or "_none_"))
    lines.append(f"- **Discovered domains ({len(scope['domains'])}):** "
                 + (", ".join(f"`{d}`" for d in scope['domains'][:15])
                    + (" …" if len(scope['domains']) > 15 else "")
                    or "_none_"))
    lines.append("")
    lines.append("## 2. Per-Target Audit Results\n")
    qualifying = 0
    for entry in per_repo:
        repo = entry["repo"]
        camp = entry.get("oss_campaign", {})
        findings = camp.get("findings", []) if isinstance(camp, dict) else []
        lines.append(f"### `{repo}`\n")
        lines.append(f"- mode: `{camp.get('mode', '?')}`  ·  "
                     f"findings: **{len(findings)}**  ·  "
                     f"error: `{camp.get('error', None)}`")
        for f in findings:
            sev = str(f.get("severity") or "P3").upper()
            mark = "✅ P1/P2" if sev in P_SEVERITY_FLOOR else "·"
            if sev in P_SEVERITY_FLOOR:
                qualifying += 1
            lines.append(f"  - {mark} **{f.get('title', '(untitled)')}** "
                         f"— sev=`{sev}` cwe=`{f.get('cwe', '?')}` "
                         f"acts=`{f.get('acts_score', '?')}`")
            if f.get("description"):
                lines.append(f"    > {str(f['description'])[:400]}")
            if f.get("proof_of_concept"):
                lines.append("    ```")
                lines.append(f"    {str(f['proof_of_concept'])[:1000]}")
                lines.append("    ```")
        lines.append("")
    lines.append(f"## 3. Submission-Ready Findings\n")
    lines.append(f"**{qualifying}** finding(s) meet the P1/P2 floor and are "
                 "ready to be queued for `bounty_gateway.submit_to_hackerone` "
                 "after operator approval (Rhodawk never auto-submits).")
    return "\n".join(lines)


def _run_mission_bounty(ms: MissionState) -> None:
    """End-to-end bug-bounty mission."""
    ms.status = "running"
    url = ms.target

    html = _fetch_bounty_page(url, ms)
    if not html:
        ms.status = "error"
        ms.error  = "could not fetch bounty page (camofox + requests both failed)"
        ms.log(ms.error, "ERR")
        ms.ended_at = time.time()
        return

    scope = _extract_scope(html)
    ms.artifacts["scope"] = scope
    ms.log(f"scope extracted: {len(scope['repos'])} repos, "
           f"{len(scope['domains'])} domains", "OK")

    per_repo: list[dict[str, Any]] = []
    for repo_slug in scope["repos"]:
        repo_url = f"https://github.com/{repo_slug}"
        ms.log(f"sub-mission → {repo_url}", "QUEUE")
        sub = _REGISTRY.create(kind="repo", target=repo_url)
        # Run in-thread so the bounty mission produces ONE consolidated
        # report; if the operator wants parallel they can fire
        # `mission repo` directly per slug.
        try:
            _run_mission_repo(sub)
        except Exception as exc:  # noqa: BLE001
            sub.status = "error"
            sub.error  = str(exc)
            sub.log(traceback.format_exc(), "ERR")
        per_repo.append({
            "repo": repo_slug,
            "mission_id": sub.mission_id,
            "oss_campaign": sub.artifacts.get("oss_campaign"),
            "zero_day_summary": sub.artifacts.get("zero_day_summary"),
        })

    report_md = _phd_bounty_report(ms, scope, per_repo)
    out_path  = MISSIONS_DIR / f"{ms.mission_id}-report.md"
    out_path.write_text(report_md, encoding="utf-8")
    ms.artifacts["report_md_path"] = str(out_path)
    ms.artifacts["report_md_excerpt"] = report_md[:4000]
    ms.log(f"PhD report written → {out_path}", "OK")

    ms.status   = "done"
    ms.ended_at = time.time()
    ms.log("bounty mission complete", "DONE")


# ── Mission: BRIEF ──────────────────────────────────────────────────────────
def _mission_brief() -> dict[str, Any]:
    """
    Synchronous status snapshot — heartbeat schedule, queue, skill
    counts, recent missions, meta-learner cycle log tail.
    """
    info: dict[str, Any] = {
        "version": "rhodawk-embodied-os-1.0",
        "now"    : datetime.now(timezone.utc).isoformat(),
    }
    # heartbeat schedule
    try:
        sched_path = ROOT_DIR / "openclaw_schedule.yaml"
        if sched_path.is_file():
            info["schedule_yaml_excerpt"] = sched_path.read_text(
                encoding="utf-8")[:1200]
    except Exception:  # noqa: BLE001
        pass
    # job queue
    try:
        import job_queue
        if hasattr(job_queue, "snapshot"):
            info["job_queue"] = job_queue.snapshot()
    except Exception:  # noqa: BLE001
        pass
    # skill stats
    try:
        from architect import skill_selector
        info["skills"] = skill_selector.stats()
    except Exception:  # noqa: BLE001
        pass
    # recent missions
    info["recent_missions"] = [m.summary() for m in _REGISTRY.list_recent(10)]
    # meta-learner tail
    try:
        log_path = Path(os.getenv("LOG_DIR", "/tmp")) / "meta_learner_daemon.log"
        if log_path.is_file():
            tail = log_path.read_text(encoding="utf-8").splitlines()[-20:]
            info["meta_learner_tail"] = tail
    except Exception:  # noqa: BLE001
        pass
    info["paused_night_hunt"] = bool(os.getenv("NIGHT_HUNTER_PAUSED"))
    return info


# ── Front-of-house dispatcher ───────────────────────────────────────────────
class EmbodiedOS:
    """
    Singleton-style wrapper.  Importing this module is enough — the
    intents are registered with openclaw_gateway at import time below.
    """

    @staticmethod
    def dispatch(text: str, *, user: str = "operator") -> dict[str, Any]:
        """
        Public NL entrypoint.  Resolution order:

          1. New mission verbs (mission repo / mission bounty /
             mission status / mission brief).
          2. Anything else → delegate to ``openclaw_gateway.handle_command``
             which preserves every existing intent (scan_repo, night_run_now,
             pause/resume, status, approve/reject/explain, help).
        """
        text = (text or "").strip()
        if not text:
            return {"ok": False, "intent": "noop",
                    "reply": "Empty command.", "data": None}

        # mission repo <url>
        m = re.match(r"^\s*mission\s+repo\s+(?P<u>\S+)", text, re.I)
        if m:
            ms = _REGISTRY.create(kind="repo", target=m.group("u"))
            threading.Thread(
                target=_run_mission_repo, args=(ms,),
                daemon=True, name=f"mission-{ms.mission_id}",
            ).start()
            return {"ok": True, "intent": "mission_repo",
                    "reply": (f"Mission {ms.mission_id} queued for "
                              f"{ms.target}. Poll with "
                              f"`mission status {ms.mission_id}`."),
                    "data": ms.summary()}

        # mission bounty <url>
        m = re.match(r"^\s*mission\s+bounty\s+(?P<u>\S+)", text, re.I)
        if m:
            ms = _REGISTRY.create(kind="bounty", target=m.group("u"))
            threading.Thread(
                target=_run_mission_bounty, args=(ms,),
                daemon=True, name=f"mission-{ms.mission_id}",
            ).start()
            return {"ok": True, "intent": "mission_bounty",
                    "reply": (f"Bounty mission {ms.mission_id} queued for "
                              f"{ms.target}. Final PhD report will land in "
                              f"{MISSIONS_DIR}."),
                    "data": ms.summary()}

        # mission status <id>
        m = re.match(r"^\s*mission\s+status\s+(?P<id>\S+)", text, re.I)
        if m:
            ms = _REGISTRY.get(m.group("id"))
            if not ms:
                return {"ok": False, "intent": "mission_status",
                        "reply": f"No mission with id={m.group('id')}.",
                        "data": None}
            return {"ok": True, "intent": "mission_status",
                    "reply": "\n".join(ms.transcript[-15:]),
                    "data": ms.summary()}

        # mission brief
        if re.match(r"^\s*mission\s+brief\b", text, re.I):
            info = _mission_brief()
            reply_lines = [
                f"EmbodiedOS @ {info['now']}",
                f"  skills      : {info.get('skills', {}).get('total_skills', '?')}",
                f"  recent miss.: {len(info.get('recent_missions', []))}",
                f"  night-hunt  : {'PAUSED' if info.get('paused_night_hunt') else 'armed'}",
            ]
            return {"ok": True, "intent": "mission_brief",
                    "reply": "\n".join(reply_lines), "data": info}

        # mission list
        if re.match(r"^\s*mission\s+list\b", text, re.I):
            recent = [m.summary() for m in _REGISTRY.list_recent(20)]
            return {"ok": True, "intent": "mission_list",
                    "reply": "\n".join(
                        f"  {x['mission_id']:24s}  {x['kind']:6s}  "
                        f"{x['status']:8s}  {x['target']}"
                        for x in recent
                    ) or "(no missions yet)",
                    "data": recent}

        # ── Fallback to OpenClaw — preserves every existing intent ───
        try:
            from openclaw_gateway import handle_command
            return handle_command(text, user=user)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "intent": "error",
                    "reply": f"openclaw fallback failed: {exc}",
                    "data": None}


# ── Self-registration with OpenClaw so HTTP + Telegram get the missions ─────
def _register_with_openclaw() -> None:
    try:
        import openclaw_gateway as oc

        @oc.register("mission_repo",
                     r"^\s*mission\s+repo\s+(?P<u>\S+)",
                     help="mission repo <url> — clone, fix tests, "
                          "break/refix, PR, then full zero-day pass")
        def _h_mission_repo(m):  # type: ignore[no-redef]
            return EmbodiedOS.dispatch(f"mission repo {m.group('u')}")

        @oc.register("mission_bounty",
                     r"^\s*mission\s+bounty\s+(?P<u>\S+)",
                     help="mission bounty <url> — scrape program, "
                          "audit every in-scope repo, render PhD P1/P2 report")
        def _h_mission_bounty(m):  # type: ignore[no-redef]
            return EmbodiedOS.dispatch(f"mission bounty {m.group('u')}")

        @oc.register("mission_status",
                     r"^\s*mission\s+status\s+(?P<id>\S+)",
                     help="mission status <id> — live transcript of a mission")
        def _h_mission_status(m):  # type: ignore[no-redef]
            return EmbodiedOS.dispatch(f"mission status {m.group('id')}")

        @oc.register("mission_brief",
                     r"^\s*mission\s+brief\b",
                     help="mission brief — heartbeat / what is Rhodawk doing")
        def _h_mission_brief(_m):  # type: ignore[no-redef]
            return EmbodiedOS.dispatch("mission brief")

        @oc.register("mission_list",
                     r"^\s*mission\s+list\b",
                     help="mission list — recent EmbodiedOS missions")
        def _h_mission_list(_m):  # type: ignore[no-redef]
            return EmbodiedOS.dispatch("mission list")

        LOG.info("EmbodiedOS missions registered with openclaw_gateway")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("openclaw registration deferred: %s", exc)


_register_with_openclaw()


# ── CLI for quick manual smoke tests ────────────────────────────────────────
if __name__ == "__main__":  # pragma: no cover
    import sys
    logging.basicConfig(level=logging.INFO)
    cmd = " ".join(sys.argv[1:]) or "mission brief"
    print(json.dumps(EmbodiedOS.dispatch(cmd), indent=2, default=str))
