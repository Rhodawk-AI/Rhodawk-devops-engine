"""
Rhodawk AI — Event-Driven Webhook Server
==========================================
Accepts GitHub push events, CI failure webhooks, and manual triggers.
Runs alongside Gradio in a separate thread on port 7861.

Supported events:
  POST /webhook/github       — GitHub push/status/check_run webhooks (HMAC-SHA256 validated)
  POST /webhook/ci           — Generic CI failure payload (any CI system)
  POST /webhook/trigger      — Manual trigger with repo + test path
  GET  /webhook/health       — Health check
  GET  /webhook/queue        — Current job queue status

This makes Rhodawk a first-class CI/CD participant — not a side tool you run manually.
"""

import hashlib
import hmac
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import urlparse

WEBHOOK_SECRET = os.getenv("RHODAWK_WEBHOOK_SECRET", "")
WEBHOOK_PORT = int(os.getenv("RHODAWK_WEBHOOK_PORT", "7861"))

_webhook_log: list[dict] = []
_webhook_lock = threading.Lock()
_job_dispatcher: Callable = None  # Set at runtime by app.py
_rate_limit: dict[str, list[float]] = {}
_RATE_LIMIT_MAX_EVENTS = int(os.getenv("RHODAWK_WEBHOOK_RATE_LIMIT", "10"))
_RATE_LIMIT_WINDOW_SECONDS = 60


def set_job_dispatcher(fn: Callable):
    """Register the function that app.py uses to spawn audit jobs."""
    global _job_dispatcher
    _job_dispatcher = fn


def _log_webhook(event_type: str, payload: dict, status: str, detail: str = ""):
    with _webhook_lock:
        _webhook_log.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "status": status,
            "detail": detail,
            "repo": payload.get("repository", {}).get("full_name", payload.get("repo", "unknown")),
        })
        if len(_webhook_log) > 200:
            _webhook_log.pop(0)


def get_webhook_log(limit: int = 50) -> list[dict]:
    with _webhook_lock:
        return list(reversed(_webhook_log[-limit:]))


def _verify_github_signature(body: bytes, signature_header: str) -> bool:
    if not WEBHOOK_SECRET:
        return True  # Skip validation if secret not configured
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    expected = mac.hexdigest()
    received = signature_header[7:]
    return hmac.compare_digest(expected, received)


def _rate_limit_allows(ip: str) -> bool:
    now = time.time()
    with _webhook_lock:
        events = [t for t in _rate_limit.get(ip, []) if now - t < _RATE_LIMIT_WINDOW_SECONDS]
        if len(events) >= _RATE_LIMIT_MAX_EVENTS:
            _rate_limit[ip] = events
            return False
        events.append(now)
        _rate_limit[ip] = events
        return True


def _parse_github_event(event_type: str, payload: dict) -> dict:
    """Extract repo, branch, and context from a GitHub webhook payload."""
    repo = payload.get("repository", {}).get("full_name", "")
    branch = (
        payload.get("ref", "").replace("refs/heads/", "") or
        payload.get("check_run", {}).get("head_branch", "main") or
        "main"
    )
    context = {
        "repo": repo,
        "branch": branch,
        "event_type": event_type,
        "commit_sha": payload.get("after") or payload.get("check_run", {}).get("head_sha", ""),
        "triggered_by": "github_webhook",
    }

    if event_type == "check_run":
        check = payload.get("check_run", {})
        if check.get("conclusion") == "failure":
            context["failing_check"] = check.get("name", "")
            context["details_url"] = check.get("details_url", "")
            return context
        return {}  # Only care about failures

    if event_type == "status":
        if payload.get("state") == "failure":
            context["failing_context"] = payload.get("context", "")
            return context
        return {}

    # push event — trigger full audit
    return context


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default HTTP server logs

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/webhook/health":
            self._send_json(200, {
                "status": "ok",
                "dispatcher_ready": _job_dispatcher is not None,
                "webhook_events_received": len(_webhook_log),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

        elif path == "/webhook/queue":
            from job_queue import list_all_jobs, get_metrics
            self._send_json(200, {
                "metrics": get_metrics(),
                "recent_jobs": list_all_jobs()[:10],
            })

        elif path == "/webhook/log":
            self._send_json(200, {"events": get_webhook_log(50)})

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        client_ip = self.client_address[0] if self.client_address else "unknown"
        if not _rate_limit_allows(client_ip):
            _log_webhook("rate_limit", {"repo": "unknown"}, "REJECTED", f"Too many events from {client_ip}")
            self._send_json(429, {"error": "Rate limit exceeded"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        if path == "/webhook/github":
            sig = self.headers.get("X-Hub-Signature-256", "")
            if not _verify_github_signature(body, sig):
                _log_webhook("github", payload, "REJECTED", "Invalid HMAC signature")
                self._send_json(401, {"error": "Invalid signature"})
                return

            event_type = self.headers.get("X-GitHub-Event", "push")
            context = _parse_github_event(event_type, payload)

            if not context or not context.get("repo"):
                _log_webhook(event_type, payload, "IGNORED", "Event not actionable")
                self._send_json(200, {"status": "ignored", "reason": "Event not actionable"})
                return

            _log_webhook(event_type, payload, "ACCEPTED", f"Triggering audit for {context['repo']}")

            if _job_dispatcher:
                threading.Thread(
                    target=_job_dispatcher,
                    kwargs={"repo_override": context.get("repo"), "branch": context.get("branch", "main")},
                    daemon=True,
                ).start()

            self._send_json(202, {"status": "accepted", "context": context})

        elif path == "/webhook/ci":
            repo = payload.get("repo") or payload.get("repository", "")
            test_path = payload.get("test_path") or payload.get("failing_test", "")
            failure_output = payload.get("failure_output") or payload.get("log", "")

            if not repo:
                self._send_json(400, {"error": "Missing 'repo' field"})
                return

            _log_webhook("ci_failure", payload, "ACCEPTED", f"CI failure from {repo}")

            if _job_dispatcher:
                threading.Thread(
                    target=_job_dispatcher,
                    kwargs={"repo_override": repo, "specific_test": test_path},
                    daemon=True,
                ).start()

            self._send_json(202, {"status": "accepted", "repo": repo, "test": test_path})

        elif path == "/webhook/trigger":
            repo = payload.get("repo", os.getenv("GITHUB_REPO", ""))
            if _job_dispatcher:
                threading.Thread(target=_job_dispatcher, daemon=True).start()
                _log_webhook("manual_trigger", payload, "ACCEPTED", f"Manual trigger for {repo}")
                self._send_json(202, {"status": "accepted", "repo": repo})
            else:
                self._send_json(503, {"error": "Dispatcher not ready"})

        else:
            self._send_json(404, {"error": "Unknown webhook path"})


def start_webhook_server():
    """Start the webhook server in a daemon thread."""
    server = HTTPServer(("0.0.0.0", WEBHOOK_PORT), WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
