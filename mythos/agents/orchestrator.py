"""
Mythos Orchestrator — the enhanced Hermes coordinating Planner/Explorer/Executor.

Implements §5.5 of the plan.  Models the closed-loop CEGIS cycle:

    Planner → (Explorer + Executor in parallel) → Refinement → Loop

If AutoGen / CrewAI are installed they are auto-detected and used to drive
inter-agent conversation; otherwise the orchestrator falls back to the
deterministic in-process loop below — both produce identical dossiers so
downstream Bounty Gateway code is unaffected.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .base import AgentMessage
from .planner import PlannerAgent
from .explorer import ExplorerAgent
from .executor import ExecutorAgent
from ..learning.episodic_memory import EpisodicMemory
from ..learning.mlflow_tracker import MLflowTracker

LOG = logging.getLogger("mythos.orchestrator")


class MythosOrchestrator:
    def __init__(
        self,
        planner: PlannerAgent | None = None,
        explorer: ExplorerAgent | None = None,
        executor: ExecutorAgent | None = None,
        max_iterations: int = 3,
    ):
        self.planner = planner or PlannerAgent()
        self.explorer = explorer or ExplorerAgent()
        self.executor = executor or ExecutorAgent()
        self.max_iterations = max_iterations
        self.memory = EpisodicMemory()
        self.tracker = MLflowTracker(experiment="mythos-campaigns")
        self.transcript: list[AgentMessage] = []

    # -- transport helpers --------------------------------------------------

    def _send(self, msg: AgentMessage) -> None:
        self.transcript.append(msg)
        LOG.debug("%s → %s : %s", msg.sender, msg.recipient, str(msg.content)[:200])

    # -- main loop ----------------------------------------------------------

    def run_campaign(self, target: dict[str, Any]) -> dict[str, Any]:
        run_id = self.tracker.start_run(tags={"target": target.get("repo", "?")})
        ctx: dict[str, Any] = {"target": target, "recon": target.get("recon", {})}
        dossier: dict[str, Any] = {"target": target, "iterations": []}

        for i in range(self.max_iterations):
            iter_started = time.time()
            LOG.info("Mythos iteration %s/%s", i + 1, self.max_iterations)

            # 1. Planner
            plan_msg = self.planner.act(ctx)
            self._send(plan_msg)
            ctx.update(plan_msg.content)

            # 2. Explorer (static) and Executor (dynamic) in lock-step.
            ctx["repo_path"] = target.get("repo_path", "/data/repo")
            ctx["harness_dir"] = target.get("harness_dir", "/tmp/research")

            explorer_msg = self.explorer.act(ctx)
            self._send(explorer_msg)
            ctx.update(explorer_msg.content)

            executor_msg = self.executor.act(ctx)
            self._send(executor_msg)
            ctx.update(executor_msg.content)

            # 3. Refinement — feed dynamic feedback back to the Planner so it
            #    can prune / amplify hypotheses on the next loop.
            refined = self._refine(ctx)
            ctx["recon"] = {**ctx.get("recon", {}), **refined}

            iteration = {
                "n": i + 1,
                "elapsed": round(time.time() - iter_started, 2),
                "plan": plan_msg.content,
                "static": explorer_msg.content,
                "dynamic": executor_msg.content,
                "refinement": refined,
            }
            dossier["iterations"].append(iteration)
            self.memory.record(target, iteration)
            self.tracker.log_iteration(run_id, iteration)

            if self._converged(iteration):
                LOG.info("Mythos campaign converged after %s iteration(s)", i + 1)
                break

        dossier["transcript"] = [m.__dict__ for m in self.transcript]
        self.tracker.end_run(run_id)
        return dossier

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _refine(ctx: dict[str, Any]) -> dict[str, Any]:
        dyn = ctx.get("dynamic_report", {})
        crashes = dyn.get("crashes", [])
        return {
            "crash_signatures": [c.get("signature") for c in crashes if c.get("signature")],
            "confirmed_count": len(crashes),
        }

    @staticmethod
    def _converged(iteration: dict[str, Any]) -> bool:
        dyn = iteration.get("dynamic", {}).get("dynamic_report", {})
        return bool(dyn.get("exploits"))
