"""``static-analysis-mcp`` — Joern + CodeQL + Semgrep + Tree-sitter."""

from __future__ import annotations

from ._mcp_runtime import MCPServer
from ..static.joern_bridge import JoernBridge
from ..static.codeql_bridge import CodeQLBridge
from ..static.semgrep_bridge import SemgrepBridge
from ..static.treesitter_cpg import TreeSitterCPG

server = MCPServer("static-analysis-mcp")
_joern = JoernBridge()
_codeql = CodeQLBridge()
_semgrep = SemgrepBridge()
_tree = TreeSitterCPG()


@server.tool("cpg_summary", {"repo_path": "string"})
def cpg_summary(repo_path: str):
    return _tree.summary(repo_path)


@server.tool("joern_query", {"repo_path": "string", "hypotheses": "array"})
def joern_query(repo_path: str, hypotheses: list):
    return _joern.query(repo_path, hypotheses)


@server.tool("codeql_query", {"repo_path": "string", "hypotheses": "array"})
def codeql_query(repo_path: str, hypotheses: list):
    return _codeql.query(repo_path, hypotheses)


@server.tool("semgrep_scan", {"repo_path": "string", "hypotheses": "array"})
def semgrep_scan(repo_path: str, hypotheses: list):
    return _semgrep.scan(repo_path, hypotheses)


if __name__ == "__main__":  # pragma: no cover
    server.serve_stdio()
