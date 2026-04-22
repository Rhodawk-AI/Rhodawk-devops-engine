"""
Planner Agent — strategic reasoning and hypothesis generation.

Implements §5.1 of the Mythos plan:
  * Problem decomposition.
  * Probabilistic hypothesis generation (delegates to
    :mod:`mythos.reasoning.probabilistic`).
  * Attack-graph construction.
  * Resource allocation between Explorer and Executor.
"""

from __future__ import annotations

import json
from typing import Any

from .base import AgentMessage, MythosAgent
from ..reasoning.probabilistic import HypothesisEngine
from ..reasoning.attack_graph import AttackGraph


class PlannerAgent(MythosAgent):
    name = "planner"
    model_tier = "tier1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hypothesis_engine = HypothesisEngine()
        self.attack_graph = AttackGraph()

    def decompose(self, target: dict[str, Any]) -> list[str]:
        """Split a high-level engagement into ordered sub-tasks."""
        system = (
            "Decompose a security engagement into atomic sub-tasks. "
            "Return JSON: {\"tasks\": [\"recon ...\", \"taint ...\", ...]}"
        )
        raw = self._call_llm(json.dumps(target), system=system, max_tokens=1024)
        try:
            return json.loads(raw).get("tasks", [])
        except Exception:
            # Sensible deterministic fallback so the orchestrator never stalls.
            return [
                "recon: enumerate languages, dependencies, attack surface",
                "static: run Joern + Semgrep + Tree-sitter CPG queries",
                "dynamic: synthesise fuzzing harnesses, run AFL++ + KLEE",
                "exploit: chain primitives via pwntools",
                "consensus: tier-3 adversarial review",
                "disclosure: package dossier",
            ]

    def generate_hypotheses(self, recon: dict[str, Any]) -> list[dict[str, Any]]:
        """Produce ranked vulnerability hypotheses with probabilistic priors."""
        return self.hypothesis_engine.sample(recon, n=8)

    def build_attack_graph(self, hypotheses: list[dict[str, Any]]) -> AttackGraph:
        for h in hypotheses:
            self.attack_graph.add_hypothesis(h)
        self.attack_graph.connect()
        return self.attack_graph

    def allocate(self, hypotheses: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """Decide which hypothesis goes to Explorer (static) vs Executor (dynamic)."""
        explorer_q, executor_q = [], []
        for h in hypotheses:
            (explorer_q if h.get("kind") in ("logic", "auth", "validation")
             else executor_q).append(h)
        return {"explorer": explorer_q, "executor": executor_q}

    # -- agent API ----------------------------------------------------------

    def act(self, context: dict[str, Any]) -> AgentMessage:
        target = context.get("target", {})
        recon = context.get("recon", {})
        tasks = self.decompose(target)
        hypotheses = self.generate_hypotheses(recon or target)
        graph = self.build_attack_graph(hypotheses)
        allocation = self.allocate(hypotheses)
        return AgentMessage(
            sender=self.name, recipient="orchestrator", role="response",
            content={
                "tasks": tasks,
                "hypotheses": hypotheses,
                "attack_graph": graph.to_dict(),
                "allocation": allocation,
            },
        )
