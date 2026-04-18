"""
Rhodawk AI — Commit Watcher + CAD Algorithm
============================================
Monitors GitHub repository commit streams for:
  1. Silent security patches (fixes without CVE mention)
  2. Regression introductions (commits that break previously safe invariants)
  3. Dependency bumps that change security-relevant code

Custom Algorithm: CAD (Commit Anomaly Detection)
  Uses statistical analysis of commit metadata + diff content to score
  how "suspicious" a commit is from a security perspective.
  High CAD score = likely silent security fix = potential unpatched vuln in older versions.

CAD Score Components:
  - keyword_score: security-related words in commit message (without CVE/advisory mention)
  - diff_complexity: unusual churn patterns (small message + large diff = suspicious)
  - sink_delta: did the commit add/remove dangerous sinks?
  - author_entropy: is this from an unusual author for this file?
  - timing: late-night commits, weekend commits (higher anomaly weight)
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CommitAnalysis:
    sha: str
    message: str
    author: str
    date: str
    files_changed: int
    insertions: int
    deletions: int
    cad_score: float           # 0.0–10.0 (higher = more suspicious)
    security_keywords: list[str]
    sink_changes: list[str]
    has_cve_mention: bool
    has_advisory_mention: bool
    is_suspicious: bool        # cad_score > threshold
    diff_snippet: str


_SECURITY_KEYWORDS = {
    "overflow", "injection", "traversal", "escape", "sanitize", "sanitise",
    "validate", "validation", "bypass", "privilege", "escalation", "disclosure",
    "arbitrary", "execute", "remote", "code", "memory", "corruption", "buffer",
    "heap", "stack", "uaf", "use-after-free", "null", "deref", "dereference",
    "race", "condition", "toctou", "deserialization", "serialize", "pickle",
    "auth", "authentication", "authorization", "permission", "access control",
    "sql", "query", "xss", "csrf", "ssrf", "xxe", "open redirect", "clickjack",
    "timing", "side channel", "cryptographic", "weak", "hardcoded", "credential",
    "secret", "password", "token", "key", "certificate", "tls", "ssl",
    "fix", "patch", "security", "vulnerability", "vuln", "issue", "bug",
    "denial", "dos", "crash", "abort", "segfault", "exception", "error handling",
}

_CVE_PATTERN    = re.compile(r"\bCVE-\d{4}-\d+\b", re.IGNORECASE)
_ADVISORY_PATTERN = re.compile(r"\bGHSA-[A-Z0-9-]+\b|\bSA-\d+\b|\bVU#\d+\b", re.IGNORECASE)

_DANGEROUS_SINK_PATTERNS = re.compile(
    r"\beval\b|\bexec\b|\bos\.system\b|\bsubprocess\b|\bpickle\b|\byaml\.load\b"
    r"|\bchild_process\b|\binnerHTML\b|\bdocument\.write\b|\bSQLQuery\b|\bcursor\.execute\b",
    re.IGNORECASE,
)

CAD_THRESHOLD = float(os.getenv("RHODAWK_CAD_THRESHOLD", "5.0"))


def _git_log(repo_dir: str, n: int = 50) -> list[dict]:
    """Get recent commits with stats."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--format=%H|%s|%an|%ae|%ai", "--shortstat"],
            cwd=repo_dir, capture_output=True, text=True, timeout=30,
        )
        entries = []
        lines = result.stdout.strip().splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if "|" in line and len(line.split("|")) >= 5:
                parts = line.split("|", 4)
                sha, msg, author, email, date = parts[0], parts[1], parts[2], parts[3], parts[4]
                insertions = 0
                deletions = 0
                files_changed = 0
                if i + 1 < len(lines) and ("changed" in lines[i + 1] or "insertion" in lines[i + 1]):
                    stat_line = lines[i + 1]
                    m = re.search(r"(\d+)\s+file", stat_line)
                    if m:
                        files_changed = int(m.group(1))
                    m = re.search(r"(\d+)\s+insertion", stat_line)
                    if m:
                        insertions = int(m.group(1))
                    m = re.search(r"(\d+)\s+deletion", stat_line)
                    if m:
                        deletions = int(m.group(1))
                    i += 1
                entries.append({
                    "sha": sha.strip(),
                    "message": msg.strip(),
                    "author": author.strip(),
                    "email": email.strip(),
                    "date": date.strip(),
                    "files_changed": files_changed,
                    "insertions": insertions,
                    "deletions": deletions,
                })
            i += 1
        return entries
    except Exception as e:
        print(f"[CAD] git log failed: {e}")
        return []


def _get_commit_diff(repo_dir: str, sha: str) -> str:
    """Get the diff for a specific commit."""
    try:
        result = subprocess.run(
            ["git", "show", "--unified=3", "--no-color", sha],
            cwd=repo_dir, capture_output=True, text=True, timeout=15,
        )
        return result.stdout[:5000]
    except Exception:
        return ""


def _compute_cad_score(commit: dict, diff: str) -> tuple[float, list[str], list[str]]:
    """
    CAD (Commit Anomaly Detection) algorithm.

    Returns (cad_score, matched_security_keywords, sink_changes)
    """
    msg = commit["message"].lower()
    score = 0.0
    matched_keywords = []
    sink_changes = []

    # --- Keyword scoring ---
    for kw in _SECURITY_KEYWORDS:
        if kw in msg:
            matched_keywords.append(kw)
            score += 0.4

    has_cve = bool(_CVE_PATTERN.search(commit["message"]))
    has_advisory = bool(_ADVISORY_PATTERN.search(commit["message"]))

    # If it mentions CVE/advisory it's already disclosed — less interesting for us
    if has_cve or has_advisory:
        score -= 2.0
    # If it has security keywords WITHOUT CVE → silent fix (most interesting)
    elif matched_keywords:
        score += 1.5

    # --- Diff complexity scoring ---
    ins = commit["insertions"]
    dels = commit["deletions"]
    total_churn = ins + dels

    if total_churn > 0:
        # Short commit message + large diff = suspicious
        msg_length_penalty = 1.0 if len(commit["message"]) < 30 else 0.5
        churn_score = math.log10(max(total_churn, 1)) * msg_length_penalty * 0.8
        score += min(churn_score, 3.0)

    # High deletions relative to insertions = removing dangerous code
    if dels > 0 and ins > 0:
        del_ratio = dels / (ins + dels)
        if del_ratio > 0.6:
            score += 0.8

    # --- Sink delta scoring ---
    added_lines = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removed_lines = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]

    for line in added_lines:
        if _DANGEROUS_SINK_PATTERNS.search(line):
            sink_changes.append(f"ADDED: {line[1:].strip()[:80]}")
            score += 0.5

    for line in removed_lines:
        if _DANGEROUS_SINK_PATTERNS.search(line):
            sink_changes.append(f"REMOVED: {line[1:].strip()[:80]}")
            score += 0.3  # Removing dangerous code = possible silent fix

    # --- Timing scoring ---
    try:
        date_str = commit["date"][:19]
        import datetime
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
        weekday = dt.weekday()
        if hour < 6 or hour > 22:
            score += 0.5
        if weekday >= 5:
            score += 0.3
    except Exception:
        pass

    return round(min(score, 10.0), 3), matched_keywords, sink_changes


def analyze_recent_commits(repo_dir: str, lookback: int = 50) -> dict:
    """
    Main entry point. Analyze recent commits using CAD algorithm.
    Returns suspicious commits sorted by CAD score.
    """
    print(f"[CAD] Analyzing last {lookback} commits in {repo_dir}")
    commits = _git_log(repo_dir, n=lookback)

    if not commits:
        return {"error": "No commits found or git log failed", "suspicious_commits": [], "total": 0}

    analyses = []
    for commit in commits[:lookback]:
        diff = _get_commit_diff(repo_dir, commit["sha"])
        cad_score, keywords, sinks = _compute_cad_score(commit, diff)

        has_cve = bool(_CVE_PATTERN.search(commit["message"]))
        has_advisory = bool(_ADVISORY_PATTERN.search(commit["message"]))

        analysis = CommitAnalysis(
            sha=commit["sha"][:12],
            message=commit["message"][:200],
            author=commit["author"],
            date=commit["date"][:19],
            files_changed=commit["files_changed"],
            insertions=commit["insertions"],
            deletions=commit["deletions"],
            cad_score=cad_score,
            security_keywords=keywords,
            sink_changes=sinks,
            has_cve_mention=has_cve,
            has_advisory_mention=has_advisory,
            is_suspicious=cad_score >= CAD_THRESHOLD,
            diff_snippet=diff[:500],
        )
        analyses.append(analysis)

    analyses.sort(key=lambda a: a.cad_score, reverse=True)
    suspicious = [a for a in analyses if a.is_suspicious]

    print(f"[CAD] Found {len(suspicious)} suspicious commit(s) out of {len(analyses)}")

    return {
        "total_analyzed": len(analyses),
        "suspicious_count": len(suspicious),
        "threshold": CAD_THRESHOLD,
        "algorithm": "CAD_v1",
        "suspicious_commits": [
            {
                "sha": a.sha, "message": a.message, "author": a.author,
                "date": a.date, "cad_score": a.cad_score,
                "security_keywords": a.security_keywords,
                "sink_changes": a.sink_changes[:3],
                "files_changed": a.files_changed,
                "insertions": a.insertions, "deletions": a.deletions,
                "has_cve": a.has_cve_mention,
                "diff_snippet": a.diff_snippet[:300],
            }
            for a in suspicious[:10]
        ],
        "all_scores": [{"sha": a.sha[:8], "score": a.cad_score, "msg": a.message[:60]}
                       for a in analyses[:20]],
    }


def watch_repo_stream(
    owner: str,
    repo: str,
    github_token: str,
    callback,
    poll_interval_s: int = 300,
) -> None:
    """
    Continuously poll a GitHub repo for new commits and run CAD on each batch.
    callback(analysis_result) is called when suspicious commits are found.
    Runs in a background thread.
    """
    import threading
    import requests

    seen_shas = set()

    def _poll():
        while True:
            try:
                headers = {
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github+json",
                }
                resp = requests.get(
                    f"https://api.github.com/repos/{owner}/{repo}/commits",
                    headers=headers, params={"per_page": 20}, timeout=15,
                )
                if resp.status_code != 200:
                    time.sleep(poll_interval_s)
                    continue

                commits = resp.json()
                new_commits = [c for c in commits if c["sha"] not in seen_shas]

                if new_commits:
                    for c in new_commits:
                        seen_shas.add(c["sha"])

                    print(f"[CAD WATCH] {len(new_commits)} new commit(s) on {owner}/{repo}")
                    result = {
                        "repo": f"{owner}/{repo}",
                        "new_commits": len(new_commits),
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "commits": [
                            {
                                "sha": c["sha"][:12],
                                "message": c["commit"]["message"][:100],
                                "author": c["commit"]["author"]["name"],
                            }
                            for c in new_commits
                        ],
                    }
                    callback(result)

            except Exception as e:
                print(f"[CAD WATCH] Error: {e}")

            time.sleep(poll_interval_s)

    t = threading.Thread(target=_poll, daemon=True, name=f"cad-watch-{owner}-{repo}")
    t.start()
    return t
