"""
Lightweight API-key + OAuth2 bearer authentication for the Mythos API.

Backed by an env-defined static API key (``MYTHOS_API_KEYS=key1,key2``) plus
optional JWT validation when ``MYTHOS_JWT_PUBKEY`` is set.
"""

from __future__ import annotations

import os
from typing import Any

try:  # pragma: no cover
    from fastapi import Header, HTTPException, status
except Exception:  # noqa: BLE001
    Header = HTTPException = status = None  # type: ignore

try:  # pragma: no cover
    import jwt  # type: ignore
    _JWT = True
except Exception:  # noqa: BLE001
    _JWT = False


def _allowed_keys() -> set[str]:
    return {k.strip() for k in os.getenv("MYTHOS_API_KEYS", "").split(",") if k.strip()}


def require_api_key(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if HTTPException is None:  # FastAPI not installed — let the caller handle it.
        return {"sub": "anonymous"}
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer")
    token = authorization.split(None, 1)[1].strip()
    keys = _allowed_keys()
    if keys and token in keys:
        return {"sub": "api-key", "token": token[:8] + "..."}
    if _JWT and (pubkey := os.getenv("MYTHOS_JWT_PUBKEY")):
        try:
            return jwt.decode(token, pubkey, algorithms=["RS256"])
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail=f"jwt: {exc}") from exc
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
