"""
Rhodawk AI — Immutable Audit Trail Engine
==========================================
Every AI action is appended to an append-only JSONL file with SHA-256 chaining.
Each entry references the hash of the previous entry, creating a tamper-evident
chain of custody for every line of AI-generated code. Required for SOC 2 / ISO 27001.
"""

import hashlib
import json
import os
import threading
import time
from typing import Optional

AUDIT_LOG_PATH = "/data/audit_trail.jsonl"
_audit_write_lock = threading.Lock()

_last_hash: Optional[str] = None


def _compute_hash(entry: dict) -> str:
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _get_last_hash() -> str:
    global _last_hash
    if _last_hash:
        return _last_hash
    if not os.path.exists(AUDIT_LOG_PATH):
        return "GENESIS"
    try:
        with open(AUDIT_LOG_PATH, "rb") as f:
            lines = f.read().splitlines()
            if not lines:
                return "GENESIS"
            last_line = lines[-1].decode("utf-8").strip()
            if not last_line:
                return "GENESIS"
            last_entry = json.loads(last_line)
            _last_hash = last_entry.get("entry_hash", "GENESIS")
            return _last_hash
    except Exception:
        return "GENESIS"


def log_audit_event(
    event_type: str,
    job_id: str,
    repo: str,
    model: str,
    details: dict,
    outcome: str = "PENDING",
) -> str:
    """
    Append an audit event to the immutable JSONL chain.
    Returns the entry hash for cross-referencing.
    """
    global _last_hash

    with _audit_write_lock:
        prev_hash = _get_last_hash()

        entry = {
            "schema_version": "1.0",
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "unix_ts": time.time(),
            "event_type": event_type,
            "job_id": job_id,
            "repo": repo,
            "model_version": model,
            "outcome": outcome,
            "details": details,
            "prev_hash": prev_hash,
        }

        entry_hash = _compute_hash(entry)
        entry["entry_hash"] = entry_hash

        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")

        _last_hash = entry_hash
        return entry_hash


def read_audit_trail(limit: int = 50) -> list[dict]:
    """Return the last N audit events for dashboard display."""
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
    events = []
    try:
        with open(AUDIT_LOG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        return []
    return events[-limit:]


def verify_chain_integrity() -> tuple[bool, str]:
    """
    Walk the entire audit chain and verify each entry's hash.
    Returns (is_valid, summary_message).
    Used for compliance attestation.
    """
    if not os.path.exists(AUDIT_LOG_PATH):
        return True, "No audit log yet — chain is clean."

    events = []
    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    if not events:
        return True, "Empty log — chain is clean."

    for i, entry in enumerate(events):
        stored_hash = entry.pop("entry_hash", None)
        computed = _compute_hash(entry)
        entry["entry_hash"] = stored_hash

        if computed != stored_hash:
            return False, f"CHAIN BROKEN at entry {i} (event: {entry.get('event_type')}). Possible tampering detected."

        if i > 0:
            expected_prev = events[i - 1]["entry_hash"]
            if entry["prev_hash"] != expected_prev:
                return False, f"HASH CHAIN BROKEN between entries {i-1} and {i}."

    return True, f"Chain VERIFIED — {len(events)} entries, all hashes valid."


def export_compliance_report(output_path: str = "/data/rhodawk_soc2_audit_summary.md") -> str:
    events = read_audit_trail(limit=100000)
    valid, integrity_msg = verify_chain_integrity()
    by_type: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    repos: dict[str, int] = {}
    for event in events:
        by_type[event.get("event_type", "UNKNOWN")] = by_type.get(event.get("event_type", "UNKNOWN"), 0) + 1
        by_outcome[event.get("outcome", "UNKNOWN")] = by_outcome.get(event.get("outcome", "UNKNOWN"), 0) + 1
        repos[event.get("repo", "unknown")] = repos.get(event.get("repo", "unknown"), 0) + 1

    report = [
        "# Rhodawk AI SOC 2 Audit Evidence Summary",
        "",
        f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"Chain integrity: {'VERIFIED' if valid else 'COMPROMISED'}",
        f"Integrity detail: {integrity_msg}",
        f"Total audit events: {len(events)}",
        "",
        "## Event Types",
        "",
        *[f"- {name}: {count}" for name, count in sorted(by_type.items())],
        "",
        "## Outcomes",
        "",
        *[f"- {name}: {count}" for name, count in sorted(by_outcome.items())],
        "",
        "## Repository Coverage",
        "",
        *[f"- {name}: {count} event(s)" for name, count in sorted(repos.items())],
        "",
        "## Latest Evidence Entries",
        "",
    ]
    for event in events[-25:]:
        report.append(
            f"- `{event.get('timestamp_utc')}` `{event.get('event_type')}` "
            f"`{event.get('outcome')}` hash `{event.get('entry_hash', '')[:16]}`"
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    return output_path
