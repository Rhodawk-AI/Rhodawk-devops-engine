"""
Rhodawk AI — Public Leaderboard & Open Source Health Dashboard
==============================================================
Gradio Space interface showing live stats on repos touched, PRs submitted,
patterns learned, and zero-days discovered.

This is the antagonist version's marketing engine — real numbers, real PRs,
publicly verifiable. No fake metrics.

Runs as a standalone Gradio Space OR embedded in the main app.
"""

import json
import os
import time

import gradio as gr


STATS_PATH        = "/data/public_stats.json"
RED_TEAM_DIR      = "/data/red_team"
AUDIT_LOG_PATH    = "/data/audit_trail.jsonl"


def _load_stats() -> dict:
    if not os.path.exists(STATS_PATH):
        return {}
    try:
        with open(STATS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _compute_live_stats() -> dict:
    stats = {
        "prs_submitted": 0,
        "prs_merged": 0,
        "repos_touched": set(),
        "patterns_learned": 0,
        "zero_days_found": 0,
        "fixes_today": 0,
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    today = time.strftime("%Y-%m-%d")

    if os.path.exists(AUDIT_LOG_PATH):
        try:
            with open(AUDIT_LOG_PATH) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except Exception:
                        continue

                    repo = event.get("repo", "")
                    if repo and repo != "orchestrator":
                        stats["repos_touched"].add(repo)

                    if event.get("event_type") == "PR_SUBMITTED" and event.get("outcome") == "SUCCESS":
                        stats["prs_submitted"] += 1
                        if today in event.get("timestamp_utc", ""):
                            stats["fixes_today"] += 1
        except Exception:
            pass

    try:
        from training_store import get_statistics
        ts = get_statistics()
        stats["patterns_learned"] = ts.get("patterns_learned", 0)
        stats["prs_merged"] = ts.get("human_merged", 0)
    except Exception:
        pass

    if os.path.exists(RED_TEAM_DIR):
        try:
            crashes = [
                f for f in os.listdir(RED_TEAM_DIR)
                if f.startswith("crash_") and f.endswith(".json")
            ]
            stats["zero_days_found"] = len(crashes)
        except Exception:
            pass

    stats["repos_touched"] = len(stats["repos_touched"])
    return stats


def get_leaderboard_markdown() -> str:
    s = _compute_live_stats()
    merge_rate = (
        f"{s['prs_merged'] / s['prs_submitted'] * 100:.1f}%"
        if s["prs_submitted"] > 0 else "—"
    )

    return f"""## Rhodawk AI — Open Source Health Dashboard

```
┌───────────────────────────────────────────────────────────────────┐
│  PRs submitted: {str(s['prs_submitted']).rjust(6)}    │  PRs merged: {str(s['prs_merged']).rjust(5)} ({merge_rate})    │
│  Repos touched: {str(s['repos_touched']).rjust(6)}    │  Patterns learned: {str(s['patterns_learned']).rjust(6)}        │
│  Zero-days found: {str(s['zero_days_found']).rjust(4)}    │  Fixes deployed today: {str(s['fixes_today']).rjust(3)}        │
└───────────────────────────────────────────────────────────────────┘
```

*Last updated: {s['last_updated']}*

---

### How it works

1. Rhodawk scans repositories for failing CI/tests
2. An LLM agent generates a fix, verified by re-running the tests
3. A 3-model adversarial consensus reviews the diff for security issues
4. Passing fixes are submitted as PRs — maintainers decide to merge
5. Every merged PR feeds the self-improving memory engine

---

### Data Flywheel

Every `(failure → fix)` pair that gets merged by a maintainer is stored as
proprietary training signal. The fix quality improves with each run.
"""


def get_top_repos_display() -> str:
    if not os.path.exists(AUDIT_LOG_PATH):
        return "No audit data yet. Run audits to populate."

    repo_pr_counts: dict[str, int] = {}
    try:
        with open(AUDIT_LOG_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if event.get("event_type") == "PR_SUBMITTED" and event.get("outcome") == "SUCCESS":
                    repo = event.get("repo", "")
                    if repo:
                        repo_pr_counts[repo] = repo_pr_counts.get(repo, 0) + 1
    except Exception:
        return "Could not read audit log."

    if not repo_pr_counts:
        return "No PRs submitted yet."

    top = sorted(repo_pr_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = ["### Top Projects Fixed This Session\n"]
    bar_chars = "█" * 10
    max_count = top[0][1] if top else 1
    for repo, count in top:
        bar_len = int(count / max_count * 10)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        lines.append(f"- `{repo}` {bar} {count} fix(es)")
    return "\n".join(lines)


def build_leaderboard_interface() -> gr.Blocks:
    with gr.Blocks(title="Rhodawk AI — Open Source Health", theme=gr.themes.Monochrome()) as demo:
        gr.Markdown("# Rhodawk AI — Autonomous Code Health Engine")

        with gr.Row():
            with gr.Column(scale=2):
                stats_md = gr.Markdown(get_leaderboard_markdown())
            with gr.Column(scale=1):
                top_repos = gr.Markdown(get_top_repos_display())

        with gr.Row():
            refresh_btn = gr.Button("Refresh Stats", variant="primary")

        refresh_btn.click(
            fn=lambda: (get_leaderboard_markdown(), get_top_repos_display()),
            outputs=[stats_md, top_repos],
        )

    return demo


if __name__ == "__main__":
    demo = build_leaderboard_interface()
    demo.launch(server_name="0.0.0.0", server_port=7862)
