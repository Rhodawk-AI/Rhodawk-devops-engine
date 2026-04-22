"""
Episodic memory — stores complete campaign trajectories on disk so the
Planner can retrieve "what worked last time on a similar repo".

Backed by SQLite for portability (no extra deps).  Schema mirrors the
``memory_engine`` patterns already in the repo.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any

_DB = os.getenv("MYTHOS_EPISODIC_DB", "/data/mythos/episodic.sqlite")


class EpisodicMemory:
    def __init__(self, path: str = _DB):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS episodes ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  ts REAL,"
            "  repo TEXT,"
            "  iteration INTEGER,"
            "  cwes TEXT,"
            "  outcome TEXT,"
            "  payload TEXT"
            ")"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodes_repo ON episodes(repo)"
        )
        self._db.commit()

    def record(self, target: dict[str, Any], iteration: dict[str, Any]) -> int:
        cwes = [h.get("cwe") for h in iteration.get("plan", {}).get("hypotheses", [])]
        outcome = "exploit" if iteration.get("dynamic", {}).get(
            "dynamic_report", {}).get("exploits") else "unconfirmed"
        cur = self._db.execute(
            "INSERT INTO episodes(ts, repo, iteration, cwes, outcome, payload) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), target.get("repo", "?"), iteration.get("n", 0),
             json.dumps(cwes), outcome, json.dumps(iteration, default=str)[:200_000]),
        )
        self._db.commit()
        return cur.lastrowid or 0

    def recall(self, repo: str, limit: int = 10) -> list[dict[str, Any]]:
        cur = self._db.execute(
            "SELECT ts, iteration, cwes, outcome FROM episodes "
            "WHERE repo = ? ORDER BY id DESC LIMIT ?", (repo, limit),
        )
        return [
            {"ts": ts, "iteration": it, "cwes": json.loads(cwes), "outcome": outcome}
            for ts, it, cwes, outcome in cur.fetchall()
        ]
