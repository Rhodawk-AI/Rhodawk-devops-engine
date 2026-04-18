"""
Rhodawk AI — Concurrent Worker Pool (Process-Isolated Edition)
==============================================================
ThreadPoolExecutor-based audit orchestration with optional process isolation.

Process isolation mode (RHODAWK_PROCESS_ISOLATE=true):
  Each test repair runs in its own subprocess via multiprocessing.Process.
  This prevents:
    - A crashing fix attempt from killing the orchestrator
    - Memory leaks accumulating across many test repairs
    - Global state corruption from aggressive Aider subprocess calls
    - One tenant's runaway fix from starving others

  Isolation overhead: ~200ms per test (fork cost). Acceptable given tests
  typically take seconds. Not recommended for < 5-second test suites.

Default (RHODAWK_PROCESS_ISOLATE=false):
  Original ThreadPoolExecutor behavior — shared memory, low overhead.

BUG-001 FIX: Updated signature to accept env_config: EnvConfig instead of
             pytest_bin: str to match app.py's call site.
BUG-011 FIX: Tests returning already_green=True are no longer counted as
             "healed" — they are counted under a separate "already_green" key.
"""

import concurrent.futures
import multiprocessing
import os
import threading
import traceback
from typing import Callable

MAX_WORKERS = int(os.getenv("RHODAWK_WORKERS", "8"))
PROCESS_ISOLATE = os.getenv("RHODAWK_PROCESS_ISOLATE", "false").lower() == "true"
ISOLATION_TIMEOUT = int(os.getenv("RHODAWK_ISOLATE_TIMEOUT", "600"))

_pool_lock = threading.Lock()


def _isolated_worker(
    result_queue: multiprocessing.Queue,
    test_path: str,
    process_fn_module: str,
    process_fn_name: str,
    env_config,
    mcp_config_path: str,
    tenant_id: str,
    repo: str,
) -> None:
    """
    Runs inside a child process. Imports the module fresh, calls process_fn,
    puts the result on the queue.
    """
    try:
        import importlib
        mod = importlib.import_module(process_fn_module)
        fn = getattr(mod, process_fn_name)
        result = fn(
            test_path=test_path,
            env_config=env_config,
            mcp_config_path=mcp_config_path,
            tenant_id=tenant_id,
            target_repo=repo,
        )
        result_queue.put({"ok": True, "result": result})
    except Exception as e:
        result_queue.put({"ok": False, "error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc()})


def _run_isolated(
    test_path: str,
    process_fn: Callable,
    env_config,
    mcp_config_path: str,
    tenant_id: str,
    repo: str,
) -> dict:
    """
    Run process_fn in a subprocess. Falls back to in-process on spawn failure.
    """
    # Determine module + name so the child can import it fresh
    module_name = getattr(process_fn, "__module__", None)
    fn_name = getattr(process_fn, "__name__", None)

    if not module_name or not fn_name:
        return _process_one_test(test_path, process_fn, env_config, mcp_config_path, tenant_id, repo)

    ctx = multiprocessing.get_context("fork")
    q: multiprocessing.Queue = ctx.Queue()

    p = ctx.Process(
        target=_isolated_worker,
        args=(q, test_path, module_name, fn_name, env_config, mcp_config_path, tenant_id, repo),
        daemon=True,
    )
    p.start()
    p.join(timeout=ISOLATION_TIMEOUT)

    if p.is_alive():
        p.kill()
        p.join()
        return {"success": False, "error": f"Isolated worker timed out after {ISOLATION_TIMEOUT}s: {test_path}"}

    if not q.empty():
        msg = q.get_nowait()
        if msg.get("ok"):
            return msg["result"]
        return {"success": False, "error": msg.get("error", "unknown error")}

    return {"success": False, "error": f"Isolated worker exited with code {p.exitcode}: {test_path}"}


def run_parallel_audit(
    test_files: list[str],
    process_fn: Callable,
    env_config,
    mcp_config_path: str,
    tenant_id: str,
    target_repo: str,
) -> dict:
    results = {"healed": 0, "failed": 0, "skipped": 0, "already_green": 0, "prs": [], "errors": []}

    if not test_files:
        return results

    runner = _run_isolated if PROCESS_ISOLATE else _process_one_test

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                runner,
                test_path=t,
                process_fn=process_fn,
                env_config=env_config,
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
            elif outcome.get("already_green"):
                results["already_green"] += 1
                if outcome.get("pr_url"):
                    results["prs"].append(outcome.get("pr_url"))
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
    env_config,
    mcp_config_path: str,
    tenant_id: str,
    repo: str,
) -> dict:
    return process_fn(
        test_path=test_path,
        env_config=env_config,
        mcp_config_path=mcp_config_path,
        tenant_id=tenant_id,
        target_repo=repo,
    )
