"""
Executor Agent — dynamic execution, instrumentation, exploit synthesis.

Drives :mod:`mythos.dynamic` and :mod:`mythos.exploit`.  Provides crash /
trace feedback to the Planner so the CEGIS loop can refine hypotheses.
"""

from __future__ import annotations

import json
from typing import Any

from .base import AgentMessage, MythosAgent
from ..dynamic.aflpp_runner import AFLPlusPlusRunner
from ..dynamic.klee_runner import KLEERunner
from ..dynamic.qemu_harness import QEMUHarness
from ..dynamic.frida_instr import FridaInstrumenter
from ..dynamic.gdb_automation import GDBAutomation
from ..exploit.pwntools_synth import PwntoolsSynth
from ..exploit.rop_chain import ROPChainBuilder
from ..exploit.heap_exploit import HeapExploitKit
from ..exploit.privesc_kb import PrivEscKB


class ExecutorAgent(MythosAgent):
    name = "executor"
    model_tier = "tier2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.afl = AFLPlusPlusRunner()
        self.klee = KLEERunner()
        self.qemu = QEMUHarness()
        self.frida = FridaInstrumenter()
        self.gdb = GDBAutomation()
        self.pwn = PwntoolsSynth()
        self.rop = ROPChainBuilder()
        self.heap = HeapExploitKit()
        self.privesc = PrivEscKB()

    def execute(self, harness_dir: str, hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {"crashes": [], "traces": [], "exploits": []}
        out["crashes"] += self.afl.run(harness_dir)
        out["traces"]  += self.klee.run(harness_dir)
        if self.qemu.available():
            out["traces"] += self.qemu.run(harness_dir)
        if self.frida.available():
            out["traces"] += self.frida.attach_all(harness_dir)
        # GDB tactical step-through on each crash.
        for crash in out["crashes"]:
            out["traces"].append(self.gdb.replay(crash))
        # Synthesise exploits for confirmed crashes.
        for crash in out["crashes"]:
            chain = self.rop.build(crash)
            poc = self.pwn.assemble(crash, chain)
            heap = self.heap.spray_template(crash)
            out["exploits"].append({"crash": crash.get("id"),
                                    "rop_chain": chain,
                                    "poc": poc,
                                    "heap_template": heap})
        out["privesc_paths"] = self.privesc.suggest(hypotheses)
        return out

    def act(self, context: dict[str, Any]) -> AgentMessage:
        harness_dir = context.get("harness_dir", "/tmp/research")
        hypotheses = context.get("hypotheses", [])
        result = self.execute(harness_dir, hypotheses)
        # Tier-2 LLM critique pass to narrate the exploit.
        narration = self._call_llm(
            json.dumps(result)[:12000],
            system="You are the Executor. Summarise crashes and exploit chains "
                   "as JSON {\"summary\": str, \"impact\": str, \"next_steps\": [...]}.",
            max_tokens=1024,
        )
        result["narration"] = narration
        return AgentMessage(
            sender=self.name, recipient="orchestrator", role="response",
            content={"dynamic_report": result},
        )
