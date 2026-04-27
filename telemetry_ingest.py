"""
Rhodawk EmbodiedOS — eBPF / Falco Telemetry Ingest (Gap 8)
============================================================
Streams Falco events into the engine for runtime threat correlation.

Falco runs in the host (or sidecar) and writes JSON-line events to
``$FALCO_LOG_PATH``. ``FalcoTelemetry`` tails that file in a background
thread, parses each event, and routes it to:

  * the threat graph (so runtime IOCs become first-class nodes), and
  * the SOAR engine (so a CRITICAL-priority Falco rule fires the
    matching playbook within seconds).

If Falco is not installed or the log path is missing, the sensor logs
a single warning and exits — it never blocks startup.

Public surface
--------------
    FalcoTelemetry(log_path=None)
        .start()   start the background tailer thread
        .stop()    stop and join

    start_falco_sensor()
        Process-wide convenience: spin the singleton, return it.

Environment
-----------
    RHODAWK_TELEMETRY_ENABLED  "true"|"false"  default "true"
    FALCO_LOG_PATH             default /var/log/falco/falco.log
    FALCO_PRIORITY_MIN         default WARNING (NOTICE|INFO|...)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

LOG = logging.getLogger("rhodawk.telemetry.falco")

ENABLED = os.getenv("RHODAWK_TELEMETRY_ENABLED", "true").lower() == "true"
FALCO_LOG_PATH = os.getenv("FALCO_LOG_PATH", "/var/log/falco/falco.log")
FALCO_PRIORITY_MIN = os.getenv("FALCO_PRIORITY_MIN", "WARNING").upper()

_PRIORITY_RANK = {
    "DEBUG": 0, "INFORMATIONAL": 1, "INFO": 1, "NOTICE": 2,
    "WARNING": 3, "WARN": 3, "ERROR": 4, "CRITICAL": 5,
    "ALERT": 6, "EMERGENCY": 7,
}


@dataclass
class FalcoEvent:
    rule: str
    priority: str
    output: str
    time: str
    fields: dict
    raw: dict

    def as_finding(self) -> dict:
        """Translate a Falco event into a SOAR-compatible finding dict."""
        sev_map = {
            "DEBUG": "INFO", "INFO": "INFO", "INFORMATIONAL": "INFO",
            "NOTICE": "LOW", "WARNING": "MEDIUM", "WARN": "MEDIUM",
            "ERROR": "HIGH", "CRITICAL": "CRITICAL",
            "ALERT": "CRITICAL", "EMERGENCY": "CRITICAL",
        }
        return {
            "finding_id": "falco_" + str(abs(hash((self.rule, self.time))))[:12],
            "title": f"Falco: {self.rule}",
            "severity": sev_map.get(self.priority, "MEDIUM"),
            "cwe_id": "CWE-RUNTIME",
            "description": self.output,
            "tags": ["runtime", "ebpf", "falco"],
            "source": "falco",
            "raw": self.raw,
        }


class FalcoTelemetry:
    """Tail Falco's JSON log and fan events out to the engine."""

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or FALCO_LOG_PATH
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._stats = {"read": 0, "matched": 0, "dropped": 0, "errors": 0}
        self._lock = threading.Lock()

    # ── lifecycle ────────────────────────────────────────────────────

    def start(self) -> bool:
        if not ENABLED:
            LOG.info("Falco telemetry disabled (RHODAWK_TELEMETRY_ENABLED=false).")
            return False
        if self._thread is not None and self._thread.is_alive():
            return True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="rhodawk-falco-tailer", daemon=True
        )
        self._thread.start()
        LOG.info("Falco telemetry started — tailing %s", self.log_path)
        return True

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    # ── background tailer ───────────────────────────────────────────

    def _run(self) -> None:
        # Wait for the log file to appear (Falco might start later).
        waited = 0
        while not os.path.exists(self.log_path):
            if self._stop.is_set():
                return
            time.sleep(2)
            waited += 2
            if waited == 30:
                LOG.warning(
                    "Falco log %s not present after 30s — continuing to wait.",
                    self.log_path,
                )
            if waited >= 600:
                LOG.warning(
                    "Falco log %s never appeared (waited 10m) — sensor exiting.",
                    self.log_path,
                )
                return

        min_rank = _PRIORITY_RANK.get(FALCO_PRIORITY_MIN, 3)
        try:
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(0, os.SEEK_END)  # tail-from-now (don't replay history)
                while not self._stop.is_set():
                    line = fh.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    self._process_line(line, min_rank)
        except FileNotFoundError:
            LOG.warning("Falco log %s vanished — sensor exiting.", self.log_path)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Falco tailer crashed: %s", exc)

    def _process_line(self, line: str, min_rank: int) -> None:
        with self._lock:
            self._stats["read"] += 1
        line = line.strip()
        if not line or not line.startswith("{"):
            return
        try:
            doc = json.loads(line)
        except Exception:  # noqa: BLE001
            with self._lock:
                self._stats["errors"] += 1
            return
        priority = str(doc.get("priority", "")).upper()
        if _PRIORITY_RANK.get(priority, 0) < min_rank:
            with self._lock:
                self._stats["dropped"] += 1
            return
        evt = FalcoEvent(
            rule=str(doc.get("rule", "unknown")),
            priority=priority or "INFO",
            output=str(doc.get("output", "")),
            time=str(doc.get("time", "")),
            fields=doc.get("output_fields", {}) or {},
            raw=doc,
        )
        with self._lock:
            self._stats["matched"] += 1
        self._dispatch(evt)

    def _dispatch(self, evt: FalcoEvent) -> None:
        finding = evt.as_finding()
        # Threat graph (best-effort)
        try:
            import threat_graph  # type: ignore
            db = threat_graph.get_db()
            promote = getattr(db, "record_finding", None) or getattr(
                db, "upsert_finding", None
            )
            if promote:
                promote(finding)
        except Exception as exc:  # noqa: BLE001
            LOG.debug("threat_graph promote failed for falco evt: %s", exc)

        # SOAR (best-effort)
        try:
            from soar_engine import get_default_engine
            get_default_engine().process_finding(finding)
        except Exception as exc:  # noqa: BLE001
            LOG.debug("soar dispatch failed for falco evt: %s", exc)


# ── process-wide singleton ───────────────────────────────────────────

_SENSOR: FalcoTelemetry | None = None
_SENSOR_LOCK = threading.Lock()


def start_falco_sensor() -> FalcoTelemetry:
    """Start (or return) the singleton Falco telemetry sensor.

    Safe to call from app startup. Returns the sensor object so tests
    and operators can inspect ``.stats()``.
    """
    global _SENSOR
    with _SENSOR_LOCK:
        if _SENSOR is None:
            _SENSOR = FalcoTelemetry()
        _SENSOR.start()
    return _SENSOR


__all__ = ["FalcoTelemetry", "FalcoEvent", "start_falco_sensor"]
