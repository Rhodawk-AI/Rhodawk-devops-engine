"""
Attack-graph construction for the Planner.

Nodes  = hypotheses or intermediate states (e.g. "leaked-pointer", "RCE").
Edges  = exploitation transitions weighted by the joint probability of the
         pair occurring in the same code-base + the cost of the chain.

Falls back to a tiny pure-Python adjacency-list when ``networkx`` is absent
so the orchestrator works in minimal images.
"""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - optional dep
    import networkx as nx  # type: ignore
except Exception:  # noqa: BLE001
    nx = None  # type: ignore


# Heuristic compatibility map between vulnerability classes that can be
# plausibly chained together to amplify impact.
_CHAIN_RULES: list[tuple[str, str, float]] = [
    ("CWE-22",  "CWE-78",  0.7),  # path traversal → command injection
    ("CWE-89",  "CWE-78",  0.5),  # SQLi → RCE via UDF
    ("CWE-79",  "CWE-352", 0.6),  # XSS → CSRF
    ("CWE-918", "CWE-502", 0.4),  # SSRF → deserialisation
    ("CWE-119", "CWE-787", 0.8),  # overflow → OOB write
    ("CWE-787", "CWE-416", 0.7),  # OOB write → UAF
    ("CWE-416", "CWE-269", 0.6),  # UAF → privesc
    ("CWE-287", "CWE-862", 0.5),  # auth bypass → missing authz
]


class AttackGraph:
    def __init__(self):
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[tuple[str, str, float]] = []
        self._g = nx.DiGraph() if nx is not None else None

    def add_hypothesis(self, h: dict[str, Any]) -> None:
        cwe = h["cwe"]
        self.nodes[cwe] = {**h, "id": cwe}
        if self._g is not None:
            self._g.add_node(cwe, **h)

    def connect(self) -> None:
        for src, dst, base_w in _CHAIN_RULES:
            if src in self.nodes and dst in self.nodes:
                w = base_w * self.nodes[src]["confidence"] * self.nodes[dst]["confidence"]
                self.edges.append((src, dst, round(w, 4)))
                if self._g is not None:
                    self._g.add_edge(src, dst, weight=w)

    def critical_paths(self, top: int = 3) -> list[list[str]]:
        if self._g is None or self._g.number_of_nodes() == 0:
            # naive heaviest-edge fallback
            sorted_e = sorted(self.edges, key=lambda e: e[2], reverse=True)[:top]
            return [list(e[:2]) for e in sorted_e]
        paths: list[tuple[float, list[str]]] = []
        for src in self._g.nodes:
            for dst in self._g.nodes:
                if src == dst:
                    continue
                try:
                    p = nx.shortest_path(self._g, src, dst, weight=lambda *_: 1)
                    score = sum(self._g.edges[a, b].get("weight", 0) for a, b in zip(p, p[1:]))
                    paths.append((score, p))
                except Exception:
                    continue
        paths.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in paths[:top]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.nodes.values()),
            "edges": [{"src": s, "dst": d, "weight": w} for s, d, w in self.edges],
            "critical_paths": self.critical_paths(),
        }
