"""
Mythos productization API.

Run with::

    uvicorn mythos.api.fastapi_server:app --host 0.0.0.0 --port 8000

If ``fastapi`` isn't installed (e.g. minimal HF Space build) importing this
module is still safe — ``app`` is set to ``None`` so a deployment guard can
detect the gap.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

LOG = logging.getLogger("mythos.api")

try:  # pragma: no cover
    from fastapi import Depends, FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    _FASTAPI = True
except Exception:  # noqa: BLE001
    _FASTAPI = False
    FastAPI = None  # type: ignore

from .auth import require_api_key
from .schemas import AnalyseRequest, AnalyseResponse, WebhookEvent
from .webhooks import deliver
from ..agents.orchestrator import MythosOrchestrator

_RUNS: dict[str, dict[str, Any]] = {}


if _FASTAPI:
    app = FastAPI(
        title="Rhodawk Mythos API",
        version="1.0.0",
        description="Autonomous vulnerability research as a service.",
    )
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    @app.get("/v1/health")
    def health():
        return {"status": "ok", "service": "rhodawk-mythos"}

    @app.post("/v1/analyze_target", response_model=AnalyseResponse)
    def analyze_target(req: AnalyseRequest, principal=Depends(require_api_key)):
        run_id = uuid.uuid4().hex
        _RUNS[run_id] = {"status": "running", "principal": principal}

        target = req.dict()
        target["recon"] = {
            "languages": req.languages,
            "frameworks": req.frameworks,
            "dependencies": req.dependencies,
        }

        def _execute():
            try:
                dossier = MythosOrchestrator(max_iterations=req.max_iterations).run_campaign(target)
                _RUNS[run_id] = {"status": "complete", "dossier": dossier}
                if req.callback_url:
                    deliver(req.callback_url, "analysis.complete",
                            {"run_id": run_id, "summary": dossier.get("iterations", [])[-1:]})
            except Exception as exc:  # noqa: BLE001
                _RUNS[run_id] = {"status": "error", "error": str(exc)}
                if req.callback_url:
                    deliver(req.callback_url, "analysis.error",
                            {"run_id": run_id, "error": str(exc)})

        threading.Thread(target=_execute, daemon=True).start()
        return AnalyseResponse(target=target, iterations=[], crashes=[],
                               summary=f"queued run_id={run_id}")

    @app.get("/v1/runs/{run_id}")
    def get_run(run_id: str, principal=Depends(require_api_key)):
        if run_id not in _RUNS:
            raise HTTPException(status_code=404, detail="unknown run_id")
        return _RUNS[run_id]

    @app.post("/v1/webhooks/test")
    def webhook_test(evt: WebhookEvent, principal=Depends(require_api_key)):
        return {"received": evt.dict(), "by": principal.get("sub")}

else:  # pragma: no cover
    app = None
    LOG.warning("fastapi not installed — Mythos API surface unavailable")
