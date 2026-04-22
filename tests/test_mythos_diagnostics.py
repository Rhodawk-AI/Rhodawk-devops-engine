"""Mythos diagnostics smoke tests."""

from __future__ import annotations


def test_availability_matrix_has_all_components():
    from mythos.diagnostics import availability_matrix
    m = availability_matrix()
    for k in ("static.treesitter", "static.joern", "static.codeql",
              "dynamic.aflpp", "dynamic.klee", "exploit.pwntools"):
        assert k in m


def test_mcp_check_lists_all_servers():
    from mythos.diagnostics import mcp_check
    out = mcp_check()
    assert "reconnaissance_mcp" in out


def test_reasoning_check_returns_graph():
    from mythos.diagnostics import reasoning_check
    r = reasoning_check()
    assert r["n_hypotheses"] > 0
    assert r["graph_nodes"] > 0


def test_embodied_bridge_channels_default_off():
    """With no env vars set every channel must report unwired (no exceptions)."""
    import os
    for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
              "DISCORD_WEBHOOK_URL", "OPENCLAW_WEBHOOK_URL", "HERMES_AGENT_URL"):
        os.environ.pop(k, None)
    from architect import embodied_bridge
    ch = embodied_bridge.channels()
    assert all(v is False for v in ch.values())
