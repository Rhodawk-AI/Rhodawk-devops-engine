"""Scope-parser MCP tests — text parsing path (no network)."""

from __future__ import annotations


def test_parse_scope_text_extracts_assets():
    from mythos.mcp.scope_parser_mcp import parse_scope_text
    txt = """
    Eligible targets:
      - https://api.example.com
      - admin.example.com
      - 10.0.0.0/8
      - https://www.example.com/path?x=1
    Out of scope: third-party.com
    """
    out = parse_scope_text(txt, "manual")
    assert "https://api.example.com" in out["urls"]
    assert "admin.example.com" in out["domains"]
    assert "10.0.0.0/8" in out["cidrs"]
    assert out["platform"] == "manual"


def test_list_active_programs_no_creds_returns_empty():
    """With no credentials the tool must return empty programs gracefully."""
    import os
    for k in ("HACKERONE_USERNAME", "HACKERONE_API_TOKEN",
              "BUGCROWD_API_TOKEN", "INTIGRITI_API_TOKEN"):
        os.environ.pop(k, None)
    from mythos.mcp.scope_parser_mcp import list_active_programs
    out = list_active_programs()
    assert out["count"] == 0
    assert out["programs"] == []
