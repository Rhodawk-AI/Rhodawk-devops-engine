"""
Rhodawk AI — Async Telegram Bot (decoupled polling listener)
============================================================
The previous Telegram surface was a Flask webhook bolted onto the main
process. With the 14 GB local embedding model and the gRPC bridges
sharing the same Python interpreter, the main thread routinely stalled
for tens of seconds — long enough for the webhook server's worker to
miss `/start` and never reply.

This module runs the Telegram bot on **its own dedicated daemon thread**
with its own asyncio event loop, using `python-telegram-bot` v20+ async
polling. It never blocks on, and is never blocked by, the engine's
synchronous fuzzing / static-analysis work.

Public surface
--------------
    start_in_background(token=None, *, chat_id=None) -> threading.Thread | None
        Idempotent. Spawns the listener thread once per process and
        returns the thread (or None if PTB is unavailable / no token).

    stop() -> None
        Signal the polling loop to exit cleanly.

The bot exposes:
    /start     → "I'm DevSecOps ready for my first task" (with debug log)
    /help      → list of intents from openclaw_gateway
    /status    → engine status from openclaw_gateway
    <free text>→ openclaw_gateway.handle_command(...)

All command handlers run inside the bot's own event loop and never
share mutable state with the main process beyond the openclaw_gateway
intent dispatcher (which is pure-Python and safe to call from any
thread).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from typing import Any

LOG = logging.getLogger("rhodawk.telegram_bot")

# Verbose ingestion logging is on by default for debugging the
# unresponsiveness issue. Set RHODAWK_TG_DEBUG=0 to silence.
DEBUG = os.getenv("RHODAWK_TG_DEBUG", "1") != "0"

# Make sure debug log lines hit stderr even if the root logger has no
# handler attached (the main app sometimes attaches handlers late).
if DEBUG and not LOG.handlers:
    _h = logging.StreamHandler(sys.stderr)
    _h.setFormatter(logging.Formatter(
        "[telegram_bot %(asctime)s %(levelname)s] %(message)s",
        "%H:%M:%S",
    ))
    LOG.addHandler(_h)
    LOG.setLevel(logging.DEBUG)


# ── State (guarded — no race on double-start) ─────────────────────────────
_THREAD: threading.Thread | None = None
_STATE_LOCK = threading.Lock()
_STOP_EVENT = threading.Event()
_LOOP: asyncio.AbstractEventLoop | None = None


# ── Handlers ──────────────────────────────────────────────────────────────
async def _start_handler(update, context) -> None:  # type: ignore[no-untyped-def]
    """`/start` — verbose-logged readiness ping."""
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    LOG.info(
        "INGEST /start :: user_id=%s username=%s chat_id=%s text=%r",
        getattr(user, "id", None),
        getattr(user, "username", None),
        getattr(chat, "id", None),
        getattr(msg, "text", None),
    )

    reply = "I'm DevSecOps ready for my first task"
    try:
        await msg.reply_text(reply)
        LOG.info("EGRESS /start OK chat_id=%s", getattr(chat, "id", None))
    except Exception as exc:  # noqa: BLE001
        LOG.exception("EGRESS /start FAILED chat_id=%s — %s",
                      getattr(chat, "id", None), exc)


async def _help_handler(update, context) -> None:  # type: ignore[no-untyped-def]
    LOG.info("INGEST /help chat_id=%s", update.effective_chat.id)
    try:
        from openclaw_gateway import handle_command  # type: ignore
        result = await asyncio.to_thread(handle_command, "help",
                                         user=f"telegram:{update.effective_chat.id}")
        await update.effective_message.reply_text(result.get("reply") or "(no help)")
    except Exception as exc:  # noqa: BLE001
        LOG.exception("/help failed: %s", exc)
        await update.effective_message.reply_text(f"help failed: {exc}")


async def _status_handler(update, context) -> None:  # type: ignore[no-untyped-def]
    LOG.info("INGEST /status chat_id=%s", update.effective_chat.id)
    try:
        from openclaw_gateway import handle_command  # type: ignore
        # `handle_command` may invoke synchronous engine code, so run it
        # off the event loop in a worker thread. This is the critical
        # decoupling — the polling loop NEVER awaits a sync call directly.
        result = await asyncio.to_thread(handle_command, "status",
                                         user=f"telegram:{update.effective_chat.id}")
        await update.effective_message.reply_text(result.get("reply") or "(no status)")
    except Exception as exc:  # noqa: BLE001
        LOG.exception("/status failed: %s", exc)
        await update.effective_message.reply_text(f"status failed: {exc}")


async def _freeform_handler(update, context) -> None:  # type: ignore[no-untyped-def]
    msg = update.effective_message
    text = (msg.text or "").strip()
    if not text or text.startswith("/"):
        return
    LOG.info("INGEST text chat_id=%s text=%r", update.effective_chat.id, text)
    try:
        from openclaw_gateway import handle_command  # type: ignore
        result = await asyncio.to_thread(
            handle_command, text, user=f"telegram:{update.effective_chat.id}"
        )
        await msg.reply_text(result.get("reply") or "(no reply)")
    except Exception as exc:  # noqa: BLE001
        LOG.exception("freeform handler failed: %s", exc)
        await msg.reply_text(f"handler failed: {exc}")


async def _error_handler(update, context) -> None:  # type: ignore[no-untyped-def]
    LOG.exception("PTB error: %s", getattr(context, "error", None))


# ── Bot loop ──────────────────────────────────────────────────────────────
async def _run_bot_async(token: str) -> None:
    """Build the Application, run async polling until `_STOP_EVENT` fires."""
    try:
        from telegram.ext import (  # type: ignore
            Application,
            CommandHandler,
            MessageHandler,
            filters,
        )
    except Exception as exc:  # noqa: BLE001
        LOG.error("python-telegram-bot v20+ not installed — bot disabled (%s)", exc)
        return

    app = (
        Application.builder()
        .token(token)
        # Concurrent updates means PTB will dispatch handlers in parallel
        # rather than serially — `/start` will not have to wait behind a
        # slow `/status` call from another user.
        .concurrent_updates(True)
        .build()
    )

    app.add_handler(CommandHandler("start", _start_handler))
    app.add_handler(CommandHandler("help", _help_handler))
    app.add_handler(CommandHandler("status", _status_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _freeform_handler))
    app.add_error_handler(_error_handler)

    LOG.info("Telegram bot starting async polling (debug=%s)", DEBUG)

    # Manual lifecycle so we can interleave with our own stop event.
    await app.initialize()
    await app.start()
    # `drop_pending_updates=True` clears stale updates that piled up
    # while the previous (blocked) main thread was unresponsive — this
    # is what made `/start` look "dead" after a restart.
    await app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=None,
    )
    LOG.info("Telegram bot polling. Send /start to verify ingestion.")

    try:
        # Park here until someone calls stop(); poll the threading.Event
        # cooperatively so we never block the event loop.
        while not _STOP_EVENT.is_set():
            await asyncio.sleep(0.5)
    finally:
        LOG.info("Telegram bot shutting down…")
        try:
            await app.updater.stop()
        except Exception:  # noqa: BLE001
            pass
        try:
            await app.stop()
        except Exception:  # noqa: BLE001
            pass
        try:
            await app.shutdown()
        except Exception:  # noqa: BLE001
            pass
        LOG.info("Telegram bot shutdown complete.")


def _thread_entry(token: str) -> None:
    """Daemon-thread target: own asyncio loop, bound to this thread only."""
    global _LOOP
    loop = asyncio.new_event_loop()
    _LOOP = loop
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_bot_async(token))
    except Exception as exc:  # noqa: BLE001
        LOG.exception("Telegram bot crashed: %s", exc)
    finally:
        try:
            loop.close()
        except Exception:  # noqa: BLE001
            pass
        _LOOP = None


# ── Public API ────────────────────────────────────────────────────────────
def start_in_background(
    token: str | None = None,
    *,
    chat_id: str | None = None,  # noqa: ARG001 — accepted for API symmetry
) -> threading.Thread | None:
    """
    Spawn the polling listener on its own daemon thread (idempotent).

    Returns the running thread, or None if PTB is unavailable or no
    `TELEGRAM_BOT_TOKEN` is configured.
    """
    global _THREAD

    # Race-safe: two callers hitting start_in_background() simultaneously
    # would previously each construct a thread and both would race for the
    # Telegram getUpdates long-poll, causing dropped messages. The lock +
    # is_alive() check guarantees a single live listener per process.
    with _STATE_LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            LOG.debug("start_in_background: bot already running")
            return _THREAD

        tok = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not tok:
            LOG.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
            return None

        try:
            import telegram.ext  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            LOG.warning("python-telegram-bot not installed — bot disabled (%s)",
                        exc)
            return None

        _STOP_EVENT.clear()
        _THREAD = threading.Thread(
            target=_thread_entry,
            args=(tok,),
            name="rhodawk-telegram-bot",
            daemon=True,
        )
        _THREAD.start()
        LOG.info("Telegram bot thread spawned (name=%s)", _THREAD.name)
        return _THREAD


def stop() -> None:
    """Signal the polling loop to exit. Safe to call from any thread."""
    _STOP_EVENT.set()
    loop = _LOOP
    if loop and loop.is_running():
        # Give the loop a wake-up nudge so the `await asyncio.sleep`
        # in `_run_bot_async` returns promptly.
        try:
            loop.call_soon_threadsafe(lambda: None)
        except Exception:  # noqa: BLE001
            pass


def is_running() -> bool:
    return _THREAD is not None and _THREAD.is_alive()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG)
    t = start_in_background()
    if t is None:
        sys.exit("Telegram bot did not start — check TELEGRAM_BOT_TOKEN and PTB install.")
    try:
        t.join()
    except KeyboardInterrupt:
        stop()
