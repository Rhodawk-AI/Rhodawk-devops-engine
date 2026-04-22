"""
oss_guardian.py — OSS Zero-Day Pipeline (Masterplan §2.5).

Glues the existing primitives together end-to-end:

    repo_harvester  →  oss_target_scorer  →  architect.sandbox  →
    language_runtime  →  hermes_orchestrator  →  disclosure_vault  →
    embodied_bridge

The module is designed so each stage can be stubbed for tests.  The
production entry point is ``OSSGuardian().run(repo_url)``.

Run as a module:

    python -m oss_guardian --repo https://github.com/nodejs/node
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOG = logging.getLogger("oss_guardian")


@dataclass
class OSSCampaign:
    repo_url: str
    mode: str            # "fix" | "attack"
    findings: list[dict] = field(default_factory=list)
    pr_url: str | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ── Lazy stage helpers (kept tiny so this module typechecks alone) ─────────
def _open_sandbox(repo_url: str):
    from architect import sandbox
    return sandbox.open_sandbox(repo_url)


def _detect_runtime(repo_path: str):
    from language_runtime import detect_runtime
    return detect_runtime(repo_path)


def _hermes_attack(repo_path: str, language: str):
    from hermes_orchestrator import run_hermes_research
    return run_hermes_research(target_repo=repo_path,
                               focus_area=f"oss-guardian:{language}",
                               max_iterations=6)


def _route_disclosure(finding: dict) -> dict:
    """Route a finding to the right submission lane."""
    sev = str(finding.get("severity", "P3")).upper()
    cve = finding.get("cve_id")
    acts = float(finding.get("acts_score", 0.0))
    if acts < 0.80 or sev not in ("P1", "P2"):
        return {"lane": "skip", "reason": "below-quality-gate"}
    if cve:
        return {"lane": "github_pr", "reason": "existing CVE"}
    return {"lane": "disclosure_vault", "reason": "novel zero-day"}


# ── Main runner ────────────────────────────────────────────────────────────
class OSSGuardian:
    """Autonomous open-source vulnerability research runner."""

    def __init__(self, *, attack_only: bool = False, fix_only: bool = False):
        self.attack_only = attack_only
        self.fix_only = fix_only

    # public entry
    def run(self, repo_url: str) -> OSSCampaign:
        camp = OSSCampaign(repo_url=repo_url, mode="attack")
        try:
            with _open_sandbox(repo_url) as sbx:
                repo_path = getattr(sbx, "repo_path", None) or str(sbx)
                runtime = _detect_runtime(repo_path)
                camp.notes.append(f"runtime:{getattr(runtime, 'language', '?')}")

                # 1) Run the project's own test suite; failing tests = fix mode.
                test_result = self._safe_run_tests(runtime)
                if not self.attack_only and test_result.get("failures"):
                    camp.mode = "fix"
                    camp.notes.append(
                        f"test-suite has {len(test_result['failures'])} failure(s) — entering fix mode"
                    )
                    pr = self._fix_mode(repo_path, runtime, test_result)
                    camp.pr_url = pr
                    return camp

                # 2) Tests pass → full Hermes attack run.
                if self.fix_only:
                    camp.notes.append("fix-only mode requested but no failures found")
                    return camp

                session = _hermes_attack(repo_path, getattr(runtime, "language", "unknown"))
                findings = self._extract_findings(session)
                camp.findings = findings
                self._route_findings(findings, camp)
        except Exception as exc:  # noqa: BLE001
            LOG.exception("OSSGuardian crashed on %s: %s", repo_url, exc)
            camp.error = str(exc)
        return camp

    # ── internals ──────────────────────────────────────────────────────────
    def _safe_run_tests(self, runtime) -> dict[str, Any]:
        try:
            r = runtime.run_tests()
            if hasattr(r, "to_dict"):
                return r.to_dict()
            return dict(r) if isinstance(r, dict) else {"failures": []}
        except Exception as exc:  # noqa: BLE001
            LOG.warning("test-suite run failed: %s", exc)
            return {"failures": [], "error": str(exc)}

    def _fix_mode(self, repo_path: str, runtime, test_result: dict) -> str | None:
        try:
            from hermes_orchestrator import run_hermes_research
            session = run_hermes_research(
                target_repo=repo_path,
                focus_area="oss-guardian:fix-failing-tests",
                max_iterations=3,
            )
            return getattr(session, "pr_url", None)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("fix-mode failed: %s", exc)
            return None

    def _extract_findings(self, session) -> list[dict]:
        out: list[dict] = []
        for f in getattr(session, "findings", []) or []:
            if dataclasses.is_dataclass(f):
                out.append(dataclasses.asdict(f))
            elif isinstance(f, dict):
                out.append(f)
            else:
                out.append({"raw": repr(f)})
        return out

    def _route_findings(self, findings: list[dict], camp: OSSCampaign) -> None:
        try:
            from architect import embodied_bridge
            from architect.embodied_bridge import FindingPayload
        except Exception:  # noqa: BLE001
            embodied_bridge = None
            FindingPayload = None  # type: ignore[assignment]
        try:
            import disclosure_vault  # type: ignore
        except Exception:  # noqa: BLE001
            disclosure_vault = None

        for f in findings:
            decision = _route_disclosure(f)
            f["routing"] = decision
            if decision["lane"] == "disclosure_vault" and disclosure_vault is not None:
                try:
                    disclosure_vault.intake(f, source="oss_guardian")  # type: ignore[attr-defined]
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("disclosure_vault.intake failed: %s", exc)
            if embodied_bridge is not None and FindingPayload is not None:
                try:
                    payload = FindingPayload(
                        finding_id=str(f.get("finding_id") or f.get("id") or "?"),
                        title=str(f.get("title") or "(untitled)"),
                        severity=str(f.get("severity") or "P3"),
                        cwe=str(f.get("cwe") or "?"),
                        repo=camp.repo_url,
                        file_path=str(f.get("file_path") or ""),
                        description=str(f.get("description") or ""),
                        proof_of_concept=str(f.get("proof_of_concept") or ""),
                        acts_score=float(f.get("acts_score") or 0.0),
                    )
                    embodied_bridge.emit_finding(payload)
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("embodied_bridge.emit_finding failed: %s", exc)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="oss_guardian")
    ap.add_argument("--repo", required=True, help="GitHub repo URL or local path")
    ap.add_argument("--attack-only", action="store_true")
    ap.add_argument("--fix-only", action="store_true")
    ap.add_argument("--out", help="Write campaign JSON to this path")
    args = ap.parse_args(argv)

    g = OSSGuardian(attack_only=args.attack_only, fix_only=args.fix_only)
    camp = g.run(args.repo)
    js = camp.to_json()
    if args.out:
        Path(args.out).write_text(__import__("json").dumps(js, indent=2))
    else:
        print(__import__("json").dumps(js, indent=2))
    return 0 if not camp.error else 1


if __name__ == "__main__":
    raise SystemExit(main())
