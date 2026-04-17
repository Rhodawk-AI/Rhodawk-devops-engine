"""
Rhodawk AI — Namespaced Job Queue
===================================
Replaces the flat single-tenant STATE_FILE with a proper namespaced job store.
Each job is keyed by (tenant_id, repo, test_path) — ready for multi-tenant SaaS.
State is persisted as atomic JSON writes. Future path: swap backing store to PostgreSQL.
"""

import hashlib
import json
import os
import threading
import time
from enum import Enum
from typing import Optional

QUEUE_DIR = "/data/jobs"
_queue_lock = threading.Lock()


class JobStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SAST_BLOCKED = "SAST_BLOCKED"
    DONE = "DONE"
    FAILED = "FAILED"


def _job_id(tenant_id: str, repo: str, test_path: str) -> str:
    raw = f"{tenant_id}::{repo}::{test_path}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _job_path(job_id: str) -> str:
    os.makedirs(QUEUE_DIR, exist_ok=True)
    return os.path.join(QUEUE_DIR, f"{job_id}.json")


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
    job_id = _job_id(tenant_id, repo, test_path)
    path = _job_path(job_id)

    with _queue_lock:
        existing = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        job = {
            **existing,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "repo": repo,
            "test_path": test_path,
            "status": status.value,
            "detail": detail,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        if "created_at" not in job:
            job["created_at"] = job["updated_at"]
        if pr_url is not None:
            job["pr_url"] = pr_url
        if sast_findings is not None:
            job["sast_findings_count"] = len(sast_findings)
        if model_version is not None:
            job["model_version"] = model_version
        if prompt_hash is not None:
            job["prompt_hash"] = prompt_hash

        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(job, f, indent=2)
        os.replace(tmp_path, path)

    return job_id


def get_job(tenant_id: str, repo: str, test_path: str) -> Optional[dict]:
    job_id = _job_id(tenant_id, repo, test_path)
    path = _job_path(job_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def get_job_status_enum(tenant_id: str, repo: str, test_path: str) -> Optional[JobStatus]:
    job = get_job(tenant_id, repo, test_path)
    if not job:
        return None
    try:
        return JobStatus(job["status"])
    except ValueError:
        return None


def list_all_jobs() -> list[dict]:
    if not os.path.exists(QUEUE_DIR):
        return []
    jobs = []
    for fname in sorted(os.listdir(QUEUE_DIR)):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(QUEUE_DIR, fname)) as f:
                jobs.append(json.load(f))
        except Exception:
            pass
    return sorted(jobs, key=lambda j: j.get("updated_at", ""), reverse=True)


def get_metrics() -> dict:
    jobs = list_all_jobs()
    return {
        "total": len(jobs),
        "done": sum(1 for j in jobs if j["status"] == "DONE"),
        "failed": sum(1 for j in jobs if j["status"] == "FAILED"),
        "running": sum(1 for j in jobs if j["status"] == "RUNNING"),
        "sast_blocked": sum(1 for j in jobs if j["status"] == "SAST_BLOCKED"),
        "prs_created": sum(1 for j in jobs if j.get("pr_url")),
    }
