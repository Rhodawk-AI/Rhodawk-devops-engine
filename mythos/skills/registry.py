"""
agentskills.io-compatible skill registry.

Skills are JSON documents persisted to disk and indexed by name; the Hermes
agent populates this registry from successful campaign trajectories so the
Mythos orchestrator can compose them at planning time.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any

_REGISTRY_DIR = os.getenv("MYTHOS_SKILLS_DIR", "/data/mythos/skills")


@dataclass
class Skill:
    name: str
    description: str
    inputs: dict[str, str] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_ts: float = field(default_factory=time.time)
    schema: str = "agentskills.io/1.0"


class SkillRegistry:
    def __init__(self, root: str = _REGISTRY_DIR):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self._seed_default()

    def add(self, skill: Skill) -> str:
        path = os.path.join(self.root, f"{skill.name}.json")
        with open(path, "w") as fh:
            json.dump(asdict(skill), fh, indent=2)
        return path

    def get(self, name: str) -> Skill | None:
        path = os.path.join(self.root, f"{name}.json")
        if not os.path.exists(path):
            return None
        with open(path) as fh:
            data = json.load(fh)
        return Skill(**data)

    def list(self, tag: str | None = None) -> list[Skill]:
        out: list[Skill] = []
        for fn in os.listdir(self.root):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(self.root, fn)) as fh:
                s = Skill(**json.load(fh))
                if tag is None or tag in s.tags:
                    out.append(s)
        return out

    def _seed_default(self) -> None:
        for skill in DEFAULT_SKILLS:
            target = os.path.join(self.root, f"{skill.name}.json")
            if not os.path.exists(target):
                self.add(skill)


DEFAULT_SKILLS: list[Skill] = [
    Skill(
        name="analyze_ast",
        description="Parse a target file with Tree-sitter and emit a CST summary.",
        inputs={"path": "string"}, outputs={"summary": "object"},
        steps=[{"call": "mythos.static.treesitter_cpg.TreeSitterCPG.summary"}],
        tags=["static", "ast"],
    ),
    Skill(
        name="generate_fuzz_harness",
        description="Synthesise a hypothesis-driven fuzz harness for the Executor.",
        inputs={"hypothesis": "object"}, outputs={"harness_path": "string"},
        steps=[{"call": "harness_factory.build_harness"}],
        tags=["dynamic", "fuzzing"],
    ),
    Skill(
        name="find_rop_gadgets",
        description="Enumerate ROP gadgets in a binary using angrop / ROPgadget.",
        inputs={"binary": "string"}, outputs={"gadgets": "array"},
        steps=[{"call": "mythos.exploit.rop_chain.ROPChainBuilder.build"}],
        tags=["exploit", "rop"],
    ),
    Skill(
        name="chain_exploit",
        description="Chain primitives into a runnable PoC with pwntools.",
        inputs={"crash": "object", "rop_chain": "array"},
        outputs={"poc_path": "string"},
        steps=[{"call": "mythos.exploit.pwntools_synth.PwntoolsSynth.assemble"}],
        tags=["exploit", "pwntools"],
    ),
    Skill(
        name="perform_taint_analysis",
        description="Run Semgrep + Joern with hypothesis-targeted taint queries.",
        inputs={"repo_path": "string", "hypotheses": "array"},
        outputs={"findings": "array"},
        steps=[{"call": "mythos.static.semgrep_bridge.SemgrepBridge.scan"}],
        tags=["static", "taint"],
    ),
    Skill(
        name="debug_process",
        description="Replay a crash through GDB and capture state.",
        inputs={"crash": "object"}, outputs={"gdb_log": "string"},
        steps=[{"call": "mythos.dynamic.gdb_automation.GDBAutomation.replay"}],
        tags=["dynamic", "gdb"],
    ),
    Skill(
        name="generate_poc_report",
        description="Package campaign findings + PoC into a disclosure dossier.",
        inputs={"dossier": "object"}, outputs={"report_path": "string"},
        steps=[{"call": "disclosure_vault.write_dossier"}],
        tags=["disclosure"],
    ),
]
