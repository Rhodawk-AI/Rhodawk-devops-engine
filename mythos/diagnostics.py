"""
Mythos diagnostics — capability availability matrix + lightweight self-checks.

Importable from anywhere (no heavy side-effects). Used by:
  * ``mythos.__main__`` (the ``python -m mythos`` self-test CLI)
  * ``app.py`` (the Gradio "🜲 Mythos" tab status box)
  * ``mythos.api.fastapi_server`` health endpoint hooks
"""

from __future__ import annotations

from typing import Any


def _probe(modpath: str, attr: str) -> dict[str, Any]:
    try:
        mod = __import__(modpath, fromlist=[attr])
        cls = getattr(mod, attr)
        inst = cls()
        ok = bool(getattr(inst, "available", lambda: True)())
        return {"available": ok}
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def availability_matrix() -> dict[str, dict[str, Any]]:
    """Return ``{component_name: {available: bool, error?: str}}``."""
    return {
        "static.treesitter": _probe("mythos.static.treesitter_cpg",  "TreeSitterCPG"),
        "static.joern":      _probe("mythos.static.joern_bridge",     "JoernBridge"),
        "static.codeql":     _probe("mythos.static.codeql_bridge",    "CodeQLBridge"),
        "static.semgrep":    _probe("mythos.static.semgrep_bridge",   "SemgrepBridge"),
        "dynamic.aflpp":     _probe("mythos.dynamic.aflpp_runner",    "AFLPlusPlusRunner"),
        "dynamic.klee":      _probe("mythos.dynamic.klee_runner",     "KLEERunner"),
        "dynamic.qemu":      _probe("mythos.dynamic.qemu_harness",    "QEMUHarness"),
        "dynamic.frida":     _probe("mythos.dynamic.frida_instr",     "FridaInstrumenter"),
        "dynamic.gdb":       _probe("mythos.dynamic.gdb_automation",  "GDBAutomation"),
        "exploit.pwntools":  _probe("mythos.exploit.pwntools_synth",  "PwntoolsSynth"),
        "exploit.rop":       _probe("mythos.exploit.rop_chain",       "ROPChainBuilder"),
        "exploit.heap":      _probe("mythos.exploit.heap_exploit",    "HeapExploitKit"),
        "exploit.privesc":   _probe("mythos.exploit.privesc_kb",      "PrivEscKB"),
    }


def reasoning_check() -> dict[str, Any]:
    from .reasoning.probabilistic import HypothesisEngine
    from .reasoning.attack_graph import AttackGraph

    he = HypothesisEngine(seed=7)
    hyps = he.sample({"languages": ["python", "c"],
                      "frameworks": ["flask"],
                      "dependencies": ["pickle", "yaml"]}, n=5)
    g = AttackGraph()
    for h in hyps:
        g.add_hypothesis(h)
    g.connect()
    return {"backend": getattr(he, "backend", "?"),
            "n_hypotheses": len(hyps),
            "graph_nodes": len(g.nodes),
            "graph_edges": len(g.edges)}


def learning_check() -> dict[str, Any]:
    from .learning.rl_planner import RLPlanner
    from .learning.episodic_memory import EpisodicMemory
    from .learning.mlflow_tracker import MLflowTracker

    return {"rl_backend": RLPlanner().backend,
            "episodic": bool(EpisodicMemory()),
            "mlflow_backend": MLflowTracker(experiment="self-test").backend}


def api_check() -> dict[str, Any]:
    from .api import fastapi_server

    return {"fastapi_available": bool(fastapi_server.app),
            "title": getattr(fastapi_server.app, "title", None)
                     if fastapi_server.app else None}


def mcp_check() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in ("static_analysis_mcp", "dynamic_analysis_mcp",
                 "exploit_generation_mcp", "vulnerability_database_mcp",
                 "web_security_mcp", "reconnaissance_mcp"):
        try:
            mod = __import__(f"mythos.mcp.{name}", fromlist=["server"])
            out[name] = {"tools": [t["name"] for t in mod.server.list_tools()]}
        except Exception as exc:  # noqa: BLE001
            out[name] = {"error": f"{type(exc).__name__}: {exc}"}
    return out
