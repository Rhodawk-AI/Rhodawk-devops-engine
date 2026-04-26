"""
EmbodiedOS — Unified three-layer memory (Section 4.6).

Layer 1 — Session memory   (in-process, per-mission ring buffer).
Layer 2 — Episodic memory  (SQLite, FTS5 if available, mission summaries).
Layer 3 — Procedural memory (skills + rhodawk.knowledge graph).

The store is intentionally simple.  Heavy semantic search is delegated to
the existing ``rhodawk.knowledge`` module (Neo4j / vector DB) when
present; if it's not, we degrade to SQLite LIKE/FTS5 which is more than
adequate for a few thousand entries.

Concurrency: a single ``threading.Lock`` is held around every SQLite
write.  Reads use a connection-per-call pattern with WAL mode, so reads
never block writes for long.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from embodied.config import get_config
from embodied.skills.sync_engine import get_engine as get_skill_engine

LOG = logging.getLogger("embodied.memory.unified_memory")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SessionBuffer:
    mission_id: str
    events: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=512))


# ---------------------------------------------------------------------------
# UnifiedMemory
# ---------------------------------------------------------------------------


class UnifiedMemory:
    def __init__(self) -> None:
        cfg = get_config().memory
        self.episodic_path: Path = cfg.episodic_db
        try:
            self.episodic_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fallback when /data is not writable (e.g. local dev).
            self.episodic_path = Path("/tmp") / self.episodic_path.name
            self.episodic_path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, SessionBuffer] = {}
        self._sessions_lock = threading.Lock()
        self._db_lock = threading.Lock()
        self._init_db()

    # ------------------------------------------------------------------ DB

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.episodic_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._db_lock, self._connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts          REAL    NOT NULL,
                    summary     TEXT    NOT NULL,
                    metadata    TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_episodes_ts ON episodes(ts);
                CREATE TABLE IF NOT EXISTS session_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts          REAL    NOT NULL,
                    mission_id  TEXT    NOT NULL,
                    event       TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_session_mission ON session_log(mission_id);
                """
            )
            # Try FTS5 (fast text search). Skip silently if unavailable.
            try:
                c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts
                             USING fts5(summary, metadata,
                                        content='episodes', content_rowid='id');""")
                c.executescript(
                    """
                    CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
                        INSERT INTO episodes_fts(rowid, summary, metadata)
                        VALUES (new.id, new.summary, new.metadata);
                    END;
                    CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
                        INSERT INTO episodes_fts(episodes_fts, rowid, summary, metadata)
                        VALUES ('delete', old.id, old.summary, old.metadata);
                    END;
                    """
                )
            except sqlite3.OperationalError:
                LOG.info("FTS5 unavailable — episodic search will fall back to LIKE.")

    # --------------------------------------------------------- Layer 1 — session

    def write_session(self, *, mission_id: str, event: dict[str, Any]) -> None:
        ev = {"ts": time.time(), **event}
        with self._sessions_lock:
            buf = self._sessions.setdefault(mission_id, SessionBuffer(mission_id))
            buf.events.append(ev)
        try:
            with self._db_lock, self._connect() as c:
                c.execute("INSERT INTO session_log(ts, mission_id, event) VALUES(?,?,?)",
                          (ev["ts"], mission_id, json.dumps(ev)))
        except Exception as exc:  # noqa: BLE001
            LOG.info("session_log insert failed: %s", exc)

    def session_recent(self, mission_id: str, *, limit: int = 64) -> list[dict[str, Any]]:
        with self._sessions_lock:
            buf = self._sessions.get(mission_id)
            if buf:
                return list(buf.events)[-limit:]
        try:
            with self._db_lock, self._connect() as c:
                rows = c.execute(
                    "SELECT event FROM session_log WHERE mission_id=? ORDER BY id DESC LIMIT ?",
                    (mission_id, limit),
                ).fetchall()
            return [json.loads(r[0]) for r in rows][::-1]
        except Exception:  # noqa: BLE001
            return []

    # ------------------------------------------------------- Layer 2 — episodic

    def episodic_add(self, *, summary: str, metadata: dict[str, Any]) -> int:
        try:
            with self._db_lock, self._connect() as c:
                cur = c.execute(
                    "INSERT INTO episodes(ts, summary, metadata) VALUES(?,?,?)",
                    (time.time(), summary, json.dumps(metadata, default=str)),
                )
                return int(cur.lastrowid or 0)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("episodic_add failed: %s", exc)
            return -1

    def episodic_query(self, *, query: str, limit: int = 25) -> list[dict[str, Any]]:
        try:
            with self._db_lock, self._connect() as c:
                try:
                    rows = c.execute(
                        "SELECT episodes.id, episodes.ts, episodes.summary, episodes.metadata "
                        "FROM episodes JOIN episodes_fts ON episodes_fts.rowid=episodes.id "
                        "WHERE episodes_fts MATCH ? ORDER BY episodes.ts DESC LIMIT ?",
                        (query, limit),
                    ).fetchall()
                except sqlite3.OperationalError:
                    rows = c.execute(
                        "SELECT id, ts, summary, metadata FROM episodes "
                        "WHERE summary LIKE ? OR metadata LIKE ? ORDER BY ts DESC LIMIT ?",
                        (f"%{query}%", f"%{query}%", limit),
                    ).fetchall()
        except Exception:  # noqa: BLE001
            return []
        return [
            {"id": r[0], "ts": r[1], "summary": r[2], "metadata": json.loads(r[3] or "{}")}
            for r in rows
        ]

    # ---------------------------------------------------- Layer 3 — procedural

    def procedural_save_skill(self, *, name: str, frontmatter: dict[str, Any], body: str) -> dict[str, Any]:
        # Persist into the skills catalogue (canonical agentskills.io shape).
        engine_result = get_skill_engine().save_auto_skill(name=name, frontmatter=frontmatter, body=body)

        # Also push into the rhodawk knowledge graph if it exists.
        try:
            from rhodawk import knowledge  # type: ignore
            if hasattr(knowledge, "remember_skill"):
                knowledge.remember_skill(name=name, frontmatter=frontmatter, body=body)
        except Exception:  # noqa: BLE001
            pass

        # And into episodic so it's searchable forever.
        self.episodic_add(
            summary=f"[SkillLearned] {name}",
            metadata={"frontmatter": frontmatter, "body": body[:512]},
        )
        return engine_result

    def procedural_search(self, *, query: str, top_k: int = 8) -> str:
        return get_skill_engine().select_for_task(task_description=query, top_k=top_k)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


_MEM: UnifiedMemory | None = None
_MEM_LOCK = threading.Lock()


def get_memory() -> UnifiedMemory:
    global _MEM
    with _MEM_LOCK:
        if _MEM is None:
            _MEM = UnifiedMemory()
        return _MEM
