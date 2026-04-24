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

# DigitalOcean Inference (PRIMARY)
DO_BASE="${DO_INFERENCE_BASE_URL:-https://inference.do-ai.run/v1}"
DO_MODEL="${DO_INFERENCE_MODEL:-llama3.3-70b-instruct}"
start_daemon "do" 50051 "${DO_BASE}" \
    "${DO_INFERENCE_API_KEY:-${DIGITALOCEAN_INFERENCE_KEY:-}}" \
    "${DO_MODEL}"

# OpenRouter (FALLBACK)
OR_BASE="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
OR_MODEL="${OPENROUTER_MODEL:-qwen/qwen-2.5-coder-32b-instruct:free}"
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

echo "[entrypoint] launching Rhodawk orchestrator…"
exec python -u app.py
