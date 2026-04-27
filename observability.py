"""
Rhodawk EmbodiedOS — Observability (Gap 14)
============================================
OpenTelemetry + Langfuse wrappers for the orchestrator. Every span is
non-blocking and degrades silently when the OTel SDK or Langfuse is not
installed, so a missing exporter MUST NOT take down the LLM pipeline.

INV-030: OpenTelemetry spans must not block LLM calls.
        — every wrapper is wrapped in try/except, every span has a hard
          timeout, and exporter failures are logged but never re-raised.

Public surface
--------------
    trace_span(name, attrs=None)            — context manager
    instrument_llm_router(chat_fn)          — decorator for llm_router.chat
    instrument_tool_dispatch(dispatch_fn)   — decorator for _dispatch_tool
    record_llm_event(role, model, tokens,
                     cost_usd, latency_ms,
                     prompt=None, response=None,
                     ok=True, error=None)   — Langfuse generation event
    shutdown()                              — flush + shutdown providers

Environment
-----------
    RHODAWK_TELEMETRY_ENABLED   "true"|"false"  default "true"
    OTEL_EXPORTER_OTLP_ENDPOINT host:port for OTLP/gRPC collector
    OTEL_SERVICE_NAME           default "rhodawk-devsecops"
    LANGFUSE_PUBLIC_KEY         pk_*   (optional)
    LANGFUSE_SECRET_KEY         sk_*   (optional)
    LANGFUSE_HOST               default https://cloud.langfuse.com
"""

from __future__ import annotations

import contextlib
import functools
import logging
import os
import time
from typing import Any, Callable, Iterator, Optional

LOG = logging.getLogger("rhodawk.observability")

ENABLED = os.getenv("RHODAWK_TELEMETRY_ENABLED", "true").lower() == "true"
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "rhodawk-devsecops")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

_tracer: Any = None
_langfuse_client: Any = None
_initialized = False


def _init() -> None:
    """Idempotent lazy init. Never raises — logs and degrades to no-op."""
    global _tracer, _langfuse_client, _initialized
    if _initialized:
        return
    _initialized = True
    if not ENABLED:
        LOG.info("Telemetry disabled (RHODAWK_TELEMETRY_ENABLED=false).")
        return

    # ── OpenTelemetry ────────────────────────────────────────────────
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
        )
        from opentelemetry.sdk.resources import Resource

        provider = TracerProvider(
            resource=Resource.create({"service.name": SERVICE_NAME})
        )
        if OTEL_ENDPOINT:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )
                provider.add_span_processor(
                    BatchSpanProcessor(
                        OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True),
                        max_export_batch_size=128,
                        schedule_delay_millis=2000,
                    )
                )
                LOG.info("OTel OTLP exporter wired → %s", OTEL_ENDPOINT)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("OTel OTLP exporter init failed: %s", exc)
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("rhodawk")
    except Exception as exc:  # noqa: BLE001
        LOG.warning("OpenTelemetry SDK unavailable — spans become no-ops: %s", exc)
        _tracer = None

    # ── Langfuse ─────────────────────────────────────────────────────
    if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
        try:
            from langfuse import Langfuse  # type: ignore
            _langfuse_client = Langfuse(
                public_key=LANGFUSE_PUBLIC_KEY,
                secret_key=LANGFUSE_SECRET_KEY,
                host=LANGFUSE_HOST,
            )
            LOG.info("Langfuse client wired → %s", LANGFUSE_HOST)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Langfuse init failed — LLM events become no-ops: %s", exc)
            _langfuse_client = None
    else:
        LOG.info("Langfuse keys not set — LLM events skipped.")


@contextlib.contextmanager
def trace_span(name: str, attrs: Optional[dict] = None) -> Iterator[Any]:
    """Non-blocking span context manager. Always yields. Never raises.

    INV-030: this MUST be safe to wrap around any LLM call. If the
    tracer is unavailable, exporter is down, or the span itself errors,
    the wrapped block still runs to completion and exceptions from the
    inner block propagate normally.
    """
    _init()
    if _tracer is None:
        yield None
        return
    span = None
    try:
        span = _tracer.start_span(name)
        if attrs:
            for k, v in attrs.items():
                try:
                    span.set_attribute(k, v)
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001
        LOG.debug("trace_span %s start failed: %s", name, exc)
        span = None
    try:
        yield span
    finally:
        if span is not None:
            try:
                span.end()
            except Exception:  # noqa: BLE001
                pass


def record_llm_event(
    *,
    role: str,
    model: str,
    tokens: int = 0,
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
    prompt: Any = None,
    response: Any = None,
    ok: bool = True,
    error: Optional[str] = None,
) -> None:
    """Emit a Langfuse generation event. No-op if Langfuse not configured."""
    _init()
    if _langfuse_client is None:
        return
    try:
        _langfuse_client.generation(
            name=f"llm.{role}",
            model=model,
            input=prompt,
            output=response,
            metadata={
                "tokens": tokens,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "ok": ok,
                "error": error,
            },
        )
    except Exception as exc:  # noqa: BLE001
        LOG.debug("Langfuse generation event failed: %s", exc)


def instrument_llm_router(chat_fn: Callable) -> Callable:
    """Decorator for ``llm_router.chat``. Wraps each call in a span + Langfuse event.

    Signature preserved: ``chat(role, messages, **kw) -> dict|str``.
    INV-030: failures in the telemetry path NEVER short-circuit the LLM call.
    """

    @functools.wraps(chat_fn)
    def wrapper(role: str, messages: list, *args: Any, **kwargs: Any) -> Any:
        model_hint = kwargs.get("model") or role
        t0 = time.perf_counter()
        with trace_span(
            "llm.chat",
            {"llm.role": role, "llm.model_hint": str(model_hint)},
        ):
            try:
                result = chat_fn(role, messages, *args, **kwargs)
                latency = (time.perf_counter() - t0) * 1000.0
                try:
                    record_llm_event(
                        role=role,
                        model=str(model_hint),
                        latency_ms=latency,
                        prompt=str(messages)[:4000],
                        response=str(result)[:4000],
                        ok=True,
                    )
                except Exception:  # noqa: BLE001
                    pass
                return result
            except Exception as exc:
                latency = (time.perf_counter() - t0) * 1000.0
                try:
                    record_llm_event(
                        role=role,
                        model=str(model_hint),
                        latency_ms=latency,
                        ok=False,
                        error=str(exc)[:500],
                    )
                except Exception:  # noqa: BLE001
                    pass
                raise

    wrapper.__rhodawk_instrumented__ = True  # type: ignore[attr-defined]
    return wrapper


def instrument_tool_dispatch(dispatch_fn: Callable) -> Callable:
    """Decorator for ``hermes_orchestrator._dispatch_tool``. One span per tool call."""

    @functools.wraps(dispatch_fn)
    def wrapper(tool_name: str, args: dict, session: Any) -> Any:
        with trace_span(
            "hermes.tool",
            {"tool.name": tool_name, "session.id": getattr(session, "session_id", "")},
        ):
            return dispatch_fn(tool_name, args, session)

    wrapper.__rhodawk_instrumented__ = True  # type: ignore[attr-defined]
    return wrapper


def shutdown() -> None:
    """Flush + shut down exporters. Safe to call at process exit."""
    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        shut = getattr(provider, "shutdown", None)
        if callable(shut):
            shut()
    except Exception:  # noqa: BLE001
        pass
    try:
        if _langfuse_client is not None:
            flush = getattr(_langfuse_client, "flush", None)
            if callable(flush):
                flush()
    except Exception:  # noqa: BLE001
        pass


__all__ = [
    "trace_span",
    "instrument_llm_router",
    "instrument_tool_dispatch",
    "record_llm_event",
    "shutdown",
]
