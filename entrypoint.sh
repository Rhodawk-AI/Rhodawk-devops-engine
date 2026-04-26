#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Rhodawk runtime bootstrap.
#
# 1. Launch the camofox-browser anti-detection browser server on
#    127.0.0.1:9377 (used by the orchestrator via camofox_client.py).
# 2. Launch the OpenClaude headless gRPC daemon for the DigitalOcean
#    Inference provider on :50051 (PRIMARY).
# 3. Launch the OpenClaude headless gRPC daemon for OpenRouter on
#    :50052 (FALLBACK) — only if OPENROUTER_API_KEY is present.
# 4. Wait briefly for everything to bind, then hand control to app.py
#    which talks to them over gRPC + HTTP.
# ─────────────────────────────────────────────────────────────────────
set -eo pipefail

OC_DIR=/opt/openclaude
CAMOFOX_DIR=/opt/camofox
LOG_DIR="${LOG_DIR:-/tmp}"
mkdir -p "${LOG_DIR}"

# ─── camofox-browser ─────────────────────────────────────────────────
# Anti-detection Firefox-fork browser server.  Lazily downloads the
# Camoufox engine (~300MB) on first launch into the user's home dir,
# so the first start may take a minute.  Subsequent starts are fast.
start_camofox() {
    local entry="${CAMOFOX_DIR}/node_modules/@askjo/camofox-browser/server.js"
    [[ -f "${entry}" ]] || entry="${CAMOFOX_DIR}/node_modules/camofox-browser/server.js"
    if [[ ! -f "${entry}" ]]; then
        echo "[entrypoint] camofox-browser not installed — skipping"
        return 0
    fi
    echo "[entrypoint] starting camofox-browser on ${CAMOFOX_HOST:-127.0.0.1}:${CAMOFOX_PORT:-9377}"
    (
        cd "${CAMOFOX_DIR}"
        PORT="${CAMOFOX_PORT:-9377}" \
        HOST="${CAMOFOX_HOST:-127.0.0.1}" \
        CAMOFOX_HEADLESS="${CAMOFOX_HEADLESS:-virtual}" \
        CAMOFOX_PROFILE_DIR="${CAMOFOX_PROFILE_DIR:-/data/camofox/profiles}" \
        CAMOFOX_COOKIES_DIR="${CAMOFOX_COOKIES_DIR:-/data/camofox/cookies}" \
        CAMOFOX_API_KEY="${CAMOFOX_API_KEY:-}" \
        PROXY_HOST="${PROXY_HOST:-}" \
        PROXY_PORT="${PROXY_PORT:-}" \
        PROXY_USERNAME="${PROXY_USERNAME:-}" \
        PROXY_PASSWORD="${PROXY_PASSWORD:-}" \
            node "${entry}" \
                > "${LOG_DIR}/camofox.log" 2>&1 &
        echo $! > "${LOG_DIR}/camofox.pid"
    )
}

start_daemon() {
    local label=$1 port=$2 base_url=$3 api_key=$4 model=$5
    if [[ -z "${api_key}" ]]; then
        echo "[entrypoint] skipping ${label} daemon — no API key"
        return 0
    fi
    echo "[entrypoint] starting OpenClaude ${label} daemon on :${port}"
    (
        cd "${OC_DIR}"
        CLAUDE_CODE_USE_OPENAI=1 \
        OPENAI_API_KEY="${api_key}" \
        OPENAI_BASE_URL="${base_url}" \
        OPENAI_MODEL="${model}" \
        GRPC_PORT="${port}" \
        GRPC_HOST=0.0.0.0 \
        OPENCLAUDE_AUTO_APPROVE=1 \
        MCP_RUNTIME_CONFIG="${MCP_RUNTIME_CONFIG:-/tmp/mcp_runtime.json}" \
            bun run scripts/start-grpc.ts \
                > "${LOG_DIR}/openclaude-${label}.log" 2>&1 &
        echo $! > "${LOG_DIR}/openclaude-${label}.pid"
    )
}

# camofox first — slowest to bind because of the lazy engine download.
start_camofox

# ─── THE MODEL SQUAD (DigitalOcean primary, OpenRouter fallback) ─────
# 1. The Hands       (EXECUTION) — primary executor / patch generation
# 2. The Brain       (HERMES)    — reasoning + Godmode meta-learning
# 3. The Reader      (RECON)     — massive context ingestion (OR-only today)
# 4. The Screener    (TRIAGE)    — fast cheap filtering
# 5. The Safety Net  (FALLBACK)  — emergency tier (OR-only)
# Override any of these via the container env to swap models.
export EXECUTION_MODEL="${EXECUTION_MODEL:-llama3.3-70b-instruct}"
export HERMES_MODEL="${HERMES_MODEL:-deepseek-r1-distill-llama-70b}"
export RECON_MODEL="${RECON_MODEL:-kimi-k2.5}"
export TRIAGE_MODEL="${TRIAGE_MODEL:-qwen3-32b}"
export FALLBACK_MODEL="${FALLBACK_MODEL:-claude-4.6-sonnet}"
export FALLBACK_MODEL_ALT="${FALLBACK_MODEL_ALT:-minimax-m2.5}"

# DigitalOcean Inference (PRIMARY) — drives the OpenClaude :50051 daemon
DO_BASE="${DO_INFERENCE_BASE_URL:-https://inference.do-ai.run/v1}"
DO_MODEL="${DO_INFERENCE_MODEL:-${EXECUTION_MODEL}}"
start_daemon "do" 50051 "${DO_BASE}" \
    "${DO_INFERENCE_API_KEY:-${DIGITALOCEAN_INFERENCE_KEY:-}}" \
    "${DO_MODEL}"

# OpenRouter (FALLBACK) — drives the OpenClaude :50052 daemon (optional)
OR_BASE="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
OR_MODEL="${OPENROUTER_MODEL:-meta-llama/llama3.3-70b-instruct}"
start_daemon "or" 50052 "${OR_BASE}" "${OPENROUTER_API_KEY:-}" "${OR_MODEL}"

# Brief settle window so the first healing call doesn't race the binder.
# The Python client also has wait_ready() so this is just a friendly nudge.
sleep 2

# ─── G0DM0D3 Meta-Learner Daemon ─────────────────────────────────────
# Self-bootstrapping meta-learning loop.  Runs in the background, in
# parallel with app.py — it never blocks the Gradio UI or the GitHub
# webhook listener.  Output is tee-d to ${LOG_DIR}/meta_learner.log
# so it can be tailed via `docker logs -f` *and* persisted to disk.
if [[ "${META_LEARNER_ENABLED:-1}" == "1" ]]; then
    echo "[entrypoint] starting G0DM0D3 meta_learner_daemon.py in background"
    (
        LOG_DIR="${LOG_DIR}" \
        MCP_RUNTIME_CONFIG="${MCP_RUNTIME_CONFIG:-/tmp/mcp_runtime.json}" \
        CAMOFOX_HOST="${CAMOFOX_HOST:-127.0.0.1}" \
        CAMOFOX_PORT="${CAMOFOX_PORT:-9377}" \
            python -u meta_learner_daemon.py \
                > "${LOG_DIR}/meta_learner.log" 2>&1 &
        echo $! > "${LOG_DIR}/meta_learner.pid"
    )
else
    echo "[entrypoint] META_LEARNER_ENABLED=0 — skipping meta-learner daemon"
fi

# EmbodiedOS = Hermes + OpenClaw unified front-of-house.  app.py already
# wires the OpenClaw HTTP gateway behind OPENCLAW=1; we default it ON so
# the unified NL command surface (POST /openclaw/command + Telegram
# webhook + the new mission_repo / mission_bounty intents registered by
# embodied_os.py) is live as soon as the container is up.
export OPENCLAW="${OPENCLAW:-1}"

# ─── EmbodiedOS bootstrap (sections 4.1 – 4.7) ───────────────────────
# Spins up the new ``embodied`` package's three always-on services in
# background threads inside a single Python process:
#
#   • MCP bridge       (HTTP, default :8600)  — exposes Rhodawk tools
#                                                to Hermes Agent + OpenClaw.
#   • Unified gateway  (HTTP, default :8601)  — Telegram / Discord /
#                                                Slack / OpenClaw / direct.
#   • Research daemon  (continuous)           — fetches CVEs / writeups
#                                                and auto-distils them
#                                                into agentskills.io skills.
#
# Disable any of these via the matching env flag (see .env.example).
if [[ "${EMBODIED_OS_ENABLED:-1}" == "1" ]]; then
    echo "[entrypoint] starting EmbodiedOS bootstrap (bridge + gateway + learner)…"
    (
        LOG_DIR="${LOG_DIR}" \
        EMBODIED_BRIDGE_HOST="${EMBODIED_BRIDGE_HOST:-127.0.0.1}" \
        EMBODIED_BRIDGE_PORT="${EMBODIED_BRIDGE_PORT:-8600}" \
        EMBODIED_BRIDGE_TRANSPORT="${EMBODIED_BRIDGE_TRANSPORT:-http}" \
        EMBODIED_BRIDGE_SECRET="${EMBODIED_BRIDGE_SECRET:-}" \
        HERMES_AGENT_URL="${HERMES_AGENT_URL:-http://127.0.0.1:8400}" \
        HERMES_AGENT_API_KEY="${HERMES_AGENT_API_KEY:-}" \
        HERMES_SKILLS_DIR="${HERMES_SKILLS_DIR:-${HOME}/.hermes/skills}" \
        OPENCLAW_BASE_URL="${OPENCLAW_BASE_URL:-http://127.0.0.1:8500}" \
        OPENCLAW_API_KEY="${OPENCLAW_API_KEY:-}" \
        OPENCLAW_SKILLS_DIR="${OPENCLAW_SKILLS_DIR:-${HOME}/.openclaw/skills}" \
        EMBODIED_SKILL_CACHE="${EMBODIED_SKILL_CACHE:-/tmp/embodied_skill_cache}" \
        EMBODIED_EPISODIC_DB="${EMBODIED_EPISODIC_DB:-/data/embodied_episodic.sqlite}" \
        EMBODIED_LEARNING_ENABLED="${EMBODIED_LEARNING_ENABLED:-1}" \
        EMBODIED_AUTOSUBMIT="${EMBODIED_AUTOSUBMIT:-0}" \
            python -u -m embodied bootstrap \
                > "${LOG_DIR}/embodied_os.log" 2>&1 &
        echo $! > "${LOG_DIR}/embodied_os.pid"
    )

    # Emit fresh MCP registration files so Hermes Agent + OpenClaw can
    # discover the bridge on their next reconnect.  Best-effort.
    python -u -c "from embodied.bridge.mcp_server import build_server; \
                  s = build_server(); \
                  s.emit_hermes_registration('/tmp/mcp_runtime.embodied.json'); \
                  s.emit_openclaw_registration('/tmp/openclaw_mcp.embodied.json')" \
        2>>"${LOG_DIR}/embodied_os.log" || true
else
    echo "[entrypoint] EMBODIED_OS_ENABLED=0 — EmbodiedOS bootstrap skipped"
fi

echo "[entrypoint] launching Rhodawk orchestrator (EmbodiedOS=on)…"
exec python -u app.py
