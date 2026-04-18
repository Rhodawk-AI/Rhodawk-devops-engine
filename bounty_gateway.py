"""
Rhodawk AI — Bug Bounty Gateway (Human-Approval Required)
==========================================================
Manages the responsible disclosure pipeline to:
  - HackerOne (REST API v1)
  - Bugcrowd (JSON API)
  - GitHub Security Advisories (GHSA)
  - Direct maintainer email (coordinated disclosure)

CRITICAL DESIGN PRINCIPLE:
  NOTHING is submitted without explicit human approval.
  All findings sit in PENDING_HUMAN_APPROVAL state until a human clicks
  the "Approve & Submit" button in the Gradio UI. The approval gate is
  enforced at the API call level, not just the UI level.

Disclosure timeline follows Google Project Zero standard (90 days).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

import requests

HACKERONE_API_KEY     = os.getenv("HACKERONE_API_KEY", "")
HACKERONE_USERNAME    = os.getenv("HACKERONE_USERNAME", "")
HACKERONE_PROGRAM     = os.getenv("HACKERONE_PROGRAM", "")
BUGCROWD_API_KEY      = os.getenv("BUGCROWD_API_KEY", "")
BUGCROWD_PROGRAM_URL  = os.getenv("BUGCROWD_PROGRAM_URL", "")
GITHUB_TOKEN          = os.getenv("GITHUB_TOKEN", "")

DISCLOSURE_DB = os.getenv("RHODAWK_DISCLOSURE_DB", "/data/disclosure_pipeline.db")
DISCLOSURE_WINDOW_DAYS = int(os.getenv("RHODAWK_DISCLOSURE_DAYS", "90"))


class DisclosureStatus(str, Enum):
    PENDING_HUMAN_APPROVAL = "PENDING_HUMAN_APPROVAL"
    HUMAN_APPROVED         = "HUMAN_APPROVED"
    HUMAN_REJECTED         = "HUMAN_REJECTED"
    SUBMITTED_HACKERONE    = "SUBMITTED_HACKERONE"
    SUBMITTED_BUGCROWD     = "SUBMITTED_BUGCROWD"
    SUBMITTED_GITHUB_GHSA  = "SUBMITTED_GITHUB_GHSA"
    SUBMITTED_DIRECT       = "SUBMITTED_DIRECT"
    DUPLICATE              = "DUPLICATE"
    NOT_A_BUG              = "NOT_A_BUG"
    FIXED_BY_VENDOR        = "FIXED_BY_VENDOR"


@dataclass
class DisclosureRecord:
    record_id: str
    finding_id: str
    title: str
    description: str
    proof_of_concept: str
    target_repo: str
    cwe_id: str
    severity: str
    estimated_cvss: float
    bounty_tier: str
    exploit_class: str
    status: DisclosureStatus = DisclosureStatus.PENDING_HUMAN_APPROVAL
    platform: str = "none"
    submission_url: str = ""
    bounty_received: float = 0.0
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    approved_at: str = ""
    submitted_at: str = ""
    deadline: str = ""
    human_notes: str = ""
    cve_draft: dict = field(default_factory=dict)


def _init_db():
    os.makedirs(os.path.dirname(DISCLOSURE_DB), exist_ok=True)
    conn = sqlite3.connect(DISCLOSURE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS disclosure_records (
            record_id TEXT PRIMARY KEY,
            finding_id TEXT,
            title TEXT,
            description TEXT,
            proof_of_concept TEXT,
            target_repo TEXT,
            cwe_id TEXT,
            severity TEXT,
            estimated_cvss REAL,
            bounty_tier TEXT,
            exploit_class TEXT,
            status TEXT,
            platform TEXT,
            submission_url TEXT,
            bounty_received REAL,
            created_at TEXT,
            approved_at TEXT,
            submitted_at TEXT,
            deadline TEXT,
            human_notes TEXT,
            cve_draft TEXT
        )
    """)
    conn.commit()
    conn.close()


_init_db()


def add_to_pipeline(
    finding_id: str,
    title: str,
    description: str,
    proof_of_concept: str,
    target_repo: str,
    cwe_id: str,
    severity: str,
    estimated_cvss: float,
    bounty_tier: str,
    exploit_class: str,
    cve_draft: dict = None,
) -> DisclosureRecord:
    """Add a new finding to the disclosure pipeline. Status = PENDING_HUMAN_APPROVAL."""
    record_id = hashlib.sha256(f"{finding_id}{time.time()}".encode()).hexdigest()[:16]
    deadline = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ",
        time.gmtime(time.time() + DISCLOSURE_WINDOW_DAYS * 86400)
    )
    record = DisclosureRecord(
        record_id=record_id,
        finding_id=finding_id,
        title=title,
        description=description,
        proof_of_concept=proof_of_concept,
        target_repo=target_repo,
        cwe_id=cwe_id,
        severity=severity,
        estimated_cvss=estimated_cvss,
        bounty_tier=bounty_tier,
        exploit_class=exploit_class,
        deadline=deadline,
        cve_draft=cve_draft or {},
    )
    _save_record(record)
    print(f"[DISCLOSURE] Added to pipeline: {record_id} — Status: PENDING_HUMAN_APPROVAL")
    return record


def _save_record(record: DisclosureRecord):
    conn = sqlite3.connect(DISCLOSURE_DB)
    conn.execute("""
        INSERT OR REPLACE INTO disclosure_records VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
    """, (
        record.record_id, record.finding_id, record.title, record.description,
        record.proof_of_concept, record.target_repo, record.cwe_id, record.severity,
        record.estimated_cvss, record.bounty_tier, record.exploit_class,
        record.status.value, record.platform, record.submission_url,
        record.bounty_received, record.created_at, record.approved_at,
        record.submitted_at, record.deadline, record.human_notes,
        json.dumps(record.cve_draft),
    ))
    conn.commit()
    conn.close()


def get_pipeline(status_filter: str = None) -> list[dict]:
    """Get all records in the pipeline, optionally filtered by status."""
    conn = sqlite3.connect(DISCLOSURE_DB)
    if status_filter:
        rows = conn.execute(
            "SELECT * FROM disclosure_records WHERE status=? ORDER BY created_at DESC",
            (status_filter,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM disclosure_records ORDER BY created_at DESC"
        ).fetchall()
    conn.close()

    columns = [
        "record_id", "finding_id", "title", "description", "proof_of_concept",
        "target_repo", "cwe_id", "severity", "estimated_cvss", "bounty_tier",
        "exploit_class", "status", "platform", "submission_url", "bounty_received",
        "created_at", "approved_at", "submitted_at", "deadline", "human_notes", "cve_draft",
    ]
    return [dict(zip(columns, row)) for row in rows]


def human_approve(record_id: str, notes: str = "") -> dict:
    """
    Human approval gate — must be called before any submission attempt.
    Updates status to HUMAN_APPROVED. Still does not submit.
    """
    conn = sqlite3.connect(DISCLOSURE_DB)
    conn.execute(
        "UPDATE disclosure_records SET status=?, approved_at=?, human_notes=? WHERE record_id=?",
        (DisclosureStatus.HUMAN_APPROVED.value,
         time.strftime("%Y-%m-%dT%H:%M:%SZ"), notes, record_id)
    )
    conn.commit()
    conn.close()
    print(f"[DISCLOSURE] HUMAN APPROVED: {record_id}")
    return {"status": "approved", "record_id": record_id, "notes": notes}


def human_reject(record_id: str, notes: str = "") -> dict:
    """Human rejection — finding is closed without disclosure."""
    conn = sqlite3.connect(DISCLOSURE_DB)
    conn.execute(
        "UPDATE disclosure_records SET status=?, human_notes=? WHERE record_id=?",
        (DisclosureStatus.HUMAN_REJECTED.value, notes, record_id)
    )
    conn.commit()
    conn.close()
    print(f"[DISCLOSURE] HUMAN REJECTED: {record_id} — {notes}")
    return {"status": "rejected", "record_id": record_id}


def submit_to_hackerone(record_id: str) -> dict:
    """
    Submit an APPROVED finding to HackerOne.
    REQUIRES human_approve() to have been called first.
    """
    records = get_pipeline()
    record = next((r for r in records if r["record_id"] == record_id), None)
    if not record:
        return {"error": f"Record {record_id} not found"}

    if record["status"] != DisclosureStatus.HUMAN_APPROVED.value:
        return {
            "error": f"BLOCKED: Record status is '{record['status']}'. "
                     f"Human approval required before submission. "
                     f"Call human_approve('{record_id}') first."
        }

    if not HACKERONE_API_KEY or not HACKERONE_USERNAME or not HACKERONE_PROGRAM:
        return {
            "error": "HackerOne credentials not configured. "
                     "Set HACKERONE_API_KEY, HACKERONE_USERNAME, HACKERONE_PROGRAM env vars."
        }

    payload = {
        "data": {
            "type": "report",
            "attributes": {
                "title": record["title"],
                "vulnerability_information": (
                    f"## Description\n{record['description']}\n\n"
                    f"## Proof of Concept\n```\n{record['proof_of_concept']}\n```\n\n"
                    f"## CWE\n{record['cwe_id']}\n\n"
                    f"## Severity\n{record['severity']} (CVSS: {record['estimated_cvss']})\n\n"
                    f"*Generated by Rhodawk AI Security Research Engine — "
                    f"human-verified before submission*"
                ),
                "impact": (
                    f"Estimated severity: {record['severity']}\n"
                    f"Exploit class: {record['exploit_class']}\n"
                    f"Bounty tier estimate: {record['bounty_tier']}"
                ),
                "severity_rating": {
                    "CRITICAL": "critical", "HIGH": "high",
                    "MEDIUM": "medium", "LOW": "low",
                }.get(record["severity"], "medium"),
            },
            "relationships": {
                "program": {"data": {"type": "program", "attributes": {"handle": HACKERONE_PROGRAM}}}
            }
        }
    }

    try:
        resp = requests.post(
            "https://api.hackerone.com/v1/hackers/reports",
            auth=(HACKERONE_USERNAME, HACKERONE_API_KEY),
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            report_url = f"https://hackerone.com/reports/{data['data']['id']}"
            conn = sqlite3.connect(DISCLOSURE_DB)
            conn.execute(
                "UPDATE disclosure_records SET status=?, platform=?, submission_url=?, submitted_at=? WHERE record_id=?",
                (DisclosureStatus.SUBMITTED_HACKERONE.value, "hackerone", report_url,
                 time.strftime("%Y-%m-%dT%H:%M:%SZ"), record_id)
            )
            conn.commit()
            conn.close()
            return {"success": True, "platform": "hackerone", "url": report_url}
        else:
            return {"error": f"HackerOne API error {resp.status_code}: {resp.text[:500]}"}
    except Exception as e:
        return {"error": str(e)}


def submit_github_advisory(record_id: str, repo_owner: str, repo_name: str) -> dict:
    """
    Submit an APPROVED finding as a GitHub Security Advisory (GHSA).
    Requires GitHub token with security_events scope.
    """
    records = get_pipeline()
    record = next((r for r in records if r["record_id"] == record_id), None)
    if not record:
        return {"error": f"Record {record_id} not found"}

    if record["status"] != DisclosureStatus.HUMAN_APPROVED.value:
        return {"error": f"BLOCKED: Human approval required. Status: {record['status']}"}

    if not GITHUB_TOKEN:
        return {"error": "GITHUB_TOKEN not set"}

    severity_map = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}

    payload = {
        "summary": record["title"],
        "description": (
            f"{record['description']}\n\n"
            f"**Proof of Concept:**\n```\n{record['proof_of_concept']}\n```\n\n"
            f"*Discovered by Rhodawk AI Security Research Engine — human-verified*"
        ),
        "severity": severity_map.get(record["severity"], "medium"),
        "cwe_ids": [record["cwe_id"]] if record["cwe_id"] != "CWE-UNKNOWN" else [],
        "vulnerabilities": [
            {"package": {"ecosystem": "other", "name": repo_name},
             "vulnerable_version_range": "*"}
        ],
    }

    try:
        resp = requests.post(
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/security-advisories",
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-API-Version": "2022-11-28",
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            advisory_url = data.get("html_url", "")
            conn = sqlite3.connect(DISCLOSURE_DB)
            conn.execute(
                "UPDATE disclosure_records SET status=?, platform=?, submission_url=?, submitted_at=? WHERE record_id=?",
                (DisclosureStatus.SUBMITTED_GITHUB_GHSA.value, "github_ghsa", advisory_url,
                 time.strftime("%Y-%m-%dT%H:%M:%SZ"), record_id)
            )
            conn.commit()
            conn.close()
            return {"success": True, "platform": "github_ghsa", "url": advisory_url}
        else:
            return {"error": f"GitHub API error {resp.status_code}: {resp.text[:500]}"}
    except Exception as e:
        return {"error": str(e)}


def get_pipeline_summary() -> str:
    """Human-readable pipeline summary for the Gradio dashboard."""
    records = get_pipeline()
    if not records:
        return "No findings in disclosure pipeline yet."

    pending = [r for r in records if r["status"] == "PENDING_HUMAN_APPROVAL"]
    approved = [r for r in records if r["status"] == "HUMAN_APPROVED"]
    submitted = [r for r in records if "SUBMITTED" in r["status"]]
    rejected = [r for r in records if r["status"] == "HUMAN_REJECTED"]

    lines = [
        f"Disclosure Pipeline — {len(records)} total finding(s)\n",
        f"  ⏳ Pending human approval : {len(pending)}",
        f"  ✅ Human approved         : {len(approved)}",
        f"  📤 Submitted              : {len(submitted)}",
        f"  ❌ Rejected               : {len(rejected)}",
        "",
    ]
    for r in sorted(records, key=lambda x: x["estimated_cvss"], reverse=True)[:5]:
        days_left = ""
        if r.get("deadline"):
            try:
                deadline_ts = time.mktime(time.strptime(r["deadline"][:19], "%Y-%m-%dT%H:%M:%S"))
                days = int((deadline_ts - time.time()) / 86400)
                days_left = f" ({days}d left)"
            except Exception:
                pass
        lines.append(
            f"  [{r['bounty_tier']}] {r['title'][:60]} | "
            f"CVSS:{r['estimated_cvss']} | {r['status']}{days_left}"
        )
    return "\n".join(lines)
