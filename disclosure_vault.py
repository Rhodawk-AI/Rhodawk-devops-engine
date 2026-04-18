"""
Rhodawk AI — Responsible Disclosure Vault
==========================================
Manages the complete responsible disclosure lifecycle with a mandatory
human approval gate at every stage.

DISCLOSURE POLICY (non-negotiable):
  1. ALL findings start as DRAFT — nothing is shared externally
  2. Human operator must read the full dossier and click Approve
  3. After approval, the system generates a disclosure message —
     the operator sends it via the maintainer's own security channel
  4. Standard 90-day responsible disclosure timeline is tracked
  5. Bug bounty submissions are prepared for human submission —
     never automated
  6. No GitHub API writes in AVR mode
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

VAULT_DB  = os.getenv("RHODAWK_VAULT_DB",  "/data/disclosure_vault.sqlite")
VAULT_DIR = os.getenv("RHODAWK_VAULT_DIR", "/data/vault")
DISCLOSURE_DAYS = int(os.getenv("RHODAWK_DISCLOSURE_DAYS", "90"))


def _init_db() -> None:
    os.makedirs(os.path.dirname(VAULT_DB), exist_ok=True)
    os.makedirs(VAULT_DIR, exist_ok=True)
    conn = sqlite3.connect(VAULT_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS disclosures (
            id                TEXT PRIMARY KEY,
            repo              TEXT NOT NULL,
            severity          TEXT NOT NULL,
            title             TEXT NOT NULL,
            status            TEXT DEFAULT 'DRAFT',
            created_at        REAL,
            human_approved    INTEGER DEFAULT 0,
            approved_by       TEXT,
            approved_at       REAL,
            disclosed_at      REAL,
            deadline_at       REAL,
            dossier_path      TEXT,
            bug_bounty_program TEXT,
            maintainer_contact TEXT
        );
    """)
    conn.commit()
    conn.close()


def compile_dossier(
    repo: str,
    semantic_graph: dict,
    assumption_gap: dict,
    harness_result: dict,
    chain_analysis: Optional[list] = None,
    bug_bounty_program: str = "",
    maintainer_contact: str = "",
) -> str:
    """
    Compile a structured responsible disclosure dossier.
    Stored locally — NOT sent anywhere until a human operator approves.
    Returns the disclosure ID.
    """
    _init_db()

    disclosure_id = hashlib.sha256(
        f"{repo}:{assumption_gap.get('id','')}:{time.time()}".encode()
    ).hexdigest()[:16]

    deadline_ts = time.time() + (DISCLOSURE_DAYS * 86400)
    severity    = assumption_gap.get("severity_hypothesis", "P3")
    gap_desc    = assumption_gap.get("description", "N/A")[:120]

    triggered_str = str(harness_result.get("triggered", "Not tested"))
    poc_output    = harness_result.get("stdout", "N/A")[:1500]
    chain_block   = (
        json.dumps(chain_analysis, indent=2)
        if chain_analysis
        else "No chains identified."
    )

    trust_states  = json.dumps(semantic_graph.get("trust_states",  []), indent=2)[:2000]
    transitions   = json.dumps(semantic_graph.get("transitions",   []), indent=2)[:1000]

    dossier = f"""# Responsible Disclosure Report — {disclosure_id}

> **STATUS: DRAFT — PENDING HUMAN OPERATOR REVIEW**
> This report has NOT been sent to any maintainer or bug bounty programme.
> No live system has been tested or attacked.

---

| Field | Value |
|---|---|
| **Disclosure ID** | `{disclosure_id}` |
| **Repository** | `{repo}` |
| **Severity Hypothesis** | **{severity}** |
| **Disclosure Deadline** | {time.strftime('%Y-%m-%d', time.localtime(deadline_ts))} ({DISCLOSURE_DAYS}-day standard) |
| **Bug Bounty Programme** | {bug_bounty_program or "Not specified"} |
| **Maintainer Contact** | {maintainer_contact or "See SECURITY.md"} |
| **Created** | {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} |

---

## ⚠️ Operator Action Required

Before this disclosure proceeds, you must:

- [ ] Read and understand the full dossier
- [ ] Independently verify the assumption gap description is accurate
- [ ] Confirm the PoC result matches what is claimed
- [ ] Verify the target repo has a responsible disclosure policy or bug bounty programme
- [ ] Click **Approve** in the Rhodawk Security Research dashboard

---

## 1. Executive Summary

**Finding:** {assumption_gap.get('description', 'N/A')}

**File:** `{assumption_gap.get('file', 'N/A')}`  
**Location:** `{assumption_gap.get('line_hint', 'N/A')}`  
**Confidence:** {assumption_gap.get('confidence', 'UNKNOWN')}

---

## 2. State Machine Analysis

**Untrusted Input Path:**
{assumption_gap.get('untrusted_input', 'N/A')}

**Bypassed or Insufficient Check:**
{assumption_gap.get('bypassed_check', 'N/A')}

**Theoretical Impact:**
{assumption_gap.get('potential_impact', 'N/A')}

### Trust States Identified

```json
{trust_states}
```

### State Transitions

```json
{transitions}
```

---

## 3. Proof of Concept (Local Sandbox Only)

> All PoC testing was performed against a locally cloned copy of the repository.
> No live/production system was accessed.

**Gap Triggered in Sandbox:** {triggered_str}  
**Exit Code:** {harness_result.get('exit_code', 'N/A')}  
**Timed Out:** {harness_result.get('timed_out', False)}  

**Sandbox Output:**
```
{poc_output}
```

---

## 4. Vulnerability Chain Analysis (Theoretical)

{chain_block}

> All chain proposals above are theoretical and require independent human verification.

---

## 5. Responsible Disclosure Next Steps

1. **Operator** reviews and verifies this dossier
2. **Operator** approves disclosure via Rhodawk dashboard
3. **Operator** contacts maintainer via their `SECURITY.md` / `security@` policy
4. Submit to bug bounty programme if applicable: `{bug_bounty_program or 'N/A'}`
5. Allow **{DISCLOSURE_DAYS} days** for maintainer to produce a fix
6. Coordinate public disclosure date with maintainer

---

*Generated by Rhodawk AI Ethical Security Research Platform*  
*All findings require human verification and explicit approval before disclosure*  
*No automated exploitation of live systems is performed*
"""

    dossier_path = os.path.join(VAULT_DIR, f"{disclosure_id}.md")
    Path(dossier_path).write_text(dossier, encoding="utf-8")

    conn = sqlite3.connect(VAULT_DB)
    conn.execute(
        """INSERT INTO disclosures
           (id, repo, severity, title, status, created_at, deadline_at,
            dossier_path, bug_bounty_program, maintainer_contact)
           VALUES (?,?,?,?,  'DRAFT',?,?,  ?,?,?)""",
        (
            disclosure_id, repo, severity,
            f"{severity} — {gap_desc}",
            time.time(), deadline_ts,
            dossier_path, bug_bounty_program, maintainer_contact,
        ),
    )
    conn.commit()
    conn.close()

    return disclosure_id


def get_pending_disclosures() -> list[dict]:
    _init_db()
    conn = sqlite3.connect(VAULT_DB)
    rows = conn.execute(
        """SELECT id, repo, severity, title, status, created_at, deadline_at, bug_bounty_program
           FROM disclosures WHERE status IN ('DRAFT','HUMAN_APPROVED')
           ORDER BY created_at DESC"""
    ).fetchall()
    conn.close()
    now = time.time()
    return [
        {
            "id": r[0], "repo": r[1], "severity": r[2], "title": r[3],
            "status": r[4], "created_at": r[5],
            "days_remaining": max(0, int((r[6] - now) / 86400)) if r[6] else DISCLOSURE_DAYS,
            "bug_bounty_program": r[7] or "N/A",
        }
        for r in rows
    ]


def get_all_disclosures() -> list[dict]:
    _init_db()
    conn = sqlite3.connect(VAULT_DB)
    rows = conn.execute(
        "SELECT id, repo, severity, title, status, created_at, deadline_at, bug_bounty_program "
        "FROM disclosures ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    now = time.time()
    return [
        {
            "id": r[0], "repo": r[1], "severity": r[2], "title": r[3],
            "status": r[4], "created_at": r[5],
            "days_remaining": max(0, int((r[6] - now) / 86400)) if r[6] else DISCLOSURE_DAYS,
            "bug_bounty_program": r[7] or "N/A",
        }
        for r in rows
    ]


def read_dossier(disclosure_id: str) -> str:
    _init_db()
    conn = sqlite3.connect(VAULT_DB)
    row = conn.execute(
        "SELECT dossier_path FROM disclosures WHERE id=?", (disclosure_id,)
    ).fetchone()
    conn.close()
    if not row or not row[0]:
        return f"Dossier not found for ID: {disclosure_id}"
    try:
        return Path(row[0]).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading dossier: {e}"


def approve_disclosure(disclosure_id: str, approved_by: str) -> bool:
    """Human operator explicitly approves a finding for disclosure."""
    _init_db()
    conn = sqlite3.connect(VAULT_DB)
    conn.execute(
        "UPDATE disclosures SET status='HUMAN_APPROVED', human_approved=1, "
        "approved_by=?, approved_at=? WHERE id=?",
        (approved_by, time.time(), disclosure_id),
    )
    conn.commit()
    conn.close()
    return True


def reject_disclosure(disclosure_id: str, reason: str = "") -> bool:
    """Human operator rejects / archives a finding."""
    _init_db()
    conn = sqlite3.connect(VAULT_DB)
    conn.execute(
        "UPDATE disclosures SET status='REJECTED' WHERE id=?",
        (disclosure_id,),
    )
    conn.commit()
    conn.close()
    return True


def prepare_disclosure_message(disclosure_id: str) -> str:
    """
    After human approval, generate the message for the operator to send
    to the maintainer via THEIR preferred channel (SECURITY.md / email / HackerOne).

    The operator sends this manually — it is never automated.
    """
    _init_db()
    conn = sqlite3.connect(VAULT_DB)
    row = conn.execute(
        "SELECT repo, severity, title, bug_bounty_program, human_approved, approved_by "
        "FROM disclosures WHERE id=?",
        (disclosure_id,),
    ).fetchone()
    conn.close()

    if not row:
        return "Disclosure not found."
    if not row[4]:
        return "ERROR: Human approval is required before generating a disclosure message."

    repo, severity, title, bounty, _, approved_by = row

    msg = f"""Subject: Responsible Disclosure — {severity} Finding in {repo}

Hello {repo.split('/')[0]} security team,

I am reaching out as part of responsible security research conducted through the Rhodawk AI ethical research platform.

We have identified a potential {severity}-severity security finding in `{repo}`.

**Finding:** {title}

**Disclosure ID:** `{disclosure_id}`
**Disclosure Deadline:** {DISCLOSURE_DAYS} days from today (industry standard)
**Bug Bounty Programme:** {bounty or "N/A"}

We have prepared a full technical dossier including:
- State machine analysis
- Proof-of-concept (local sandbox only — no live systems tested)
- Theoretical vulnerability chain analysis

We would like to coordinate disclosure privately before any public disclosure.
Please let us know your preferred communication channel and we will share the full dossier.

This report was reviewed and approved for disclosure by a human researcher before being sent.

Respectfully,
Rhodawk AI Security Research Team
"""

    conn = sqlite3.connect(VAULT_DB)
    conn.execute(
        "UPDATE disclosures SET status='DISCLOSED', disclosed_at=? WHERE id=?",
        (time.time(), disclosure_id),
    )
    conn.commit()
    conn.close()

    return msg
