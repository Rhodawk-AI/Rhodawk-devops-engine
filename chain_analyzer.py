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
