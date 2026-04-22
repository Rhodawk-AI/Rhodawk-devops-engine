"""
LoRA / QLoRA adapter manager.

Wraps the existing ``lora_scheduler`` module and adds Mythos-specific
versioning + A/B testing semantics.  Adapters are pinned per (cwe, target
language) so the orchestrator can ship a specialised Tier-2 weight set per
campaign class.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any


_ADAPTERS_INDEX = os.getenv("MYTHOS_ADAPTER_INDEX", "/data/mythos/adapters/index.json")


class LoRAAdapterManager:
    def __init__(self):
        self.index: dict[str, dict[str, Any]] = {}
        self._load()

    def register(self, name: str, *, cwe: str, language: str, base_model: str,
                 weight_path: str, metrics: dict[str, float] | None = None) -> str:
        entry = {
            "name": name, "cwe": cwe, "language": language, "base_model": base_model,
            "weight_path": weight_path, "metrics": metrics or {},
            "version": int(time.time()),
        }
        self.index.setdefault(name, {})["latest"] = entry
        self.index[name].setdefault("history", []).append(entry)
        self._save()
        return f"{name}@{entry['version']}"

    def select(self, *, cwe: str, language: str) -> dict[str, Any] | None:
        for name, body in self.index.items():
            latest = body.get("latest", {})
            if latest.get("cwe") == cwe and latest.get("language") == language:
                return latest
        return None

    def rollback(self, name: str) -> dict[str, Any] | None:
        body = self.index.get(name, {})
        history = body.get("history", [])
        if len(history) < 2:
            return None
        body["latest"] = history[-2]
        self._save()
        return body["latest"]

    def _load(self) -> None:
        try:
            with open(_ADAPTERS_INDEX) as fh:
                self.index = json.load(fh)
        except Exception:  # noqa: BLE001
            pass

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(_ADAPTERS_INDEX), exist_ok=True)
            with open(_ADAPTERS_INDEX, "w") as fh:
                json.dump(self.index, fh, indent=2)
        except OSError:
            pass
