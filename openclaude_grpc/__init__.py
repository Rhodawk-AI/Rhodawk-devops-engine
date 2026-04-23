"""
openclaude_grpc — Python bridge to the vendored OpenClaude headless gRPC daemon.

Public surface:
    OpenClaudeClient       — low-level bidi-streaming client
    run_openclaude         — drop-in replacement for the legacy ``run_aider``
                              function (returns ``(combined_output, exit_code)``)
"""
from .client import (
    OpenClaudeClient,
    OpenClaudeError,
    OpenClaudeResult,
    run_openclaude,
)

__all__ = [
    "OpenClaudeClient",
    "OpenClaudeError",
    "OpenClaudeResult",
    "run_openclaude",
]
