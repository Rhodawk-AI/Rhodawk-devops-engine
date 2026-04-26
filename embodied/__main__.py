"""
EmbodiedOS — CLI entrypoint.

Usage
-----

    python -m embodied bridge          # run only the MCP bridge (stdio)
    python -m embodied bridge --http   # MCP bridge over HTTP
    python -m embodied gateway         # run the unified HTTP gateway
    python -m embodied learn           # run the learning daemon (foreground)
    python -m embodied learn --once    # one tick, then exit
    python -m embodied sync-skills     # sync the unified skill catalogue
    python -m embodied side1 <repo>    # run Side 1 on a repo
    python -m embodied side2           # run Side 2 — one bounty cycle
    python -m embodied side2 --program HACKERONE/<handle>
    python -m embodied bootstrap       # start every long-running service in
                                       # background threads + block on SIGINT
                                       # (this is what entrypoint.sh calls).

Every sub-command exits cleanly on Ctrl-C and never raises to the shell.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import threading
import time

from embodied.bridge.mcp_server import serve as serve_bridge
from embodied.config import get_config
from embodied.learning.research_daemon import run_once as learn_once, start_daemon as start_learning
from embodied.pipelines.bounty_hunter import run_bounty_hunter, scan_bounty_program
from embodied.pipelines.repo_hunter import run_repo_hunter
from embodied.router.unified_gateway import build_gateway, serve_in_background
from embodied.skills.sync_engine import get_engine

LOG = logging.getLogger("embodied")


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    )


def _cmd_bridge(args: argparse.Namespace) -> int:
    serve_bridge(transport="http" if args.http else "stdio")
    return 0


def _cmd_gateway(args: argparse.Namespace) -> int:
    cfg = get_config().bridge
    gw = build_gateway()
    gw.serve_http(args.host or cfg.host, args.port or (cfg.port + 1))
    return 0


def _cmd_learn(args: argparse.Namespace) -> int:
    if args.once:
        print(json.dumps(learn_once(), indent=2))
        return 0
    t = start_learning()
    try:
        while t.is_alive():
            t.join(1.0)
    except KeyboardInterrupt:
        pass
    return 0


def _cmd_sync_skills(_: argparse.Namespace) -> int:
    print(json.dumps(get_engine().sync().to_json(), indent=2))
    return 0


def _cmd_side1(args: argparse.Namespace) -> int:
    print(json.dumps(run_repo_hunter(repo_url=args.repo, fix_only=args.fix_only), indent=2, default=str))
    return 0


def _cmd_side2(args: argparse.Namespace) -> int:
    if args.program:
        platform, _, program = args.program.partition("/")
        out = scan_bounty_program(platform=platform.lower(), program=program)
    else:
        out = run_bounty_hunter()
    print(json.dumps(out, indent=2, default=str))
    return 0


def _cmd_bootstrap(_: argparse.Namespace) -> int:
    """Spin up every always-on service of EmbodiedOS in background threads."""
    cfg = get_config()
    LOG.info("EmbodiedOS bootstrap — bridge=%s gateway+1=%s learning_interval=%ss",
             cfg.bridge.port, cfg.bridge.port + 1, cfg.learning.interval_s)

    threads: list[threading.Thread] = []

    # Skill sync (one-shot, then keep the engine warm)
    try:
        get_engine().sync()
    except Exception as exc:  # noqa: BLE001
        LOG.warning("initial skill sync failed: %s", exc)

    # Bridge MCP server (HTTP transport — easy for legacy + LSP clients)
    bt = threading.Thread(target=lambda: serve_bridge(transport="http"),
                          name="embodied-bridge-http", daemon=True)
    bt.start()
    threads.append(bt)

    # Unified gateway
    threads.append(serve_in_background())

    # Learning daemon
    threads.append(start_learning())

    LOG.info("EmbodiedOS bootstrap complete — %d background threads up.", len(threads))

    stop = threading.Event()

    def _on_signal(*_a: object) -> None:
        LOG.info("EmbodiedOS shutting down (signal received).")
        stop.set()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    while not stop.is_set():
        time.sleep(1.0)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("embodied", description="EmbodiedOS — Hermes Agent + OpenClaw fused into Rhodawk.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("bridge", help="Run the MCP bridge that exposes Rhodawk tools.")
    pb.add_argument("--http", action="store_true", help="HTTP transport instead of stdio.")
    pb.set_defaults(func=_cmd_bridge)

    pg = sub.add_parser("gateway", help="Run the unified HTTP gateway.")
    pg.add_argument("--host", default=None)
    pg.add_argument("--port", type=int, default=None)
    pg.set_defaults(func=_cmd_gateway)

    pl = sub.add_parser("learn", help="Run the continuous-learning daemon.")
    pl.add_argument("--once", action="store_true", help="Single tick, then exit.")
    pl.set_defaults(func=_cmd_learn)

    ps = sub.add_parser("sync-skills", help="Rebuild the unified skill catalogue.")
    ps.set_defaults(func=_cmd_sync_skills)

    p1 = sub.add_parser("side1", help="Run Side 1 on a single repo.")
    p1.add_argument("repo")
    p1.add_argument("--fix-only", action="store_true")
    p1.set_defaults(func=_cmd_side1)

    p2 = sub.add_parser("side2", help="Run Side 2 — one bounty cycle.")
    p2.add_argument("--program", default=None, help="<PLATFORM>/<handle>, e.g. HACKERONE/shopify")
    p2.set_defaults(func=_cmd_side2)

    pbo = sub.add_parser("bootstrap", help="Start every EmbodiedOS service (used by entrypoint.sh).")
    pbo.set_defaults(func=_cmd_bootstrap)

    return p


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        LOG.exception("embodied CLI crashed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
