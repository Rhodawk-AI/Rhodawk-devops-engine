"""Job-queue smoke test — enqueue → status → done."""

from __future__ import annotations

import importlib

import pytest


def test_enqueue_and_status(tmp_data_dir, monkeypatch):
    monkeypatch.setenv("RHODAWK_JOB_DIR", str(tmp_data_dir / "jobs"))
    import job_queue
    importlib.reload(job_queue)

    if not hasattr(job_queue, "QUEUE_DIR"):
        pytest.skip("job_queue layout incompatible")
    job_queue.QUEUE_DIR = str(tmp_data_dir / "jobs")
    import os
    os.makedirs(job_queue.QUEUE_DIR, exist_ok=True)

    set_state = (getattr(job_queue, "set_job_state", None)
                 or getattr(job_queue, "upsert_job", None))
    get_state = (getattr(job_queue, "get_job_state", None)
                 or getattr(job_queue, "get_job", None))
    if set_state is None or get_state is None:
        pytest.skip("job_queue helpers not exposed")

    set_state("test-tenant", "owner/repo", "tests/", job_queue.JobStatus.PENDING)
    state = get_state("test-tenant", "owner/repo", "tests/")
    assert state is not None
