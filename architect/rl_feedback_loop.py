"""
RL Feedback Loop — OpenClaw-RL inspired async 4-component policy improver.

Adapted from Gen-Verse/OpenClaw-RL (Apache-2.0).  We don't run real GPU
training inside the Space — that lives on the OpenClaw fleet.  This
module is the *local* half: it captures every (prompt, response, reward)
trace, scores it via a binary judge + composite scorer, and periodically
ships a batch to the OpenClaw webhook so the LoRA adapter for the Tier-5
local model improves over time.

Components:

    1. Rollout collector   — every call_with_skills() emits a Trace.
    2. PRM / judge         — scores the trace (binary RL + composite RL).
    3. Trace store         — append-only JSONL on disk.
    4. Trainer dispatcher  — flush in batches via embodied_bridge.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOG = logging.getLogger("architect.rl_feedback_loop")

TRACE_PATH = Path(os.getenv("RHODAWK_RL_TRACE", "/data/rl_traces.jsonl"))
BATCH_SIZE = int(os.getenv("RHODAWK_RL_BATCH", "50"))
LOCK = threading.Lock()


@dataclass
class Trace:
    ts: float
    task: str
    model: str
    prompt: str
    response: str
    profile: dict[str, Any] = field(default_factory=dict)
    reward_binary: int = 0          # 1 useful / 0 neutral / -1 wasteful
    reward_composite: float = 0.0   # 0-100, from godmode_consensus.default_scorer
    judge_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ── Judge ──────────────────────────────────────────────────────────────────
def _judge(prompt: str, response: str) -> tuple[int, float, str]:
    """Cheap heuristic judge — same composite as godmode_consensus, plus
    a binary signal (-1 / 0 / +1)."""
    try:
        from .godmode_consensus import default_scorer
    except Exception:  # noqa: BLE001
        return 0, 0.0, "scorer-unavailable"
    composite, _ = default_scorer(response)
    if composite >= 70.0:
        binary = 1
        note = "high-quality response"
    elif composite < 30.0 or "i cannot" in response.lower() or "i am unable" in response.lower():
        binary = -1
        note = "refusal or low-content"
    else:
        binary = 0
        note = "neutral"
    return binary, composite, note


# ── Rollout collector ──────────────────────────────────────────────────────
def record(
    *,
    task: str,
    model: str,
    prompt: str,
    response: str,
    profile: dict[str, Any] | None = None,
    extra_judge: tuple[int, float, str] | None = None,
) -> Trace:
    binary, composite, note = extra_judge or _judge(prompt, response)
    tr = Trace(
        ts=time.time(),
        task=task,
        model=model,
        prompt=prompt[:8000],
        response=response[:8000],
        profile=dict(profile or {}),
        reward_binary=binary,
        reward_composite=composite,
        judge_notes=note,
    )
    _append(tr)
    if _count_traces() >= BATCH_SIZE:
        try:
            flush()
        except Exception as exc:  # noqa: BLE001
            LOG.warning("flush failed: %s", exc)
    return tr


def _append(tr: Trace) -> None:
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK, TRACE_PATH.open("a") as f:
        f.write(json.dumps(tr.to_dict()) + "\n")


def _count_traces() -> int:
    if not TRACE_PATH.exists():
        return 0
    with TRACE_PATH.open("rb") as f:
        # cheap line-count
        return sum(1 for _ in f)


# ── Trainer dispatcher ─────────────────────────────────────────────────────
def flush(*, max_lines: int | None = None) -> dict[str, Any]:
    """Ship all currently-stored traces to the OpenClaw fleet for LoRA
    training, then truncate the local file."""
    if not TRACE_PATH.exists():
        return {"flushed": 0, "dispatched": False}
    with LOCK:
        with TRACE_PATH.open() as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        if not lines:
            return {"flushed": 0, "dispatched": False}
        batch = lines if max_lines is None else lines[:max_lines]
        try:
            from . import embodied_bridge
            ack = embodied_bridge.dispatch_to_openclaw(
                "lora_finetune",
                {"traces": [json.loads(b) for b in batch],
                 "format": "binary+composite",
                 "submitted_at": time.time()},
            )
        except Exception as exc:  # noqa: BLE001
            LOG.warning("openclaw dispatch failed: %s", exc)
            return {"flushed": 0, "dispatched": False, "error": str(exc)}
        # Keep only the unflushed tail.
        tail = lines[len(batch):]
        with TRACE_PATH.open("w") as f:
            for ln in tail:
                f.write(ln + "\n")
        return {"flushed": len(batch), "dispatched": ack.get("dispatched", False),
                "ack": ack, "remaining": len(tail)}


def stats() -> dict[str, Any]:
    if not TRACE_PATH.exists():
        return {"pending": 0, "path": str(TRACE_PATH)}
    n = _count_traces()
    pos = neg = 0
    with TRACE_PATH.open() as f:
        for ln in f:
            try:
                j = json.loads(ln)
                if j.get("reward_binary", 0) > 0:
                    pos += 1
                elif j.get("reward_binary", 0) < 0:
                    neg += 1
            except Exception:
                pass
    return {"pending": n, "positive": pos, "negative": neg,
            "neutral": n - pos - neg, "path": str(TRACE_PATH),
            "batch_size": BATCH_SIZE}


# ── Optional language-feedback channel (OpenClaw-RL §3.4) ──────────────────
def submit_language_feedback(
    *, trace_id: str | int, feedback: str, polarity: int
) -> dict[str, Any]:
    """
    Push a free-form natural-language operator feedback onto the queue
    (mirrors OpenClaw-RL's "talk to your agent" interface).
    """
    return record(
        task="operator_feedback",
        model="(operator)",
        prompt=str(trace_id),
        response=feedback,
        extra_judge=(polarity, 100.0 if polarity > 0 else 0.0,
                     "operator_language_feedback"),
    ).to_dict()
