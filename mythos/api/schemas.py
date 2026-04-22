"""Pydantic schemas for the Mythos API surface."""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover
    from pydantic import BaseModel, Field
except Exception:  # noqa: BLE001 - pydantic always available via fastapi but be safe
    BaseModel = object  # type: ignore
    def Field(*_a, **_kw):  # type: ignore
        return None


class AnalyseRequest(BaseModel):
    repo: str = Field(..., description="Git URL or local path of the target.")
    branch: str | None = None
    languages: list[str] = []
    frameworks: list[str] = []
    dependencies: list[str] = []
    focus: str | None = Field(None, description="Optional natural-language focus area.")
    max_iterations: int = 3
    output_format: str = Field("dossier", description="dossier | sarif | json")
    callback_url: str | None = None


class CrashReport(BaseModel):
    id: str
    harness: str | None = None
    signature: str | None = None
    rop_chain: list[str] = []
    poc_path: str | None = None


class AnalyseResponse(BaseModel):
    target: dict[str, Any]
    iterations: list[dict[str, Any]]
    crashes: list[CrashReport] = []
    summary: str = ""


class WebhookEvent(BaseModel):
    event: str
    run_id: str
    payload: dict[str, Any] = {}
