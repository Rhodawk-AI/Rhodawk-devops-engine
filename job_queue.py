"""
Rhodawk AI — Namespaced Job Queue (SQLite backed, v2 — Apr 2026)
================================================================
Replaces the original per-file JSON store with a single SQLite database so
that concurrent writers (web UI + nightmode + OSS-Guardian) never race on
``open(...).replace(...)``.  All previous JSON files in ``/data/jobs/``
are imported on first start, then ignored.

The public API is intentionally identical to the v1 module so callers
do not need to change.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("job_queue")

QUEUE_DIR = "/data/jobs"               # legacy JSON dir, kept for migration
DB_PATH   = os.getenv("JOB_QUEUE_DB", "/data/jobs.sqlite")
_LOCK = threading.Lock()


class JobStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SAST_BLOCKED = "SAST_BLOCKED"
    DONE = "DONE"
    FAILED = "FAILED"


def _job_id(tenant_id: str, repo: str, test_path: str) -> str:
    raw = f"{tenant_id}::{repo}::{test_path}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id              TEXT PRIMARY KEY,
            tenant_id           TEXT NOT NULL,
            repo                TEXT NOT NULL,
            test_path           TEXT NOT NULL,
            status              TEXT NOT NULL,
            detail              TEXT NOT NULL DEFAULT '',
            pr_url              TEXT,
            sast_findings_count INTEGER,
            model_version       TEXT,
            prompt_hash         TEXT,
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON jobs(tenant_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, updated_at)")
    return conn


def _migrate_legacy_json() -> int:
    """One-shot import of any leftover ``/data/jobs/*.json`` files."""
    if not os.path.isdir(QUEUE_DIR):
        return 0
    imported = 0
    for fname in os.listdir(QUEUE_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(QUEUE_DIR, fname)
        try:
            with open(path) as f:
                j = json.load(f)
            with _connect() as c:
                c.execute("""
                    INSERT OR IGNORE INTO jobs
                    (job_id, tenant_id, repo, test_path, status, detail,
                     pr_url, sast_findings_count, model_version, prompt_hash,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    j.get("job_id") or _job_id(j.get("tenant_id", ""),
                                               j.get("repo", ""),
                                               j.get("test_path", "")),
                    j.get("tenant_id", ""),
                    j.get("repo", ""),
                    j.get("test_path", ""),
                    j.get("status", "PENDING"),
                    j.get("detail", "") or "",
                    j.get("pr_url"),
                    j.get("sast_findings_count"),
                    j.get("model_version"),
                    j.get("prompt_hash"),
                    j.get("created_at") or j.get("updated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    j.get("updated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ))
            os.rename(path, path + ".imported")
            imported += 1
        except Exception as exc:  # noqa: BLE001
            LOG.warning("migrate %s failed: %s", path, exc)
    return imported


_MIGRATED = False


def _ensure_migrated() -> None:
    global _MIGRATED
    if _MIGRATED:
        return
    with _LOCK:
        if _MIGRATED:
            return
        _migrate_legacy_json()
        _MIGRATED = True


def upsert_job(
    tenant_id: str,
    repo: str,
    test_path: str,
    status: JobStatus,
    detail: str = "",
    pr_url: Optional[str] = None,
    sast_findings: Optional[list] = None,
    model_version: Optional[str] = None,
    prompt_hash: Optional[str] = None,
) -> str:
    _ensure_migrated()
    jid = _job_id(tenant_id, repo, test_path)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    findings_count = len(sast_findings) if sast_findings is not None else None
    with _LOCK, _connect() as c:
        existing = c.execute(
            "SELECT created_at FROM jobs WHERE job_id=?", (jid,)
        ).fetchone()
        created = existing[0] if existing else now
        c.execute("""
            INSERT INTO jobs (job_id, tenant_id, repo, test_path, status,
                              detail, pr_url, sast_findings_count,
                              model_version, prompt_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status              = excluded.status,
                detail              = excluded.detail,
                pr_url              = COALESCE(excluded.pr_url, jobs.pr_url),
                sast_findings_count = COALESCE(excluded.sast_findings_count, jobs.sast_findings_count),
                model_version       = COALESCE(excluded.model_version, jobs.model_version),
                prompt_hash         = COALESCE(excluded.prompt_hash, jobs.prompt_hash),
                updated_at          = excluded.updated_at
        """, (jid, tenant_id, repo, test_path, status.value, detail or "",
              pr_url, findings_count, model_version, prompt_hash, created, now))
    return jid


def get_job(tenant_id: str, repo: str, test_path: str) -> Optional[dict]:
    _ensure_migrated()
    jid = _job_id(tenant_id, repo, test_path)
    with _connect() as c:
        c.row_factory = sqlite3.Row
        row = c.execute("SELECT * FROM jobs WHERE job_id=?", (jid,)).fetchone()
    return dict(row) if row else None


def get_job_status_enum(tenant_id: str, repo: str, test_path: str) -> Optional[JobStatus]:
    job = get_job(tenant_id, repo, test_path)
    if not job:
        return None
    try:
        return JobStatus(job["status"])
    except ValueError:
        return None


def list_all_jobs() -> list[dict]:
    _ensure_migrated()
    with _connect() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            "SELECT * FROM jobs ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_metrics() -> dict:
    _ensure_migrated()
    with _connect() as c:
        total = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        by_status = dict(c.execute(
            "SELECT status, COUNT(*) FROM jobs GROUP BY status"
        ).fetchall())
        prs = c.execute(
            "SELECT COUNT(*) FROM jobs WHERE pr_url IS NOT NULL AND pr_url != ''"
        ).fetchone()[0]
    return {
        "total":        total,
        "done":         by_status.get("DONE", 0),
        "failed":       by_status.get("FAILED", 0),
        "running":      by_status.get("RUNNING", 0),
        "sast_blocked": by_status.get("SAST_BLOCKED", 0),
        "prs_created":  prs,
    }


def prune_done_jobs(max_age_hours: int = 72) -> int:
    """Remove DONE/FAILED jobs older than ``max_age_hours``."""
    _ensure_migrated()
    cutoff_ts = time.time() - (max_age_hours * 3600)
    cutoff_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(cutoff_ts))
    with _LOCK, _connect() as c:
        cur = c.execute("""
            DELETE FROM jobs
            WHERE status IN ('DONE', 'FAILED')
              AND updated_at < ?
        """, (cutoff_iso,))
        return cur.rowcount or 0
