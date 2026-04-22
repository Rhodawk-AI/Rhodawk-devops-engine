"""HMAC-signed webhook delivery."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

import requests

_SECRET = os.getenv("MYTHOS_WEBHOOK_SECRET", "")


def sign(payload: bytes) -> str:
    if not _SECRET:
        return "unsigned"
    mac = hmac.new(_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def deliver(url: str, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"event": event, "ts": time.time(), "payload": payload},
                      default=str).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Mythos-Event": event,
        "X-Mythos-Signature": sign(body),
    }
    try:
        r = requests.post(url, data=body, headers=headers, timeout=15)
        return {"status_code": r.status_code, "body": r.text[:500]}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
