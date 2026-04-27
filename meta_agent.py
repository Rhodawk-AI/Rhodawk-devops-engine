"""
Rhodawk EmbodiedOS — MetaCoordinator (Gap 11, XBOW Architecture)
=================================================================
Persistent coordinator + short-lived stateless sub-agents.

INV-025: Sub-agents must be stateless (fresh context per invocation).

The orchestrator's main loop runs in the persistent coordinator. Each
tool dispatch is handed to a NEW ``StatelessSubAgent`` instance with
ONLY the immediate inputs visible. No conversation state, no global
mutable context, no carry-over between sub-agent invocations.

Why this matters
----------------
Long-running coordinator loops accumulate context that subtly biases
later tool calls, leaks credentials between unrelated targets, and
makes failures non-reproducible. Splitting the loop into a coordinator
that *decides* and ephemeral agents that *execute* preserves
determinism: any sub-agent invocation can be re-run from its
serialized inputs and will produce the same result.

Public surface
--------------
    MetaCoordinator(dispatch_fn)            persistent driver
        .spawn_agent_for_tool(tool_name, args, session_meta)
        .stats()                             counters + audit trail head

    StatelessSubAgent(agent_id, dispatch_fn)
        .execute(tool_name, args, session_meta) -> dict

The coordinator never holds references to spawned agents after
``execute`` returns. Each agent's working memory is garbage-collected.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

LOG = logging.getLogger("rhodawk.meta_agent")

INV025_AUDIT_PATH = os.getenv(
    "RHODAWK_META_AUDIT_LOG", "/data/meta_agent_audit.log"
)
MAX_AUDIT_TRAIL_IN_MEMORY = 256


@dataclass(frozen=True)
class SubAgentResult:
    agent_id: str
    tool_name: str
    started_at: float
    finished_at: float
    ok: bool
    result: Any
    error: Optional[str] = None

    @property
    def latency_ms(self) -> float:
        return (self.finished_at - self.started_at) * 1000.0


@dataclass
class _SessionMeta:
    """The ONLY context a sub-agent receives.

    Intentionally narrow: session id (for correlation), repo dir (for
    filesystem scope), and a phase tag. No messages, no findings, no
    tool history. INV-025 enforcement.
    """
    session_id: str
    repo_dir: str
    phase: str = "unknown"


class StatelessSubAgent:
    """One-shot tool executor. Created, invoked once, discarded.

    Holds NO mutable state across invocations. The instance is created
    inside ``MetaCoordinator.spawn_agent_for_tool`` and dropped on
    return — guaranteed by the coordinator never storing the reference.
    """

    __slots__ = ("agent_id", "_dispatch_fn", "_used")

    def __init__(self, agent_id: str, dispatch_fn: Callable[[str, dict, Any], Any]):
        self.agent_id = agent_id
        self._dispatch_fn = dispatch_fn
        self._used = False

    def execute(
        self,
        tool_name: str,
        args: dict,
        session_meta: _SessionMeta,
    ) -> SubAgentResult:
        if self._used:
            # INV-025 hard guard: refuse re-use even if the caller tries.
            raise RuntimeError(
                f"INV-025 violation: sub-agent {self.agent_id} already used"
            )
        self._used = True

        scoped_args = dict(args)
        scoped_args.setdefault("repo_dir", session_meta.repo_dir)

        # Build a minimal session-shaped object the dispatch function
        # expects, but with NO findings list, NO message history.
        session_proxy = _MinimalSessionProxy(
            session_id=session_meta.session_id,
            repo_dir=session_meta.repo_dir,
            phase=session_meta.phase,
        )

        t0 = time.perf_counter()
        try:
            result = self._dispatch_fn(tool_name, scoped_args, session_proxy)
            return SubAgentResult(
                agent_id=self.agent_id,
                tool_name=tool_name,
                started_at=t0,
                finished_at=time.perf_counter(),
                ok=True,
                result=result,
            )
        except Exception as exc:  # noqa: BLE001
            return SubAgentResult(
                agent_id=self.agent_id,
                tool_name=tool_name,
                started_at=t0,
                finished_at=time.perf_counter(),
                ok=False,
                result=None,
                error=str(exc)[:1000],
            )


class _MinimalSessionProxy:
    """Read-only-ish session shape passed to dispatch.

    Real session attributes (findings, messages, phase) are NOT
    forwarded. The dispatch path that wants to mutate the canonical
    session must do so through the coordinator's reconciliation step.
    """

    __slots__ = ("session_id", "repo_dir", "phase", "_findings_buf")

    def __init__(self, session_id: str, repo_dir: str, phase: str):
        self.session_id = session_id
        self.repo_dir = repo_dir
        self.phase = phase
        # Some tools append to session.findings; capture in an
        # ephemeral buffer the coordinator can drain after execute().
        self._findings_buf: list = []

    @property
    def findings(self) -> list:
        return self._findings_buf

    def __repr__(self) -> str:
        return f"<EphemeralSession id={self.session_id} phase={self.phase}>"


class MetaCoordinator:
    """Persistent coordinator. Owns the audit trail; owns no agent state.

    The coordinator is the ONLY long-lived object in the dispatch
    path. Sub-agents come and go with each tool call.
    """

    def __init__(self, dispatch_fn: Callable[[str, dict, Any], Any]):
        self._dispatch_fn = dispatch_fn
        self._lock = threading.Lock()
        self._counter = 0
        self._audit_trail: list[SubAgentResult] = []
        self._counters: dict[str, int] = {"spawned": 0, "ok": 0, "err": 0}

    def _new_agent_id(self) -> str:
        with self._lock:
            self._counter += 1
            seed = f"{uuid.uuid4().hex}:{self._counter}:{time.time_ns()}"
        return "agent_" + hashlib.sha1(seed.encode()).hexdigest()[:12]

    def spawn_agent_for_tool(
        self,
        tool_name: str,
        args: dict,
        session_meta: _SessionMeta | dict | Any,
    ) -> SubAgentResult:
        """Create a fresh sub-agent, run it once, discard it.

        ``session_meta`` may be a ``_SessionMeta``, a plain dict with
        ``session_id``/``repo_dir``/``phase``, or any object exposing
        those attributes. Anything else is treated as opaque context
        and ignored — INV-025 forbids carrying it into the agent.
        """
        meta = self._coerce_meta(session_meta)
        agent_id = self._new_agent_id()
        agent = StatelessSubAgent(agent_id, self._dispatch_fn)
        result = agent.execute(tool_name, args, meta)
        self._record(result)
        # Local reference to the agent dies when this method returns —
        # no map, no list, no closure retains it. INV-025 holds.
        del agent
        return result

    def _coerce_meta(self, raw: Any) -> _SessionMeta:
        if isinstance(raw, _SessionMeta):
            return raw
        if isinstance(raw, dict):
            return _SessionMeta(
                session_id=str(raw.get("session_id", "anon")),
                repo_dir=str(raw.get("repo_dir", "")),
                phase=str(raw.get("phase", "unknown")),
            )
        return _SessionMeta(
            session_id=str(getattr(raw, "session_id", "anon")),
            repo_dir=str(getattr(raw, "repo_dir", "")),
            phase=str(
                getattr(getattr(raw, "phase", None), "value", None)
                or getattr(raw, "phase", "unknown")
            ),
        )

    def _record(self, result: SubAgentResult) -> None:
        with self._lock:
            self._audit_trail.append(result)
            if len(self._audit_trail) > MAX_AUDIT_TRAIL_IN_MEMORY:
                self._audit_trail.pop(0)
            self._counters["spawned"] += 1
            if result.ok:
                self._counters["ok"] += 1
            else:
                self._counters["err"] += 1
        try:
            os.makedirs(os.path.dirname(INV025_AUDIT_PATH) or ".", exist_ok=True)
            with open(INV025_AUDIT_PATH, "a", encoding="utf-8") as fh:
                fh.write(
                    f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
                    f"agent={result.agent_id} tool={result.tool_name} "
                    f"ok={result.ok} latency_ms={result.latency_ms:.1f}\n"
                )
        except Exception as exc:  # noqa: BLE001
            LOG.debug("meta-agent audit append failed: %s", exc)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "audit_trail_size": len(self._audit_trail),
                "last": (
                    {
                        "agent_id": self._audit_trail[-1].agent_id,
                        "tool": self._audit_trail[-1].tool_name,
                        "ok": self._audit_trail[-1].ok,
                        "latency_ms": round(self._audit_trail[-1].latency_ms, 1),
                    }
                    if self._audit_trail
                    else None
                ),
            }


__all__ = [
    "MetaCoordinator",
    "StatelessSubAgent",
    "SubAgentResult",
    "_SessionMeta",
]
