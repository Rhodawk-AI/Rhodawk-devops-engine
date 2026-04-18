"""
Rhodawk AI — LoRA Fine-Tune Scheduler
======================================
Schedules periodic LoRA adapter fine-tuning runs using accumulated
(failure, fix) pairs from the training store.

This is NOT a training pipeline — it exports the training data in JSONL
format ready for consumption by:
  - Hugging Face PEFT + TRL (local SFT)
  - Hugging Face AutoTrain API
  - OpenRouter/Together batch fine-tune API (when available)

The scheduler monitors fix_success_rate and triggers a training export
when enough new high-quality data has accumulated since the last run.

Trigger conditions (any one sufficient):
  - NEW_GOOD_FIXES >= LORA_MIN_SAMPLES (default 50) since last run
  - Time since last run >= LORA_MAX_AGE_HOURS (default 168 = 1 week)

Output artifact: /data/lora_training_data_{timestamp}.jsonl
Format: standard chat-format instruction tuning JSONL:
  {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

Enable: RHODAWK_LORA_ENABLED=true
"""

import json
import os
import sqlite3
import time

from training_store import DB_PATH

LORA_ENABLED     = os.getenv("RHODAWK_LORA_ENABLED", "false").lower() == "true"
LORA_MIN_SAMPLES = int(os.getenv("RHODAWK_LORA_MIN_SAMPLES", "50"))
LORA_MAX_AGE_H   = int(os.getenv("RHODAWK_LORA_MAX_AGE_HOURS", "168"))
LORA_OUTPUT_DIR  = os.getenv("RHODAWK_LORA_OUTPUT_DIR", "/data/lora_exports")
LORA_STATE_PATH  = "/data/lora_scheduler_state.json"

SYSTEM_PROMPT = (
    "You are Rhodawk, an expert AI software engineer specializing in debugging "
    "and fixing failing automated tests. You produce minimal, correct, secure "
    "code fixes. You think step-by-step about the root cause before proposing a fix."
)


def _load_state() -> dict:
    if not os.path.exists(LORA_STATE_PATH):
        return {"last_run_ts": 0, "last_run_count": 0, "total_exports": 0}
    try:
        with open(LORA_STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {"last_run_ts": 0, "last_run_count": 0, "total_exports": 0}


def _save_state(state: dict) -> None:
    with open(LORA_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _count_good_fixes_since(since_count: int) -> int:
    """Count successful fix attempts added since the last export."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM fix_attempts WHERE success_signal = 1"
            ).fetchone()[0]
        return max(0, total - since_count)
    except Exception:
        return 0


def _export_training_data(min_success: int = 1, limit: int = 2000) -> list[dict]:
    """Export (failure, fix) pairs as chat-format messages."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT fa.failure_output, fa.diff_produced, fa.test_path
                FROM fix_attempts fa
                WHERE fa.success_signal = 1
                  AND fa.diff_produced IS NOT NULL
                  AND fa.diff_produced != ''
                ORDER BY fa.created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
    except Exception:
        return []

    examples = []
    for row in rows:
        failure = (row["failure_output"] or "")[:3000]
        diff    = (row["diff_produced"] or "")[:4000]
        test    = row["test_path"] or "unknown"

        user_content = (
            f"The following test is failing:\n"
            f"Test: `{test}`\n\n"
            f"Failure output:\n```\n{failure}\n```\n\n"
            f"Produce a minimal, secure diff to make this test pass. "
            f"Do NOT modify the test file itself."
        )
        assistant_content = (
            f"Here is the minimal fix:\n\n```diff\n{diff}\n```\n\n"
            f"This fix addresses the root cause shown in the failure output."
        )

        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ]
        })

    return examples


def should_trigger_training() -> tuple[bool, str]:
    """
    Check whether training conditions are met.
    Returns (should_run, reason).
    """
    if not LORA_ENABLED:
        return False, "LoRA scheduler disabled (RHODAWK_LORA_ENABLED != true)"

    state = _load_state()
    now = time.time()
    age_hours = (now - state["last_run_ts"]) / 3600
    new_fixes = _count_good_fixes_since(state["last_run_count"])

    if new_fixes >= LORA_MIN_SAMPLES:
        return True, f"{new_fixes} new good fixes (threshold: {LORA_MIN_SAMPLES})"

    if state["last_run_ts"] > 0 and age_hours >= LORA_MAX_AGE_H:
        return True, f"Max age {age_hours:.1f}h >= {LORA_MAX_AGE_H}h"

    return False, (
        f"Not triggered: {new_fixes}/{LORA_MIN_SAMPLES} new fixes, "
        f"{age_hours:.1f}h/{LORA_MAX_AGE_H}h elapsed"
    )


def run_training_export() -> dict:
    """
    Export training data to a JSONL file.
    Returns metadata about the export.
    """
    os.makedirs(LORA_OUTPUT_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(LORA_OUTPUT_DIR, f"lora_training_data_{timestamp}.jsonl")

    examples = _export_training_data()
    if not examples:
        return {
            "status": "skipped",
            "reason": "no training examples available",
            "path": None,
            "count": 0,
        }

    with open(out_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    state = _load_state()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            total_good = conn.execute(
                "SELECT COUNT(*) FROM fix_attempts WHERE success_signal = 1"
            ).fetchone()[0]
    except Exception:
        total_good = state["last_run_count"]

    new_state = {
        "last_run_ts": time.time(),
        "last_run_count": total_good,
        "total_exports": state["total_exports"] + 1,
        "last_export_path": out_path,
        "last_export_count": len(examples),
    }
    _save_state(new_state)

    return {
        "status": "ok",
        "path": out_path,
        "count": len(examples),
        "timestamp": timestamp,
    }


def maybe_trigger_training() -> str:
    """
    Call this after each audit cycle. Triggers export if conditions are met.
    Returns a human-readable status string for dashboard display.
    """
    should, reason = should_trigger_training()
    if not should:
        return f"LoRA scheduler: waiting — {reason}"

    result = run_training_export()
    if result["status"] == "ok":
        return (
            f"LoRA export triggered: {result['count']} examples → {result['path']} "
            f"({reason})"
        )
    return f"LoRA export skipped: {result.get('reason', 'unknown')}"


def get_scheduler_status() -> str:
    """Human-readable scheduler status for the dashboard."""
    if not LORA_ENABLED:
        return "LoRA scheduler disabled. Set RHODAWK_LORA_ENABLED=true to enable."
    state = _load_state()
    new_fixes = _count_good_fixes_since(state.get("last_run_count", 0))
    last_run = state.get("last_run_ts", 0)
    last_export = state.get("last_export_path", "none")
    last_count = state.get("last_export_count", 0)
    total = state.get("total_exports", 0)

    last_run_str = (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_run))
        if last_run > 0 else "never"
    )

    return (
        f"LoRA Scheduler Status:\n"
        f"  Last export:  {last_run_str} ({last_count} examples)\n"
        f"  Total exports: {total}\n"
        f"  New good fixes since last export: {new_fixes}/{LORA_MIN_SAMPLES}\n"
        f"  Last file: {last_export}\n"
        f"  Min samples threshold: {LORA_MIN_SAMPLES}\n"
        f"  Max age: {LORA_MAX_AGE_H}h\n"
    )
