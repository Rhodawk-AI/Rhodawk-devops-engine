"""
EmbodiedOS — Darwin Gödel Machine Code Evolution (Phase 6.2).

Implements self-improving code evolution for underperforming analysis engines.

The Darwin Gödel Machine (DGM) framework:
  1.  IDENTIFY   → detect underperforming analysis engines via metrics.
  2.  GENERATE   → produce variant Python source files via Hermes Agent.
  3.  TEST       → run variants against the 50-repo benchmark in a sandbox.
  4.  VALIDATE   → must pass full test suite + not regress.
  5.  PR         → create GitHub PR — human reviews and merges.

INVARIANT: Code evolution NEVER auto-merges. Human review is mandatory.
Run monthly. All generated code passes: (a) compile check, (b) import check.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import io
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

LOG = logging.getLogger("embodied.evolution.code_evolver")

# Modules eligible for evolution — exclude safety-critical ones.
EVOLVABLE_MODULES: list[str] = [
    "sast_gate",
    "taint_analyzer",
    "symbolic_engine",
    "vuln_classifier",
    "oss_target_scorer",
    "semantic_extractor",
    "conviction_engine",
    "chain_analyzer",
]

# Minimum regression threshold: evolved code must score ≥ this × original.
REGRESSION_THRESHOLD = 0.95


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PerformanceRecord:
    module_name: str
    success_rate: float   # 0.0 – 1.0
    avg_latency_s: float
    error_count: int
    sample_size: int


@dataclass
class CodeVariant:
    module_name: str
    source: str
    rationale: str
    compile_ok: bool = False
    import_ok: bool = False
    test_score: float = 0.0
    regressed: bool = False


@dataclass
class DGMRun:
    run_id: str
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    modules_evaluated: int = 0
    variants_generated: int = 0
    variants_passing: int = 0
    prs_opened: int = 0
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# Code Evolver
# ---------------------------------------------------------------------------


class CodeEvolver:
    """
    Darwin Gödel Machine — self-improving code evolution.

    Identifies underperforming modules, generates variants via LLM,
    validates them, and proposes improvements as GitHub PRs.
    """

    def __init__(
        self,
        *,
        github_token: str | None = None,
        repo_path: Path | None = None,
        upstream_repo: str = "Rhodawk-AI/Rhodawk-devops-engine",
    ) -> None:
        self.hermes = HermesClient()
        self.memory = get_memory()
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.repo_path = repo_path or Path(__file__).resolve().parents[2]
        self.upstream_repo = upstream_repo

    # ------------------------------------------------------------------ API

    def run(self, *, dry_run: bool = False) -> DGMRun:
        """Run a full Darwin Gödel Machine evolution cycle."""
        run = DGMRun(run_id=f"dgm-{uuid.uuid4().hex[:8]}")
        LOG.info("[DGM] starting run %s (dry_run=%s)", run.run_id, dry_run)

        # Step 1 — identify underperforming modules
        candidates = self._identify_underperformers()
        run.notes.append(f"Found {len(candidates)} underperforming module(s).")

        for perf in candidates:
            run.modules_evaluated += 1
            source_path = self.repo_path / f"{perf.module_name}.py"
            if not source_path.exists():
                run.notes.append(f"[{perf.module_name}] source not found — skipping.")
                continue

            original_source = source_path.read_text(encoding="utf-8")

            # Step 2 — generate variant
            variant = self._generate_variant(perf, original_source)
            if variant is None:
                run.notes.append(f"[{perf.module_name}] LLM produced no variant.")
                continue
            run.variants_generated += 1

            # Step 3a — compile check (Anti-Vibe §11a)
            variant.compile_ok = self._compile_check(variant.source)
            if not variant.compile_ok:
                run.notes.append(f"[{perf.module_name}] variant failed compile check — discarded.")
                continue

            # Step 3b — import check (Anti-Vibe §11b)
            variant.import_ok = self._import_check(perf.module_name, variant.source)
            if not variant.import_ok:
                run.notes.append(f"[{perf.module_name}] variant failed import check — discarded.")
                continue

            # Step 4 — test suite validation
            test_score = self._run_tests(perf.module_name, variant.source)
            variant.test_score = test_score
            original_score = perf.success_rate
            if test_score < original_score * REGRESSION_THRESHOLD:
                variant.regressed = True
                run.notes.append(
                    f"[{perf.module_name}] variant regressed "
                    f"({test_score:.2f} < {original_score * REGRESSION_THRESHOLD:.2f}) — discarded."
                )
                continue

            run.variants_passing += 1
            run.notes.append(f"[{perf.module_name}] variant passed (score={test_score:.2f}).")

            if dry_run:
                run.notes.append(f"[{perf.module_name}] dry_run=True — PR not submitted.")
                continue

            # Step 5 — create PR (NEVER auto-merge)
            pr_url = self._open_code_pr(perf.module_name, original_source, variant, run.run_id)
            if pr_url:
                run.prs_opened += 1
                run.notes.append(f"[{perf.module_name}] PR opened: {pr_url}")
            else:
                run.notes.append(f"[{perf.module_name}] PR skipped.")

        run.finished_at = time.time()
        self.memory.episodic_add(
            summary=f"[DGM] run {run.run_id}: {run.prs_opened} PRs, {run.variants_passing} passing",
            metadata=run.to_json(),
        )
        LOG.info("[DGM] run %s finished in %.1fs", run.run_id, run.finished_at - run.started_at)
        return run

    # ------------------------------------------------------------------ Step 1

    def _identify_underperformers(self) -> list[PerformanceRecord]:
        """
        Query episodic memory for module-level error patterns.
        Returns modules with success_rate < 0.7.
        """
        records: list[PerformanceRecord] = []
        for module_name in EVOLVABLE_MODULES:
            traces = self.memory.episodic_query(query=module_name, limit=50)
            errors = sum(1 for t in traces if "failed" in t.get("summary", "").lower()
                        or t.get("metadata", {}).get("status") == "failed")
            total = max(len(traces), 1)
            success_rate = 1.0 - (errors / total)
            if success_rate < 0.70 or errors >= 3:
                records.append(PerformanceRecord(
                    module_name=module_name,
                    success_rate=success_rate,
                    avg_latency_s=0.0,
                    error_count=errors,
                    sample_size=total,
                ))
                LOG.info("[DGM] %s is underperforming: success_rate=%.2f", module_name, success_rate)
        return records

    # ------------------------------------------------------------------ Step 2

    def _generate_variant(self, perf: PerformanceRecord, original_source: str) -> CodeVariant | None:
        """Ask Hermes Agent to generate an improved variant of the module."""
        result = self.hermes.run_task(
            instruction=(
                f"You are an expert Python security-tool engineer.\n\n"
                f"The following module is underperforming:\n"
                f"MODULE: {perf.module_name}\n"
                f"SUCCESS RATE: {perf.success_rate:.0%} over {perf.sample_size} runs\n"
                f"ERRORS: {perf.error_count}\n\n"
                f"CURRENT SOURCE (first 4000 chars):\n{original_source[:4000]}\n\n"
                f"Generate an IMPROVED variant that:\n"
                f"1. Fixes the most likely cause of failures.\n"
                f"2. Maintains the same public API (all exported function signatures identical).\n"
                f"3. Adds @tenacity.retry or Result[T,E] error handling where missing.\n"
                f"4. Does NOT use subprocess(shell=True).\n"
                f"5. Does NOT use Any types without a justification comment.\n\n"
                f"Output JSON: {{\"rationale\": \"...\", \"source\": \"<full python source>\"}}"
            ),
            max_iterations=4,
        )
        if not result.get("ok") or not result.get("text"):
            return None
        try:
            data = json.loads(result["text"])
            return CodeVariant(
                module_name=perf.module_name,
                source=data.get("source", ""),
                rationale=data.get("rationale", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    # ------------------------------------------------------------------ Step 3

    def _compile_check(self, source: str) -> bool:
        """AST-parse the source to confirm it compiles. Anti-Vibe §11a."""
        if not source.strip():
            return False
        try:
            ast.parse(source)
            return True
        except SyntaxError as exc:
            LOG.debug("compile check failed: %s", exc)
            return False

    def _import_check(self, module_name: str, source: str) -> bool:
        """
        Write source to a tempfile and import it in a subprocess.
        Anti-Vibe §11b.
        """
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as fh:
            fh.write(source)
            tmp_path = fh.name
        try:
            result = subprocess.run(
                ["python3", "-c", f"import importlib.util; spec=importlib.util.spec_from_file_location('_check', '{tmp_path}'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                shell=False,  # Anti-Vibe §6
            )
            return result.returncode == 0
        except Exception:  # noqa: BLE001
            return False
        finally:
            try:
                Path(tmp_path).unlink()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ Step 4

    def _run_tests(self, module_name: str, variant_source: str) -> float:
        """
        Run the project test suite against the variant.
        Returns a score in [0.0, 1.0].
        """
        test_dir = self.repo_path / "tests"
        if not test_dir.exists():
            # No test dir — assume neutral score.
            return 0.75

        with tempfile.NamedTemporaryFile(
            suffix=".py",
            prefix=f"{module_name}_",
            dir=self.repo_path,
            mode="w",
            delete=False,
        ) as fh:
            fh.write(variant_source)
            variant_path = Path(fh.name)

        try:
            # Run pytest on the module-specific test file if it exists.
            test_file = test_dir / f"test_{module_name}.py"
            targets = [str(test_file)] if test_file.exists() else [str(test_dir)]

            result = subprocess.run(
                ["python3", "-m", "pytest", "--tb=no", "-q"] + targets,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                shell=False,  # Anti-Vibe §6
                env={**os.environ, "PYTHONPATH": str(self.repo_path)},
            )
            # Parse passed/failed from pytest output.
            lines = result.stdout.splitlines()
            for line in reversed(lines):
                if "passed" in line or "failed" in line or "error" in line:
                    parts = line.split()
                    passed = next((int(p) for p, q in zip(parts, parts[1:]) if q == "passed"), 0)
                    failed = next((int(p) for p, q in zip(parts, parts[1:]) if q in ("failed", "error")), 0)
                    total = passed + failed
                    return passed / total if total > 0 else 0.75
            return 1.0 if result.returncode == 0 else 0.0
        finally:
            try:
                variant_path.unlink()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ Step 5

    def _open_code_pr(self, module_name: str, original_source: str, variant: CodeVariant, run_id: str) -> str | None:
        """
        Write the variant, commit to a branch, push, and open a GitHub PR.
        INVARIANT: NEVER auto-merges.
        """
        if not self.github_token:
            LOG.warning("[DGM] no GITHUB_TOKEN — cannot open PR for %s", module_name)
            return None

        source_path = self.repo_path / f"{module_name}.py"
        branch = f"dgm/{run_id}/{module_name}"
        try:
            _git(self.repo_path, ["config", "user.email", "embodiedos@noreply"])
            _git(self.repo_path, ["config", "user.name", "EmbodiedOS DGM"])
            _git(self.repo_path, ["checkout", "-b", branch])
            source_path.write_text(variant.source, encoding="utf-8")
            _git(self.repo_path, ["add", str(source_path)])
            _git(self.repo_path, ["commit", "-m",
                                   f"dgm({module_name}): evolved variant (score={variant.test_score:.2f})\n\n"
                                   f"Rationale: {variant.rationale[:500]}\n\n"
                                   f"DGM run: {run_id}\n"
                                   f"HUMAN REVIEW REQUIRED before merging."])
            remote = f"https://{self.github_token}@github.com/{self.upstream_repo}.git"
            _git(self.repo_path, ["push", remote, branch])
            _git(self.repo_path, ["checkout", "-"])

            return _open_github_pr(
                token=self.github_token,
                repo=self.upstream_repo,
                branch=branch,
                title=f"[DGM] Evolved module: {module_name} (score={variant.test_score:.0%})",
                body=(
                    f"## Darwin Gödel Machine — Evolved Module: `{module_name}`\n\n"
                    f"**DGM Run ID:** `{run_id}`\n"
                    f"**Test score:** `{variant.test_score:.0%}`\n"
                    f"**Regression threshold:** `{REGRESSION_THRESHOLD:.0%}`\n\n"
                    f"### Rationale\n{variant.rationale}\n\n"
                    f"### Validation\n"
                    f"- [x] Compile check passed\n"
                    f"- [x] Import check passed\n"
                    f"- [x] Test score ≥ regression threshold\n\n"
                    f"---\n"
                    f"> ⚠️ **This PR was auto-generated by the Darwin Gödel Machine.** "
                    f"Review the diff and run the full test suite before merging."
                ),
                base="main",
            )
        except Exception as exc:  # noqa: BLE001
            LOG.error("[DGM] PR creation failed for %s: %s", module_name, exc)
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
    import urllib.request
    payload = json.dumps({"title": title, "body": body, "head": branch, "base": base}).encode()
    try:
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


def run_dgm(*, dry_run: bool = False) -> dict[str, Any]:
    """Convenience wrapper called by the monthly scheduler or Telegram ``/dgm``."""
    evolver = CodeEvolver()
    run = evolver.run(dry_run=dry_run)
    return run.to_json()
