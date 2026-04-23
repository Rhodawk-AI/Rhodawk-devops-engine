"""
OpenClaude gRPC client — replaces the legacy aider subprocess shell-out.

Design contract
---------------
Every callable in this module returns an :class:`OpenClaudeResult` (or the
``(combined_output, exit_code)`` tuple that legacy callers expect) so that the
existing validation, SAST gate, conviction engine, and red-team loops keep
plugging in unchanged.

Streaming events from the daemon (text chunks, tool start/result, action
required) are accumulated into a single transcript so that downstream code
that previously parsed aider stdout still sees a useful blob.

Operational guarantees
----------------------
* Connection drops, ``StatusCode.UNAVAILABLE`` and stream-level RPC errors
  are converted into a non-zero exit code with the error message embedded in
  the combined output (mirrors aider's crash semantics).
* Per-call wall-clock timeout (defaults to 600 s) — same as the legacy
  aider invocation.
* Bidi stream auto-answers any ``ActionRequired`` prompt with ``"y"`` so that
  headless mode never deadlocks waiting for human input. The daemon also
  honours ``OPENCLAUDE_AUTO_APPROVE=1`` server-side as a belt-and-braces.
* Each call produces a fresh stream — sessions are not shared across calls
  to keep failures isolated.
"""
from __future__ import annotations

import logging
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

import grpc

from . import openclaude_pb2 as pb  # type: ignore
from . import openclaude_pb2_grpc as pb_grpc  # type: ignore

logger = logging.getLogger("openclaude_grpc")

DEFAULT_HOST = os.getenv("OPENCLAUDE_GRPC_HOST", "127.0.0.1")
DEFAULT_PORT_DO = int(os.getenv("OPENCLAUDE_GRPC_PORT_DO", "50051"))
DEFAULT_PORT_OR = int(os.getenv("OPENCLAUDE_GRPC_PORT_OR", "50052"))
DEFAULT_TIMEOUT = int(os.getenv("OPENCLAUDE_TIMEOUT", "600"))


class OpenClaudeError(RuntimeError):
    """Raised for unrecoverable client-side errors (connect, decode, etc)."""


@dataclass
class OpenClaudeResult:
    """Mirror of the legacy aider return contract.

    ``stdout`` is the model's narrative + tool stdout, ``stderr`` is tool
    failures and gRPC errors, ``exit_code`` is 0 on a clean ``done`` event,
    non-zero on any error event or transport failure. ``model_used`` lets
    downstream telemetry attribute findings to the right provider.
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: list[dict] = field(default_factory=list)

    @property
    def combined_output(self) -> str:
        if self.stderr:
            return f"{self.stdout}\n{self.stderr}".strip()
        return self.stdout.strip()

    def as_legacy_tuple(self) -> tuple[str, int]:
        return self.combined_output, self.exit_code


class OpenClaudeClient:
    """Bidirectional-streaming client for one OpenClaude daemon."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT_DO,
        timeout: int = DEFAULT_TIMEOUT,
        max_message_mb: int = 64,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        opts = [
            ("grpc.max_send_message_length", max_message_mb * 1024 * 1024),
            ("grpc.max_receive_message_length", max_message_mb * 1024 * 1024),
            ("grpc.keepalive_time_ms", 30_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.keepalive_permit_without_calls", 1),
        ]
        self._channel = grpc.insecure_channel(f"{host}:{port}", options=opts)
        self._stub = pb_grpc.AgentServiceStub(self._channel)

    # ------------------------------------------------------------------
    # health
    # ------------------------------------------------------------------
    def wait_ready(self, deadline_s: float = 60.0) -> bool:
        """Block until the daemon's gRPC channel is READY or the deadline
        elapses. Used by the orchestrator at boot to ensure the bun-built
        daemon is alive before issuing the first healing call."""
        start = time.monotonic()
        while time.monotonic() - start < deadline_s:
            try:
                grpc.channel_ready_future(self._channel).result(timeout=2.0)
                return True
            except grpc.FutureTimeoutError:
                continue
            except Exception:
                time.sleep(0.5)
        return False

    # ------------------------------------------------------------------
    # core call
    # ------------------------------------------------------------------
    def chat(
        self,
        message: str,
        working_directory: str,
        model: str = "",
        session_id: str = "",
        timeout: Optional[int] = None,
    ) -> OpenClaudeResult:
        """Send one prompt, drain the bidi stream, return an aggregated
        :class:`OpenClaudeResult`."""
        deadline = timeout if timeout is not None else self.timeout
        result = OpenClaudeResult(model_used=model)

        outbound: "queue.Queue[Optional[pb.ClientMessage]]" = queue.Queue()
        outbound.put(
            pb.ClientMessage(
                request=pb.ChatRequest(
                    message=message,
                    working_directory=working_directory,
                    model=model,
                    session_id=session_id,
                )
            )
        )

        def _send_iter() -> Iterable[pb.ClientMessage]:
            while True:
                item = outbound.get()
                if item is None:
                    return
                yield item

        done = threading.Event()
        try:
            stream = self._stub.Chat(_send_iter(), timeout=deadline)
            for ev in stream:
                kind = ev.WhichOneof("event")
                if kind == "text_chunk":
                    result.stdout += ev.text_chunk.text
                elif kind == "tool_start":
                    result.tool_calls.append(
                        {
                            "tool": ev.tool_start.tool_name,
                            "args": ev.tool_start.arguments_json,
                            "id": ev.tool_start.tool_use_id,
                        }
                    )
                    result.stdout += (
                        f"\n[tool ▶ {ev.tool_start.tool_name}]"
                        f" {ev.tool_start.arguments_json}\n"
                    )
                elif kind == "tool_result":
                    prefix = "[tool ✗]" if ev.tool_result.is_error else "[tool ✓]"
                    line = (
                        f"\n{prefix} {ev.tool_result.tool_name}:"
                        f" {ev.tool_result.output}\n"
                    )
                    if ev.tool_result.is_error:
                        result.stderr += line
                    else:
                        result.stdout += line
                elif kind == "action_required":
                    # Auto-approve. Server should already be in
                    # OPENCLAUDE_AUTO_APPROVE=1, but we double-tap to make
                    # the client safe even if the daemon was started
                    # without that flag.
                    outbound.put(
                        pb.ClientMessage(
                            input=pb.UserInput(
                                prompt_id=ev.action_required.prompt_id,
                                reply="y",
                            )
                        )
                    )
                elif kind == "done":
                    if not result.stdout and ev.done.full_text:
                        result.stdout = ev.done.full_text
                    result.prompt_tokens = ev.done.prompt_tokens
                    result.completion_tokens = ev.done.completion_tokens
                    result.exit_code = 0
                    done.set()
                    break
                elif kind == "error":
                    result.stderr += (
                        f"\n[openclaude {ev.error.code}] {ev.error.message}"
                    )
                    result.exit_code = 1
                    done.set()
                    break
        except grpc.RpcError as exc:
            result.stderr += (
                f"\n[grpc {exc.code().name}] {exc.details() or str(exc)}"
            )
            result.exit_code = 2
        except Exception as exc:  # noqa: BLE001
            result.stderr += f"\n[client] {type(exc).__name__}: {exc}"
            result.exit_code = 3
        finally:
            outbound.put(None)
            try:
                self._channel  # keep alive — see close()
            except Exception:
                pass
            if not done.is_set() and result.exit_code == 0:
                # Stream ended without an explicit done event.
                result.exit_code = 4
                result.stderr += "\n[client] stream ended without done event"

        return result

    def close(self) -> None:
        try:
            self._channel.close()
        except Exception:
            pass

    def __enter__(self) -> "OpenClaudeClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


# ──────────────────────────────────────────────────────────────────────
# High-level helper — drop-in replacement for the legacy ``run_aider``
# ──────────────────────────────────────────────────────────────────────
def _format_prompt(prompt: str, context_files: list[str]) -> str:
    """Aider received context files as CLI args; OpenClaude gets them
    inline so it knows which files matter. The agent already has full
    file-tool access via MCP/native tools, so this is just hinting."""
    if not context_files:
        return prompt
    file_list = "\n".join(f"- {p}" for p in context_files)
    return (
        f"{prompt}\n\n"
        "── Context files (focus your edits here) ──\n"
        f"{file_list}\n"
    )


def run_openclaude(
    mcp_config_path: str,
    prompt: str,
    context_files: list[str],
    *,
    repo_dir: str,
    primary_port: int = DEFAULT_PORT_DO,
    fallback_port: int = DEFAULT_PORT_OR,
    primary_label: str = "DigitalOcean",
    fallback_label: str = "OpenRouter",
    primary_model: str = "",
    fallback_model: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    log_fn=None,
) -> tuple[str, int]:
    """Drop-in replacement for ``run_aider`` — preserves the
    ``(combined_output, exit_code)`` return shape so every caller in
    ``app.py`` works unchanged.

    Tries the **primary** daemon (DigitalOcean Inference) first; on any
    non-zero exit code it falls back to the **OpenRouter** daemon so the
    healing loop's existing 15-attempt retry semantics still apply.

    ``mcp_config_path`` is honoured by the daemon itself — it re-reads
    ``MCP_RUNTIME_CONFIG`` per chat session — so we just forward the
    path via env and pass the prompt verbatim.
    """
    # Make sure the daemon picks up the MCP file the orchestrator just
    # wrote. The daemon was launched with this env var; this assignment
    # is here only as documentation / safety net for ad-hoc test runs.
    os.environ.setdefault("MCP_RUNTIME_CONFIG", mcp_config_path)

    full_prompt = _format_prompt(prompt, context_files)

    chain: list[tuple[int, str, str]] = []
    if primary_port:
        chain.append((primary_port, primary_label, primary_model))
    if fallback_port and fallback_port != primary_port:
        chain.append((fallback_port, fallback_label, fallback_model))

    last_output, last_code = "", 1
    for idx, (port, label, model) in enumerate(chain):
        if log_fn:
            log_fn(
                f"OpenClaude attempt via {label} (port {port}, model={model or 'default'})",
                "INFO",
            )
        try:
            with OpenClaudeClient(
                host=DEFAULT_HOST, port=port, timeout=timeout
            ) as client:
                if not client.wait_ready(deadline_s=15.0):
                    msg = (
                        f"OpenClaude daemon at {DEFAULT_HOST}:{port} "
                        "not ready within 15s"
                    )
                    if log_fn:
                        log_fn(msg, "WARN")
                    last_output, last_code = msg, 5
                    continue
                result = client.chat(
                    message=full_prompt,
                    working_directory=repo_dir,
                    model=model,
                    timeout=timeout,
                )
        except Exception as exc:  # noqa: BLE001
            last_output = f"[client] {type(exc).__name__}: {exc}"
            last_code = 6
            if log_fn:
                log_fn(f"{label} client crash: {exc}", "FAIL")
            continue

        last_output, last_code = result.as_legacy_tuple()
        if last_code == 0:
            return last_output, last_code
        if log_fn and idx < len(chain) - 1:
            log_fn(
                f"{label} failed (exit {last_code}) — falling back",
                "WARN",
            )
    return last_output, last_code
