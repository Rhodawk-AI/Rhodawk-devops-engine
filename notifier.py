"""
Rhodawk AI — Multi-Channel Notification Engine
================================================
Fire-and-forget notifications across Telegram (and extensible to Slack/PagerDuty).
All dispatches use tenacity retry logic and never block the audit loop.

MINOR BUG FIX: Telegram/Slack URLs are no longer captured at module load time.
They are resolved dynamically at dispatch time, so rotating credentials at runtime
(without a process restart) takes effect immediately.
"""

import os
import threading
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


def _get_telegram_creds() -> tuple[str, str]:
    """Resolve Telegram credentials at dispatch time, not module load time."""
    return os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", "")


def _get_slack_url() -> str:
    """Resolve Slack webhook URL at dispatch time, not module load time."""
    return os.getenv("SLACK_WEBHOOK_URL", "")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _post_telegram(payload: dict):
    token, _ = _get_telegram_creds()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _post_slack(payload: dict):
    slack_url = _get_slack_url()
    resp = requests.post(slack_url, json=payload, timeout=10)
    resp.raise_for_status()


def _dispatch(message: str, level: str = "INFO"):
    token, chat_id = _get_telegram_creds()
    if token and chat_id:
        try:
            _post_telegram({
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            })
        except Exception:
            pass

    slack_url = _get_slack_url()
    if slack_url:
        color_map = {"INFO": "#36a64f", "WARN": "#ffa500", "ERROR": "#ff0000", "CRITICAL": "#8b0000"}
        try:
            _post_slack({
                "attachments": [{
                    "color": color_map.get(level, "#36a64f"),
                    "text": message.replace("*", ""),
                    "mrkdwn_in": ["text"],
                }]
            })
        except Exception:
            pass


def notify(message: str, level: str = "INFO"):
    """Non-blocking dispatch. Spawns a daemon thread — never blocks audit loop."""
    threading.Thread(target=_dispatch, args=(message, level), daemon=True).start()


def notify_audit_start(repo: str):
    notify(f"🚀 *Rhodawk AI*\n\nAutonomous audit initiated on `{repo}`.", "INFO")


def notify_test_failed(test_path: str):
    notify(f"⚠️ *Test Failed*\n`{test_path}`\nDispatching Aider agent...", "WARN")


def notify_sast_blocked(test_path: str, reason: str):
    notify(f"🛡️ *SAST Gate BLOCKED PR*\n`{test_path}`\nReason: `{reason}`\nHuman review required.", "CRITICAL")


def notify_pr_created(test_path: str, pr_url: str):
    notify(f"✅ *Auto-Heal PR Generated*\n`{test_path}`\n[View PR]({pr_url})\nAwaiting human review.", "INFO")


def notify_patch_failed(test_path: str):
    notify(f"🔴 *Patch Failed*\n`{test_path}`\nAider returned non-zero exit.", "ERROR")


def notify_audit_complete(metrics: dict):
    notify(
        f"🎯 *Audit Complete*\n"
        f"Scanned: `{metrics['total']}` | Green: `{metrics['done']}` | "
        f"PRs: `{metrics['prs_created']}` | SAST Blocked: `{metrics['sast_blocked']}`",
        "INFO",
    )


def notify_chain_integrity(valid: bool, summary: str):
    if valid:
        notify(f"🔒 *Audit Chain Verified*\n{summary}", "INFO")
    else:
        notify(f"🚨 *CHAIN INTEGRITY VIOLATION*\n{summary}", "CRITICAL")
