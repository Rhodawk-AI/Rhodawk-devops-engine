"""
Rhodawk AI — Concurrent Worker Pool
====================================
ThreadPoolExecutor-based audit orchestration for parallel test healing.
"""

import concurrent.futures
import os
import threading
from typing import Callable

MAX_WORKERS = int(os.getenv("RHODAWK_WORKERS", "8"))
_pool_lock = threading.Lock()


def run_parallel_audit(
    test_files: list[str],
    process_fn: Callable,
    pytest_bin: str,
    mcp_config_path: str,
    tenant_id: str,
    target_repo: str,
) -> dict:
    results = {"healed": 0, "failed": 0, "skipped": 0, "prs": [], "errors": []}

    if not test_files:
        return results

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                _process_one_test,
                test_path=t,
                process_fn=process_fn,
                pytest_bin=pytest_bin,
                mcp_config_path=mcp_config_path,
                tenant_id=tenant_id,
                repo=target_repo,
            ): t
            for t in test_files
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                outcome = future.result()
            except Exception as e:
                outcome = {"success": False, "error": str(e)}

            if outcome.get("skipped"):
                results["skipped"] += 1
            elif outcome.get("success"):
                results["healed"] += 1
                if outcome.get("pr_url"):
                    results["prs"].append(outcome.get("pr_url"))
            else:
                results["failed"] += 1
                if outcome.get("error"):
                    results["errors"].append(outcome["error"])

    return results


def _process_one_test(
    test_path: str,
    process_fn: Callable,
    pytest_bin: str,
    mcp_config_path: str,
    tenant_id: str,
    repo: str,
) -> dict:
    return process_fn(
        test_path=test_path,
        pytest_bin=pytest_bin,
        mcp_config_path=mcp_config_path,
        tenant_id=tenant_id,
        target_repo=repo,
    )