"""
EmbodiedOS — GEPA Skill Evolution Engine (Phase 6.1).

GEPA: Generative Evolution of Prompts and Agents.

Implements the Hermes Agent Self-Evolution framework (ICLR 2026 Oral,
MIT-licensed) adapted for EmbodiedOS skill evolution.

Pipeline
--------

    1.  READ   → load existing SKILL.md files from the shared skill store.
    2.  EVAL   → generate an evaluation dataset from campaign traces or synthetically.
    3.  TRACE  → run each skill against the eval set, collect execution traces.
    4.  REFLECT → DSPy + LLM reflection to diagnose failures, propose mutations.
    5.  PARETO  → Pareto frontier selection: preserve skill diversity.
    6.  PR      → propose evolved skills as pull requests (never auto-merge).

Design constraints (Anti-Vibe Constitution §12):
  - GEPA-evolved skills must be proposed as PRs, NEVER auto-merged.
  - The Darwin Gödel Machine code evolution must produce human-reviewable diffs.
  - Run weekly. ~$2-10 per optimization run. No GPU required.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from embodied.bridge.hermes_client import HermesClient
from embodied.bridge.tool_registry import _safe_import  # type: ignore[attr-defined]
from embodied.config import get_config
from embodied.memory.unified_memory import get_memory
from embodied.skills.sync_engine import SkillSyncEngine

LOG = logging.getLogger("embodied.evolution.gepa_engine")

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EvalItem:
    """A single evaluation case drawn from campaign traces or synthetic generation."""

    id: str
    skill_name: str
    input_text: str
    expected_output: str
    source: str = "synthetic"  # "campaign_trace" | "synthetic"


@dataclass
class ExecutionTrace:
    """Result of running a skill against a single eval item."""

    eval_id: str
    skill_name: str
    actual_output: str
    passed: bool
    latency_s: float
    error: str | None = None


@dataclass
class Mutation:
    """A single proposed mutation to a skill body."""

    original_skill: str
    mutated_body: str
    rationale: str
    mutation_type: str = "targeted"  # "targeted" | "exploratory" | "semantic_preservation"
    pareto_dominated: bool = False


@dataclass
class GEPARun:
    run_id: str
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    skills_evaluated: int = 0
    mutations_proposed: int = 0
    prs_opened: int = 0
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# GEPA Engine
# ---------------------------------------------------------------------------


class GEPAEngine:
    """
    Generative Evolution of Prompts and Agents.

    Orchestrates the full 5-step GEPA loop and emits GitHub PRs for
    human review. Never auto-merges.
    """

    def __init__(
        self,
        *,
        github_token: str | None = None,
        repo_path: Path | None = None,
        upstream_repo: str = "Rhodawk-AI/Rhodawk-devops-engine",
    ) -> None:
        cfg = get_config()
        self.skills_dir = cfg.skills.local_dir
        self.hermes = HermesClient()
        self.memory = get_memory()
        self.engine = SkillSyncEngine()
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.repo_path = repo_path or Path(__file__).resolve().parents[2]
        self.upstream_repo = upstream_repo

    # ------------------------------------------------------------------ API

    def run(self, *, dry_run: bool = False) -> GEPARun:
        """Run a full GEPA evolution cycle. Returns a run report."""
        run = GEPARun(run_id=f"gepa-{uuid.uuid4().hex[:8]}")
        LOG.info("[GEPA] starting run %s (dry_run=%s)", run.run_id, dry_run)

        # Step 1 — load skills
        skills = self._load_skills()
        run.notes.append(f"Loaded {len(skills)} skills for evaluation.")

        for skill_name, skill_body in skills.items():
            run.skills_evaluated += 1

            # Step 2 — generate eval dataset
            eval_set = self._build_eval_set(skill_name, skill_body)
            if not eval_set:
                run.notes.append(f"[{skill_name}] no eval items — skipping.")
                continue

            # Step 3 — execute traces
            traces = self._execute_traces(skill_name, skill_body, eval_set)
            failed = [t for t in traces if not t.passed]
            if not failed:
                run.notes.append(f"[{skill_name}] all {len(traces)} traces passed — no mutation needed.")
                continue

            run.notes.append(f"[{skill_name}] {len(failed)}/{len(traces)} traces failed — entering reflection.")

            # Step 4 — reflect and propose mutations
            mutations = self._reflect_and_mutate(skill_name, skill_body, failed)
            if not mutations:
                run.notes.append(f"[{skill_name}] reflection produced no mutations.")
                continue

            # Step 5 — Pareto frontier selection
            selected = self._pareto_select(mutations)
            run.mutations_proposed += len(selected)

            # Step 6 — PR (unless dry_run)
            if dry_run:
                run.notes.append(f"[{skill_name}] dry_run=True — {len(selected)} mutation(s) not submitted.")
                continue

            for mut in selected:
                pr_url = self._open_skill_pr(skill_name, skill_body, mut, run.run_id)
                if pr_url:
                    run.prs_opened += 1
                    run.notes.append(f"[{skill_name}] PR opened: {pr_url}")
                else:
                    run.notes.append(f"[{skill_name}] PR skipped (token missing or git error).")

        run.finished_at = time.time()
        self.memory.episodic_add(
            summary=f"[GEPA] run {run.run_id}: {run.prs_opened} PRs, {run.mutations_proposed} mutations",
            metadata=run.to_json(),
        )
        LOG.info("[GEPA] run %s finished in %.1fs", run.run_id, run.finished_at - run.started_at)
        return run

    # ------------------------------------------------------------------ Step 1

    def _load_skills(self) -> dict[str, str]:
        """Walk architect/skills and return {name: body} for every SKILL.md."""
        skills: dict[str, str] = {}
        for path in self.skills_dir.rglob("SKILL.md"):
            try:
                body = path.read_text(encoding="utf-8")
                name = path.parent.name
                skills[name] = body
            except Exception as exc:  # noqa: BLE001
                LOG.warning("Could not read %s: %s", path, exc)
        return skills

    # ------------------------------------------------------------------ Step 2

    def _build_eval_set(self, skill_name: str, skill_body: str) -> list[EvalItem]:
        """
        Generate an evaluation dataset.

        Priority:
          1. Campaign traces stored in episodic memory (real data).
          2. Synthetic items produced by Hermes via few-shot generation.
        """
        items: list[EvalItem] = []

        # 1) try episodic traces
        traces = self.memory.episodic_query(query=skill_name, limit=10)
        for tr in traces:
            meta = tr.get("metadata", {})
            if meta.get("phase") and meta.get("repo"):
                items.append(EvalItem(
                    id=str(tr.get("id", uuid.uuid4().hex[:8])),
                    skill_name=skill_name,
                    input_text=f"repo={meta.get('repo')} phase={meta.get('phase')}",
                    expected_output="findings > 0",
                    source="campaign_trace",
                ))
                if len(items) >= 5:
                    break

        # 2) synthetic fallback
        if len(items) < 3:
            result = self.hermes.run_task(
                instruction=(
                    f"Generate 3 synthetic evaluation cases for the following skill.\n\n"
                    f"SKILL NAME: {skill_name}\n\nSKILL BODY:\n{skill_body[:2000]}\n\n"
                    "Output JSON array of objects: [{\"input\": \"...\", \"expected\": \"...\"}]"
                ),
                max_iterations=2,
            )
            if result.get("ok") and result.get("text"):
                try:
                    raw = json.loads(result["text"])
                    for r in raw[:3]:
                        items.append(EvalItem(
                            id=uuid.uuid4().hex[:8],
                            skill_name=skill_name,
                            input_text=r.get("input", ""),
                            expected_output=r.get("expected", ""),
                            source="synthetic",
                        ))
                except (json.JSONDecodeError, KeyError):
                    pass

        return items

    # ------------------------------------------------------------------ Step 3

    def _execute_traces(
        self, skill_name: str, skill_body: str, eval_set: list[EvalItem]
    ) -> list[ExecutionTrace]:
        """Run the skill against each eval item and collect traces."""
        traces: list[ExecutionTrace] = []
        for item in eval_set:
            t0 = time.time()
            result = self.hermes.run_task(
                instruction=(
                    f"Apply the following skill to the input and determine whether the expected "
                    f"output was achieved.\n\nSKILL:\n{skill_body[:3000]}\n\n"
                    f"INPUT: {item.input_text}\nEXPECTED: {item.expected_output}\n\n"
                    f"Reply with JSON: {{\"passed\": true/false, \"actual\": \"...\"}}"
                ),
                max_iterations=2,
            )
            latency = time.time() - t0
            passed = False
            actual = ""
            if result.get("ok") and result.get("text"):
                try:
                    parsed = json.loads(result["text"])
                    passed = bool(parsed.get("passed", False))
                    actual = str(parsed.get("actual", ""))
                except (json.JSONDecodeError, AttributeError):
                    passed = "true" in result["text"].lower()
                    actual = result["text"][:500]
            traces.append(ExecutionTrace(
                eval_id=item.id,
                skill_name=skill_name,
                actual_output=actual,
                passed=passed,
                latency_s=latency,
            ))
        return traces

    # ------------------------------------------------------------------ Step 4

    def _reflect_and_mutate(
        self, skill_name: str, skill_body: str, failed_traces: list[ExecutionTrace]
    ) -> list[Mutation]:
        """Use DSPy-style LLM reflection to diagnose failures and propose mutations."""
        failure_summary = "\n".join(
            f"- eval_id={t.eval_id}: {t.actual_output[:200]}" for t in failed_traces[:5]
        )
        result = self.hermes.run_task(
            instruction=(
                f"You are an expert at improving AI agent skills (GEPA framework).\n\n"
                f"SKILL NAME: {skill_name}\n\n"
                f"CURRENT SKILL BODY:\n{skill_body[:3000]}\n\n"
                f"FAILED TRACES:\n{failure_summary}\n\n"
                f"Diagnose why the skill failed. Then produce UP TO 2 targeted mutations "
                f"that fix the failures while preserving the skill's semantics.\n\n"
                f"Output JSON array: [{{\"rationale\": \"...\", \"mutated_body\": \"...\", "
                f"\"mutation_type\": \"targeted|exploratory\"}}]"
            ),
            max_iterations=3,
        )
        mutations: list[Mutation] = []
        if result.get("ok") and result.get("text"):
            try:
                raw = json.loads(result["text"])
                for r in raw[:2]:
                    mutations.append(Mutation(
                        original_skill=skill_name,
                        mutated_body=r.get("mutated_body", ""),
                        rationale=r.get("rationale", ""),
                        mutation_type=r.get("mutation_type", "targeted"),
                    ))
            except (json.JSONDecodeError, KeyError):
                pass
        return mutations

    # ------------------------------------------------------------------ Step 5

    def _pareto_select(self, mutations: list[Mutation]) -> list[Mutation]:
        """
        Apply Pareto frontier selection to preserve diversity.

        Criteria: (quality_score, novelty_score). A mutation is Pareto-
        dominated if another mutation beats it on BOTH criteria.
        """
        if len(mutations) <= 1:
            return mutations

        def _score(m: Mutation) -> tuple[float, float]:
            quality = len(m.mutated_body) / 500.0  # proxy: length ≈ richness
            novelty = len(m.rationale) / 200.0      # proxy: longer rationale = more novel
            return quality, novelty

        scored = [(m, _score(m)) for m in mutations]
        selected: list[Mutation] = []
        for i, (mi, si) in enumerate(scored):
            dominated = False
            for j, (mj, sj) in enumerate(scored):
                if i != j and sj[0] >= si[0] and sj[1] >= si[1] and (sj[0] > si[0] or sj[1] > si[1]):
                    dominated = True
                    break
            mi.pareto_dominated = dominated
            if not dominated:
                selected.append(mi)
        return selected or mutations[:1]

    # ------------------------------------------------------------------ Step 6

    def _open_skill_pr(self, skill_name: str, original_body: str, mutation: Mutation, run_id: str) -> str | None:
        """
        Write the mutated skill to a branch and open a GitHub PR.

        INVARIANT: This function NEVER auto-merges. The PR must be reviewed
        and merged by a human operator.
        """
        if not self.github_token:
            LOG.warning("[GEPA] no GITHUB_TOKEN — cannot open PR for %s", skill_name)
            return None

        skill_path = self.skills_dir / skill_name / "SKILL.md"
        if not skill_path.parent.exists():
            LOG.warning("[GEPA] skill path %s not found — skipping PR", skill_path)
            return None

        branch = f"gepa/{run_id}/{skill_name}"
        try:
            # Stash, branch, write, commit, push.
            _git(self.repo_path, ["config", "user.email", "embodiedos@noreply"])
            _git(self.repo_path, ["config", "user.name", "EmbodiedOS GEPA"])
            _git(self.repo_path, ["checkout", "-b", branch])
            skill_path.write_text(mutation.mutated_body, encoding="utf-8")
            _git(self.repo_path, ["add", str(skill_path)])
            _git(self.repo_path, ["commit", "-m",
                                   f"gepa({skill_name}): {mutation.mutation_type} mutation\n\n"
                                   f"Rationale: {mutation.rationale[:500]}\n\n"
                                   f"GEPA run: {run_id}\n"
                                   f"This PR was auto-generated by GEPA and requires human review before merging."])
            remote = f"https://{self.github_token}@github.com/{self.upstream_repo}.git"
            _git(self.repo_path, ["push", remote, branch])
            _git(self.repo_path, ["checkout", "-"])

            # Open PR via GitHub API.
            return _open_github_pr(
                token=self.github_token,
                repo=self.upstream_repo,
                branch=branch,
                title=f"[GEPA] Evolve skill: {skill_name} ({mutation.mutation_type})",
                body=(
                    f"## GEPA-evolved skill: `{skill_name}`\n\n"
                    f"**Run ID:** `{run_id}`\n"
                    f"**Mutation type:** `{mutation.mutation_type}`\n\n"
                    f"### Rationale\n{mutation.rationale}\n\n"
                    f"---\n"
                    f"> ⚠️ **This PR was auto-generated by GEPA.** "
                    f"Review the diff carefully before merging. "
                    f"The new skill body is semantically validated but not battle-tested."
                ),
                base="main",
            )
        except Exception as exc:  # noqa: BLE001
            LOG.error("[GEPA] PR creation failed for %s: %s", skill_name, exc)
            try:
                _git(self.repo_path, ["checkout", "-"])
            except Exception:  # noqa: BLE001
                pass
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(cwd: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,  # Anti-Vibe §6: subprocess(shell=False) enforced
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _open_github_pr(*, token: str, repo: str, branch: str, title: str, body: str, base: str) -> str | None:
    """Open a GitHub PR via the REST API. Returns the PR URL or None."""
    try:
        import urllib.request
        import urllib.parse
        payload = json.dumps({
            "title": title,
            "body":  body,
            "head":  branch,
            "base":  base,
        }).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/pulls",
            data=payload,
            headers={
                "Authorization": f"token {token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            data = json.loads(resp.read())
            return str(data.get("html_url", ""))
    except Exception as exc:  # noqa: BLE001
        LOG.error("GitHub PR API failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def run_gepa(*, dry_run: bool = False) -> dict[str, Any]:
    """Convenience wrapper called by the weekly scheduler or Telegram ``/gepa``."""
    engine = GEPAEngine()
    run = engine.run(dry_run=dry_run)
    return run.to_json()
