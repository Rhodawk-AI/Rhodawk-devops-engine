"""Webhook HMAC verification smoke test."""

from __future__ import annotations

import hashlib
import hmac
import json
import os

import pytest


def _signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_hmac_verify_accepts_valid(monkeypatch):
    secret = "supersecret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("WEBHOOK_HMAC_SECRET", secret)

    import importlib
    import webhook_server
    importlib.reload(webhook_server)

    body = json.dumps({"action": "ping"}).encode()
    sig = _signature(secret, body)

    verifier = (
        getattr(webhook_server, "verify_hmac", None)
        or getattr(webhook_server, "verify_signature", None)
        or getattr(webhook_server, "_verify_signature", None)
    )
    if verifier is None:
        pytest.skip("webhook_server exposes no public HMAC verifier")
    assert verifier(body, sig) is True


def test_hmac_verify_rejects_bogus(monkeypatch):
    secret = "supersecret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setenv("WEBHOOK_HMAC_SECRET", secret)

    import importlib
    import webhook_server
    importlib.reload(webhook_server)

    verifier = (
        getattr(webhook_server, "verify_hmac", None)
        or getattr(webhook_server, "verify_signature", None)
        or getattr(webhook_server, "_verify_signature", None)
    )
    if verifier is None:
        pytest.skip("webhook_server exposes no public HMAC verifier")
    body = b'{"x": 1}'
    assert verifier(body, "sha256=deadbeef") is False
