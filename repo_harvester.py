"""
Rhodawk AI — Autonomous Repository Harvester
============================================
Autonomous target selection engine for the Antagonist operating mode.

Instead of waiting for a user to supply a repo, the harvester continuously
scans public GitHub repositories for:
  - Failing CI checks (check_runs with conclusion=failure)
  - Active maintenance (last commit < 30 days)
  - Good test coverage (test files exist)
  - High star count (community trust signal)

Outputs a ranked feed of (repo, failing_test_hint) tuples for the
enterprise_audit_loop to consume continuously.

Enable continuous harvest mode with: RHODAWK_HARVESTER_ENABLED=true
Configure poll interval:             RHODAWK_HARVESTER_POLL_SECONDS=21600 (6h)
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

# W-010 FIX: rolling 30-day window instead of a hardcoded 2025-01-01 floor.
HARVESTER_PUSHED_WINDOW_DAYS = int(os.getenv("RHODAWK_HARVESTER_PUSHED_WINDOW_DAYS", "30"))

GITHUB_TOKEN       = os.getenv("GITHUB_TOKEN", "")
HARVESTER_ENABLED  = os.getenv("RHODAWK_HARVESTER_ENABLED", "false").lower() == "true"
HARVESTER_POLL_S   = int(os.getenv("RHODAWK_HARVESTER_POLL_SECONDS", "21600"))
HARVESTER_MIN_STARS = int(os.getenv("RHODAWK_HARVESTER_MIN_STARS", "100"))
HARVESTER_MAX_REPOS = int(os.getenv("RHODAWK_HARVESTER_MAX_REPOS", "20"))
HARVESTER_PERSIST  = os.getenv("RHODAWK_HARVESTER_STATE", "/data/harvester_feed.json")

_LANGUAGES = [
    "python", "javascript", "typescript", "go", "java", "ruby", "rust",
]

_harvest_lock = threading.Lock()
_feed: list[dict] = []


@dataclass
class HarvestTarget:
    repo: str
    language: str
    stars: int
    last_commit_days: int
    failing_check: str
    has_tests: bool
    priority_score: float
    discovered_at: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )


def _gh_headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-API-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _search_repos_with_failing_ci(language: str, page: int = 1) -> list[dict]:
    """Search GitHub for repos in a given language with recent activity."""
    # W-010 FIX: dynamic rolling window — was hardcoded "pushed:>2025-01-01".
    pushed_floor = (
        datetime.now(timezone.utc) - timedelta(days=HARVESTER_PUSHED_WINDOW_DAYS)
    ).strftime("%Y-%m-%d")
    q = (
        f"language:{language} "
        f"stars:>={HARVESTER_MIN_STARS} "
        f"pushed:>{pushed_floor} "
        f"fork:false "
        f"is:public"
    )
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            headers=_gh_headers(),
            params={"q": q, "sort": "updated", "per_page": 15, "page": page},
            timeout=15,
        )
        if resp.status_code == 403:
            return []
        resp.raise_for_status()
        return resp.json().get("items", [])
    except Exception:
        return []


def _get_failing_check_runs(repo_full_name: str) -> list[str]:
    """Return names of failing CI check runs for the default branch."""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo_full_name}/commits",
            headers=_gh_headers(),
            params={"per_page": 1},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        commits = resp.json()
        if not commits:
            return []
        sha = commits[0]["sha"]

        resp2 = requests.get(
            f"https://api.github.com/repos/{repo_full_name}/commits/{sha}/check-runs",
            headers=_gh_headers(),
            params={"per_page": 10},
            timeout=10,
        )
        if resp2.status_code != 200:
            return []
        runs = resp2.json().get("check_runs", [])
        return [
            r["name"] for r in runs
            if r.get("conclusion") in ("failure", "timed_out", "cancelled")
        ]
    except Exception:
        return []


def _has_test_files(repo_full_name: str, language: str) -> bool:
    """Quick heuristic: search for test files via GitHub search API."""
    patterns = {
        "python": "test_ filename:*.py",
        "javascript": "filename:*.test.js OR filename:*.spec.js",
        "typescript": "filename:*.test.ts OR filename:*.spec.ts",
        "go": "filename:*_test.go",
        "java": "filename:*Test.java",
        "ruby": "filename:*_spec.rb OR filename:*_test.rb",
        "rust": "#[cfg(test)]",
    }
    try:
        q = f"repo:{repo_full_name} {patterns.get(language, 'test')}"
        resp = requests.get(
            "https://api.github.com/search/code",
            headers=_gh_headers(),
            params={"q": q, "per_page": 1},
            timeout=10,
        )
        if resp.status_code != 200:
            return False
        return resp.json().get("total_count", 0) > 0
    except Exception:
        return False


def _last_commit_days(repo: dict) -> int:
    pushed = repo.get("pushed_at", "")
    if not pushed:
        return 9999
    try:
        ts = time.mktime(time.strptime(pushed[:19], "%Y-%m-%dT%H:%M:%S"))
        return int((time.time() - ts) / 86400)
    except Exception:
        return 9999


def _score_target(stars: int, last_commit_days: int, failing_checks: int) -> float:
    """
    Composite score — higher is better candidate for Rhodawk to fix.
    Stars: log-scaled community trust.
    Recency: prefer repos updated in last 7 days.
    Failing checks: more failures = more opportunity.
    """
    import math
    star_score = min(1.0, math.log10(max(stars, 1)) / 5.0)
    recency_score = max(0.0, 1.0 - (last_commit_days / 30.0))
    failure_score = min(1.0, failing_checks / 3.0)
    return round(star_score * 0.35 + recency_score * 0.40 + failure_score * 0.25, 4)


def run_harvest_cycle() -> list[HarvestTarget]:
    """
    Perform one harvest pass across all tracked languages.
    Returns a ranked list of HarvestTarget objects.
    """
    targets: list[HarvestTarget] = []

    for language in _LANGUAGES:
        repos = _search_repos_with_failing_ci(language, page=1)
        time.sleep(1.0)

        for repo in repos[:8]:
            full_name = repo.get("full_name", "")
            if not full_name:
                continue

            stars = repo.get("stargazers_count", 0)
            last_days = _last_commit_days(repo)

            if last_days > 60:
                continue

            failing_checks = _get_failing_check_runs(full_name)
            time.sleep(0.5)

            if not failing_checks:
                continue

            has_tests = _has_test_files(full_name, language)
            time.sleep(0.5)

            score = _score_target(stars, last_days, len(failing_checks))

            targets.append(HarvestTarget(
                repo=full_name,
                language=language,
                stars=stars,
                last_commit_days=last_days,
                failing_check=failing_checks[0] if failing_checks else "",
                has_tests=has_tests,
                priority_score=score,
            ))

        if len(targets) >= HARVESTER_MAX_REPOS:
            break

    targets.sort(key=lambda t: t.priority_score, reverse=True)
    return targets[:HARVESTER_MAX_REPOS]


def persist_feed(targets: list[HarvestTarget]) -> None:
    os.makedirs(os.path.dirname(HARVESTER_PERSIST), exist_ok=True)
    with open(HARVESTER_PERSIST, "w") as f:
        json.dump([asdict(t) for t in targets], f, indent=2)


def load_feed() -> list[dict]:
    if not os.path.exists(HARVESTER_PERSIST):
        return []
    try:
        with open(HARVESTER_PERSIST) as f:
            return json.load(f)
    except Exception:
        return []


def get_next_target() -> Optional[dict]:
    """
    Pop the highest-priority unprocessed target from the feed.
    Returns None if no targets are available.
    """
    with _harvest_lock:
        global _feed
        if not _feed:
            _feed = load_feed()
        if not _feed:
            return None
        target = _feed.pop(0)
        persist_feed([HarvestTarget(**t) for t in _feed])
        return target


def _harvest_loop(dispatch_fn) -> None:
    """
    Background thread: runs harvest cycles and dispatches audits.
    dispatch_fn(repo_override, language) — passes to enterprise_audit_loop.
    """
    while True:
        try:
            print(f"[Harvester] Starting harvest cycle at {time.strftime('%H:%M:%S')}")
            targets = run_harvest_cycle()
            print(f"[Harvester] Found {len(targets)} candidate repo(s)")

            with _harvest_lock:
                global _feed
                existing_repos = {t.get("repo") for t in _feed}
                new_targets = [t for t in targets if t.repo not in existing_repos]
                _feed.extend([asdict(t) for t in new_targets])
                persist_feed([HarvestTarget(**t) for t in _feed])

            if targets and dispatch_fn:
                top = targets[0]
                print(f"[Harvester] Dispatching audit for {top.repo} (score={top.priority_score})")
                dispatch_fn(repo_override=top.repo)

        except Exception as e:
            print(f"[Harvester] Cycle error: {e}")

        time.sleep(HARVESTER_POLL_S)


def start_harvester(dispatch_fn=None) -> Optional[threading.Thread]:
    """
    Start the harvester in a background daemon thread.
    Returns the thread handle, or None if harvester is disabled.
    """
    if not HARVESTER_ENABLED:
        return None
    if not GITHUB_TOKEN:
        print("[Harvester] GITHUB_TOKEN not set — harvester disabled.")
        return None

    t = threading.Thread(
        target=_harvest_loop,
        args=(dispatch_fn,),
        daemon=True,
        name="rhodawk-harvester",
    )
    t.start()
    print(f"[Harvester] Started — polling every {HARVESTER_POLL_S}s")
    return t


def get_feed_summary() -> str:
    """Human-readable summary of current harvest feed for dashboard display."""
    data = load_feed()
    if not data:
        return (
            "No targets in harvest feed.\n\n"
            "Set RHODAWK_HARVESTER_ENABLED=true to start continuous scanning."
        )
    lines = [f"Harvest feed — {len(data)} target(s) queued:\n"]
    for t in data[:10]:
        lines.append(
            f"  [{t.get('priority_score', 0):.3f}] {t.get('repo', '?')} "
            f"({t.get('language', '?')}, {t.get('stars', 0)} stars, "
            f"last {t.get('last_commit_days', '?')}d, "
            f"failing: {t.get('failing_check', '?')})"
        )
    return "\n".join(lines)
