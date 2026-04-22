"""
Explorer Agent — deep static & semantic code analysis.

Drives the bridges in :mod:`mythos.static` (Tree-sitter, Joern, CodeQL,
Semgrep) and feeds enriched code understanding back to the Planner.
"""

from __future__ import annotations

import json
from typing import Any

from .base import AgentMessage, MythosAgent
from ..static.treesitter_cpg import TreeSitterCPG
from ..static.joern_bridge import JoernBridge
from ..static.codeql_bridge import CodeQLBridge
from ..static.semgrep_bridge import SemgrepBridge


class ExplorerAgent(MythosAgent):
    name = "explorer"
    model_tier = "tier2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tree = TreeSitterCPG()
        self.joern = JoernBridge()
        self.codeql = CodeQLBridge()
        self.semgrep = SemgrepBridge()

    def analyse(self, repo_path: str, hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
        report: dict[str, Any] = {"semgrep": [], "joern": [], "codeql": [], "cpg": {}}
        # 1. Tree-sitter CPG snapshot — always available (pure-python parser
        #    fallback if py-tree-sitter not installed).
        report["cpg"] = self.tree.summary(repo_path)
        # 2. Semgrep — fast, broad coverage.
        report["semgrep"] = self.semgrep.scan(repo_path, hypotheses)
        # 3. Joern — deep CPG queries when available.
        if self.joern.available():
            report["joern"] = self.joern.query(repo_path, hypotheses)
        # 4. CodeQL — bring-your-own DB + queries.
        if self.codeql.available():
            report["codeql"] = self.codeql.query(repo_path, hypotheses)
        # 5. LLM tactical reasoning over consolidated findings.
        prompt = json.dumps({"hypotheses": hypotheses, "report": report})[:12000]
        verdict = self._call_llm(prompt, system=(
            "You are the Explorer. Cross-reference static findings against "
            "hypotheses. Return JSON {\"confirmed\": [...], \"refuted\": [...], "
            "\"new_hypotheses\": [...]}."
        ), max_tokens=2048)
        report["llm_verdict_raw"] = verdict
        return report

    def act(self, context: dict[str, Any]) -> AgentMessage:
        repo = context.get("repo_path", "/data/repo")
        hypotheses = context.get("hypotheses", [])
        report = self.analyse(repo, hypotheses)
        return AgentMessage(
            sender=self.name, recipient="orchestrator", role="response",
            content={"static_report": report},
        )
