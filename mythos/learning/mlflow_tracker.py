"""Thin MLflow tracker — falls back to a JSONL log when MLflow is absent."""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

try:  # pragma: no cover
    import mlflow  # type: ignore
    _MLFLOW = True
except Exception:  # noqa: BLE001
    _MLFLOW = False


_FALLBACK_LOG = os.getenv("MYTHOS_MLFLOW_FALLBACK", "/data/mythos/mlflow_fallback.jsonl")


class MLflowTracker:
    def __init__(self, experiment: str = "mythos"):
        self.experiment = experiment
        if _MLFLOW:
            try:
                mlflow.set_experiment(experiment)
            except Exception:  # noqa: BLE001
                pass

    def start_run(self, tags: dict[str, str] | None = None) -> str:
        if _MLFLOW:
            try:
                run = mlflow.start_run(tags=tags or {})
                return run.info.run_id
            except Exception:  # noqa: BLE001
                pass
        run_id = uuid.uuid4().hex
        self._jsonl({"event": "start", "run_id": run_id, "tags": tags or {},
                     "experiment": self.experiment, "ts": time.time()})
        return run_id

    def log_iteration(self, run_id: str, iteration: dict[str, Any]) -> None:
        if _MLFLOW:
            try:
                mlflow.log_metric("hypotheses",
                                  len(iteration.get("plan", {}).get("hypotheses", [])),
                                  step=iteration.get("n", 0))
                mlflow.log_metric("crashes",
                                  iteration.get("refinement", {}).get("confirmed_count", 0),
                                  step=iteration.get("n", 0))
            except Exception:  # noqa: BLE001
                pass
        self._jsonl({"event": "iter", "run_id": run_id, "iter": iteration})

    def end_run(self, run_id: str) -> None:
        if _MLFLOW:
            try:
                mlflow.end_run()
            except Exception:  # noqa: BLE001
                pass
        self._jsonl({"event": "end", "run_id": run_id, "ts": time.time()})

    def _jsonl(self, payload: dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(_FALLBACK_LOG), exist_ok=True)
            with open(_FALLBACK_LOG, "a") as fh:
                fh.write(json.dumps(payload, default=str) + "\n")
        except OSError:
            pass
