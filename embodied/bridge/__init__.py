"""
EmbodiedOS Bridge — exposes every Rhodawk capability as a Model Context
Protocol (MCP) server that both Hermes Agent and OpenClaw can invoke.
"""

from __future__ import annotations

from .mcp_server import EmbodiedBridgeServer, build_server, serve
from .tool_registry import EmbodiedTool, ToolRegistry, default_registry
from .hermes_client import HermesClient
from .openclaw_client import OpenClawClient

__all__ = [
    "EmbodiedBridgeServer",
    "build_server",
    "serve",
    "EmbodiedTool",
    "ToolRegistry",
    "default_registry",
    "HermesClient",
    "OpenClawClient",
]
