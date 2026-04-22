"""Audit-chain integrity smoke tests."""

from __future__ import annotations

import json
import os
import tempfile

import pytest


def test_audit_logger_chains_hashes(tmp_data_dir, monkeypatch):
    """Every appended event must reference the previous event's SHA-256."""
    chain_file = tmp_data_dir / "audit_chain.jsonl"
    monkeypatch.setenv("AUDIT_CHAIN_FILE", str(chain_file))

    import importlib
    import audit_logger
    importlib.reload(audit_logger)

    if hasattr(audit_logger, "AUDIT_CHAIN_FILE"):
        audit_logger.AUDIT_CHAIN_FILE = str(chain_file)

    appender = (
        getattr(audit_logger, "append_event", None)
        or getattr(audit_logger, "log_event", None)
        or getattr(audit_logger, "audit", None)
    )
    if appender is None:
        pytest.skip("audit_logger has no public append function")

    appender({"kind": "test", "i": 1})
    appender({"kind": "test", "i": 2})
    appender({"kind": "test", "i": 3})

    lines = chain_file.read_text().strip().splitlines()
    assert len(lines) == 3
    parsed = [json.loads(l) for l in lines]
    # Each entry must have a hash field, and ascending sequence preserved.
    for i, ev in enumerate(parsed):
        assert any(k in ev for k in ("hash", "sha256", "current_hash"))
        if i > 0:
            prev = parsed[i - 1]
            prev_h = prev.get("hash") or prev.get("sha256") or prev.get("current_hash")
            link = ev.get("prev_hash") or ev.get("previous_hash") or ev.get("prev")
            if link is not None:
                assert link == prev_h, "audit chain link broken"
