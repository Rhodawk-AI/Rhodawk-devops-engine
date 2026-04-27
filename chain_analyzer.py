"""
Rhodawk AI — Vulnerability Chain Analyzer
==========================================
Documents how primitive findings (individual assumption gaps + PoC results)
might combine into higher-severity chains.

ETHICAL CONSTRAINTS:
  - Chains are THEORETICAL proposals documented for human review
  - No chain is automatically executed
  - All chain proposals are stored with status PENDING_HUMAN_REVIEW
  - Human operator must approve or reject every chain before any further action

Orchestrated by Nous Hermes 3 via OpenRouter.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from typing import Optional

import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
HERMES_MODEL = os.getenv(
    "RHODAWK_RESEARCH_MODEL",
    "nousresearch/hermes-3-llama-3.1-405b:free",
)
CHAIN_DB = os.getenv("RHODAWK_CHAIN_DB", "/data/chain_memory.sqlite")


def _init_db() -> None:
    os.makedirs(os.path.dirname(CHAIN_DB), exist_ok=True)
    conn = sqlite3.connect(CHAIN_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS primitive_findings (
            id          TEXT PRIMARY KEY,
            repo        TEXT NOT NULL,
            gap_id      TEXT NOT NULL,
            severity    TEXT,
            description TEXT,
            triggered   INTEGER DEFAULT 0,
            confidence  TEXT DEFAULT 'UNKNOWN',
            created_at  REAL,
            harness_out TEXT
        );
        CREATE TABLE IF NOT EXISTS chains (
            id                TEXT PRIMARY KEY,
            repo              TEXT NOT NULL,
            primitive_ids     TEXT NOT NULL,
            description       TEXT,
            chained_severity  TEXT,
            confidence        TEXT,
            conditions        TEXT,
            theoretical_impact TEXT,
            human_notes       TEXT,
            status            TEXT DEFAULT 'PENDING_HUMAN_REVIEW',
            created_at        REAL,
            human_approved    INTEGER DEFAULT 0,
            human_reviewer    TEXT,
            reviewed_at       REAL
        );
    """)
    conn.commit()
    conn.close()


def store_primitive(
    repo: str,
    gap_id: str,
    severity: str,
    description: str,
    triggered: bool,
    confidence: str = "UNKNOWN",
    harness_result: Optional[dict] = None,
) -> str:
    """Persist a primitive finding from the harness execution."""
    _init_db()
    finding_id = hashlib.sha256(
        f"{repo}:{gap_id}:{time.time()}".encode()
    ).hexdigest()[:16]
    conn = sqlite3.connect(CHAIN_DB)
    conn.execute(
        """INSERT OR REPLACE INTO primitive_findings
           (id, repo, gap_id, severity, description, triggered, confidence, created_at, harness_out)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            finding_id, repo, gap_id, severity, description,
            1 if triggered else 0, confidence, time.time(),
            json.dumps(harness_result or {}),
        ),
    )
    conn.commit()
    conn.close()
    return finding_id


def analyze_chains(repo: str) -> list[dict]:
    """
    Ask Hermes to propose vulnerability chains from stored primitives.

    Returns THEORETICAL proposals — all tagged PENDING_HUMAN_REVIEW.
    Nothing is executed automatically.
    """
    _init_db()
    conn = sqlite3.connect(CHAIN_DB)
    rows = conn.execute(
        """SELECT id, gap_id, severity, description, triggered, confidence
           FROM primitive_findings WHERE repo = ?
           ORDER BY created_at DESC""",
        (repo,),
    ).fetchall()
    conn.close()

    if len(rows) < 2:
        return []

    primitives_text = "\n".join(
        f"- [{r[0]}] Gap: {r[1]} | Sev: {r[2]} | Triggered: {bool(r[4])} "
        f"| Confidence: {r[5]} | {r[3][:120]}"
        for r in rows
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://rhodawk.ai",
    }
    payload = {
        "model": HERMES_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a senior security researcher conducting responsible vulnerability research. "
                    "Analyse primitive findings and propose THEORETICAL vulnerability chains for human review. "
                    "Be rigorous and conservative — only propose chains that are logically sound based on "
                    "the available evidence. Mark any speculation clearly. Output valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Analyse these primitive findings from {repo} and identify plausible chains.\n\n"
                    f"PRIMITIVES:\n{primitives_text}\n\n"
                    "Output ONLY this JSON:\n"
                    '{"chains": [{'
                    '"primitive_ids": ["id1","id2"],'
                    '"description": "Step-by-step logical chain",'
                    '"chained_severity": "P1|P2|P3",'
                    '"confidence": "HIGH|MEDIUM|LOW",'
                    '"required_conditions": ["condition1"],'
                    '"theoretical_impact": "What an attacker could theoretically achieve",'
                    '"human_verification_needed": "What a human researcher must manually verify before treating this as real"'
                    "}]}"
                ),
            },
        ],
        "max_tokens": 2048,
        "temperature": 0.1,
    }

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]

        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return []

        data = json.loads(match.group())
        chains = data.get("chains", [])

        conn = sqlite3.connect(CHAIN_DB)
        for chain in chains:
            chain_id = hashlib.sha256(
                f"{repo}:{':'.join(chain.get('primitive_ids', []))}:{time.time()}".encode()
            ).hexdigest()[:16]
            chain["id"] = chain_id
            conn.execute(
                """INSERT OR IGNORE INTO chains
                   (id, repo, primitive_ids, description, chained_severity, confidence,
                    conditions, theoretical_impact, status, created_at)
                   VALUES (?,?,?,?,?,?,?,?,'PENDING_HUMAN_REVIEW',?)""",
                (
                    chain_id, repo,
                    json.dumps(chain.get("primitive_ids", [])),
                    chain.get("description", ""),
                    chain.get("chained_severity", "P3"),
                    chain.get("confidence", "LOW"),
                    json.dumps(chain.get("required_conditions", [])),
                    chain.get("theoretical_impact", ""),
                    time.time(),
                ),
            )
        conn.commit()
        conn.close()
        return chains

    except Exception as e:
        return [{"error": str(e)}]


def get_pending_chains(repo: Optional[str] = None) -> list[dict]:
    _init_db()
    conn = sqlite3.connect(CHAIN_DB)
    if repo:
        rows = conn.execute(
            """SELECT id, repo, description, chained_severity, confidence, status, created_at
               FROM chains WHERE repo=? AND status='PENDING_HUMAN_REVIEW'
               ORDER BY created_at DESC""",
            (repo,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id, repo, description, chained_severity, confidence, status, created_at
               FROM chains WHERE status='PENDING_HUMAN_REVIEW'
               ORDER BY created_at DESC""",
        ).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "repo": r[1], "description": r[2],
            "severity": r[3], "confidence": r[4], "status": r[5], "created_at": r[6],
        }
        for r in rows
    ]


def get_all_primitives(repo: Optional[str] = None) -> list[dict]:
    _init_db()
    conn = sqlite3.connect(CHAIN_DB)
    if repo:
        rows = conn.execute(
            "SELECT id, repo, gap_id, severity, description, triggered, confidence, created_at "
            "FROM primitive_findings WHERE repo=? ORDER BY created_at DESC",
            (repo,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, repo, gap_id, severity, description, triggered, confidence, created_at "
            "FROM primitive_findings ORDER BY created_at DESC",
        ).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "repo": r[1], "gap_id": r[2], "severity": r[3],
            "description": r[4], "triggered": bool(r[5]),
            "confidence": r[6], "created_at": r[7],
        }
        for r in rows
    ]


def approve_chain(chain_id: str, reviewer: str) -> bool:
    _init_db()
    conn = sqlite3.connect(CHAIN_DB)
    conn.execute(
        "UPDATE chains SET status='HUMAN_APPROVED', human_approved=1, "
        "human_reviewer=?, reviewed_at=? WHERE id=?",
        (reviewer, time.time(), chain_id),
    )
    conn.commit()
    conn.close()
    return True


def reject_chain(chain_id: str, reviewer: str) -> bool:
    _init_db()
    conn = sqlite3.connect(CHAIN_DB)
    conn.execute(
        "UPDATE chains SET status='HUMAN_REJECTED', human_reviewer=?, reviewed_at=? WHERE id=?",
        (reviewer, time.time(), chain_id),
    )
    conn.commit()
    conn.close()
    return True


# ──────────────────────────────────────────────────────────────────────────
# GAP 13 — VALIDATED MULTI-VULN CHAIN EXPLOITATION
#
# The original `analyze_chains` only proposes theoretical chains tagged
# PENDING_HUMAN_REVIEW. Gap-13 from RHODAWK_ENHANCEMENT_GUIDE.md upgrades
# this with a deterministic execution path:
#
#   1. Operator (or auto-policy) approves a proposed chain.
#   2. `execute_chain(chain_id)` walks the primitives in order, building
#      a ValidationChallenge for each step and routing it through
#      `hermes_orchestrator.validate_exploit_via_tool` — which is itself
#      backed by `exploit_validator.ExploitValidator` running inside the
#      sandbox configured via EXPLOIT_VALIDATOR_SANDBOX.
#   3. A chain is CONFIRMED only if every step returns CONFIRMED. Any
#      REFUTED / PARTIAL / ERROR step short-circuits the chain.
#   4. The full ValidatedChain — verdicts, evidence hashes, wall times —
#      is persisted in `validated_chains` for audit + leaderboard.
#
# ETHICAL CONSTRAINTS preserved:
#   - execute_chain refuses to run unless the chain status is HUMAN_APPROVED
#     OR the caller passes force_auto=True AND env RHODAWK_AUTO_VALIDATE=1.
#   - All validations are non-destructive (validator enforces read_only +
#     no_network_egress + memory cap from env).
# ──────────────────────────────────────────────────────────────────────────

from dataclasses import dataclass, field, asdict


@dataclass
class ValidatedChainStep:
    """A single primitive step inside a validated chain."""

    primitive_id: str
    gap_id: str
    vuln_class: str
    verdict: str                       # CONFIRMED / REFUTED / PARTIAL / ERROR
    evidence: str = ""
    evidence_hash: str = ""
    wall_time_ms: int = 0
    error: Optional[str] = None


@dataclass
class ValidatedChain:
    """End-to-end execution record for a multi-vuln chain.

    A chain is only ``confirmed`` when every step's verdict is CONFIRMED.
    The order of ``steps`` mirrors the primitive ordering in the chain
    proposal and is the order in which the validator was invoked.
    """

    chain_id: str
    repo: str
    status: str                        # CONFIRMED / REFUTED / PARTIAL / ERROR
    steps: list[ValidatedChainStep] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0
    chain_severity: str = "UNKNOWN"
    confirmed: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["steps"] = [asdict(s) for s in self.steps]
        return d


def _ensure_validated_table() -> None:
    """Lazily create the `validated_chains` table — additive migration."""
    os.makedirs(os.path.dirname(CHAIN_DB), exist_ok=True)
    conn = sqlite3.connect(CHAIN_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS validated_chains (
            chain_id       TEXT PRIMARY KEY,
            repo           TEXT NOT NULL,
            status         TEXT NOT NULL,
            confirmed      INTEGER NOT NULL DEFAULT 0,
            chain_severity TEXT,
            steps_json     TEXT NOT NULL,
            notes          TEXT,
            started_at     REAL,
            finished_at    REAL
        )
        """
    )
    conn.commit()
    conn.close()


def _load_chain(chain_id: str) -> Optional[dict]:
    conn = sqlite3.connect(CHAIN_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM chains WHERE id=?", (chain_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def _load_primitive(primitive_id: str) -> Optional[dict]:
    conn = sqlite3.connect(CHAIN_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM primitive_findings WHERE id=?", (primitive_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _primitive_to_challenge(primitive: dict, chain_id: str) -> dict:
    """Coerce a stored primitive into a ValidationChallenge dict.

    The legacy primitive schema does not carry a structured exploit
    payload, so we synthesise a minimal challenge whose ``exploit_code``
    is the primitive's harness output (or description as a last resort).
    The exploit validator's deterministic canary patterns then decide
    whether the primitive is observably triggerable.
    """
    harness_out = primitive.get("harness_out") or ""
    desc        = primitive.get("description") or ""
    gap_id      = primitive.get("gap_id") or ""

    vuln_class_map = {
        "SQLI": "sqli", "RCE": "rce", "SSRF": "ssrf", "XSS": "xss",
        "PATH_TRAVERSAL": "path_traversal", "XXE": "xxe", "SSTI": "ssti",
        "IDOR": "idor",
    }
    vuln_class = "rce"
    for key, val in vuln_class_map.items():
        if key in gap_id.upper() or key in desc.upper():
            vuln_class = val
            break

    return {
        "challenge_id":      f"{chain_id}::{primitive['id']}",
        "vuln_class":        vuln_class,
        "exploit_code":      harness_out or desc,
        "expected_evidence": primitive.get("expected_evidence", ""),
        "timeout_seconds":   int(os.getenv("EXPLOIT_VALIDATOR_TIMEOUT", "120")),
        "max_memory_mb":     int(os.getenv("EXPLOIT_VALIDATOR_MAX_MEMORY_MB", "256")),
        "no_network_egress": bool(int(os.getenv("EXPLOIT_VALIDATOR_NO_NETWORK", "1"))),
    }


def _persist_validated_chain(vc: ValidatedChain) -> None:
    _ensure_validated_table()
    conn = sqlite3.connect(CHAIN_DB)
    conn.execute(
        """
        INSERT OR REPLACE INTO validated_chains
            (chain_id, repo, status, confirmed, chain_severity,
             steps_json, notes, started_at, finished_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            vc.chain_id, vc.repo, vc.status, int(vc.confirmed),
            vc.chain_severity,
            json.dumps([asdict(s) for s in vc.steps]),
            vc.notes, vc.started_at, vc.finished_at,
        ),
    )
    conn.commit()
    conn.close()


def execute_chain(chain_id: str, *, force_auto: bool = False) -> dict:
    """Walk the primitives of a stored chain through the exploit validator.

    Args:
        chain_id:   The chain's primary key in the `chains` table.
        force_auto: When True AND env RHODAWK_AUTO_VALIDATE=1, skip the
                    HUMAN_APPROVED status gate. Default False — chain
                    must already be human-approved.

    Returns:
        ``ValidatedChain.to_dict()`` — the execution record persisted in
        the `validated_chains` table.
    """
    chain_row = _load_chain(chain_id)
    if not chain_row:
        return {"error": f"chain not found: {chain_id}"}

    auto_ok = (
        force_auto and os.getenv("RHODAWK_AUTO_VALIDATE", "0") == "1"
    )
    status = chain_row.get("status", "")
    if status != "HUMAN_APPROVED" and not auto_ok:
        return {
            "error": "chain not approved",
            "chain_id": chain_id,
            "status":   status,
            "hint":     "call approve_chain(chain_id, reviewer) first, "
                        "or pass force_auto=True with RHODAWK_AUTO_VALIDATE=1",
        }

    try:
        primitive_ids = json.loads(chain_row.get("primitive_ids") or "[]")
    except json.JSONDecodeError:
        primitive_ids = []
    if not primitive_ids:
        return {"error": "chain has no primitives", "chain_id": chain_id}

    repo = chain_row.get("repo", "")
    started = time.time()

    # Local import to avoid a circular import at module load time.
    try:
        from hermes_orchestrator import validate_exploit_via_tool
    except Exception as exc:                                # pragma: no cover
        return {"error": f"validator bridge unavailable: {exc}"}

    steps: list[ValidatedChainStep] = []
    overall = "CONFIRMED"

    for pid in primitive_ids:
        primitive = _load_primitive(pid)
        if not primitive:
            steps.append(ValidatedChainStep(
                primitive_id=pid, gap_id="", vuln_class="unknown",
                verdict="ERROR", error="primitive not found",
            ))
            overall = "ERROR"
            break

        challenge_dict = _primitive_to_challenge(primitive, chain_id)
        verdict_dict   = validate_exploit_via_tool(challenge_dict)

        verdict = (verdict_dict.get("verdict") or "ERROR").upper()
        steps.append(ValidatedChainStep(
            primitive_id  = pid,
            gap_id        = primitive.get("gap_id", ""),
            vuln_class    = challenge_dict["vuln_class"],
            verdict       = verdict,
            evidence      = (verdict_dict.get("evidence") or "")[:2048],
            evidence_hash = verdict_dict.get("evidence_hash", ""),
            wall_time_ms  = int(verdict_dict.get("wall_time_ms") or 0),
            error         = verdict_dict.get("error"),
        ))

        if verdict != "CONFIRMED":
            overall = verdict
            break

    finished = time.time()
    severity_map = {"CONFIRMED": "CRITICAL", "PARTIAL": "MEDIUM"}
    chain_sev = severity_map.get(overall, chain_row.get("severity", "UNKNOWN"))

    vc = ValidatedChain(
        chain_id       = chain_id,
        repo           = repo,
        status         = overall,
        steps          = steps,
        started_at     = started,
        finished_at    = finished,
        chain_severity = chain_sev,
        confirmed      = (overall == "CONFIRMED"),
        notes          = (
            f"validated {len(steps)}/{len(primitive_ids)} steps; "
            f"sandbox={os.getenv('EXPLOIT_VALIDATOR_SANDBOX', 'docker')}"
        ),
    )
    _persist_validated_chain(vc)
    return vc.to_dict()


def get_validated_chain(chain_id: str) -> Optional[dict]:
    """Fetch a previously executed validated chain by ID."""
    _ensure_validated_table()
    conn = sqlite3.connect(CHAIN_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM validated_chains WHERE chain_id=?", (chain_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    out = dict(row)
    out["steps"] = json.loads(out.get("steps_json") or "[]")
    out["confirmed"] = bool(out.get("confirmed", 0))
    out.pop("steps_json", None)
    return out
