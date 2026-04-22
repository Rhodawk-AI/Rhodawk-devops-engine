"""All ARCHITECT / Mythos MCP servers must import cleanly and expose tools."""

from __future__ import annotations

import importlib

import pytest

MCP_MODULES = [
    "mythos.mcp.static_analysis_mcp",
    "mythos.mcp.dynamic_analysis_mcp",
    "mythos.mcp.exploit_generation_mcp",
    "mythos.mcp.vulnerability_database_mcp",
    "mythos.mcp.web_security_mcp",
    "mythos.mcp.reconnaissance_mcp",
    "mythos.mcp.browser_agent_mcp",
    "mythos.mcp.scope_parser_mcp",
    "mythos.mcp.subdomain_enum_mcp",
    "mythos.mcp.httpx_probe_mcp",
    "mythos.mcp.shodan_mcp",
    "mythos.mcp.wayback_mcp",
    "mythos.mcp.frida_runtime_mcp",
    "mythos.mcp.ghidra_bridge_mcp",
    "mythos.mcp.can_bus_mcp",
    "mythos.mcp.sdr_analysis_mcp",
]


@pytest.mark.parametrize("mod", MCP_MODULES)
def test_mcp_module_imports_and_exposes_tools(mod):
    m = importlib.import_module(mod)
    assert hasattr(m, "server"), f"{mod} missing server export"
    tools = m.server.list_tools()
    assert isinstance(tools, list)
    assert tools, f"{mod} exposes no tools"
    for t in tools:
        assert "name" in t
