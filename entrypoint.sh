#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Rhodawk runtime bootstrap.
#
# 1. Launch the OpenClaude headless gRPC daemon for the DigitalOcean
#    Inference provider on :50051 (PRIMARY).
# 2. Launch the OpenClaude headless gRPC daemon for OpenRouter on
#    :50052 (FALLBACK) — only if OPENROUTER_API_KEY is present.
# 3. Wait briefly for both to bind, then hand control to app.py which
#    talks to them over gRPC.
# ─────────────────────────────────────────────────────────────────────
set -eo pipefail

OC_DIR=/opt/openclaude
LOG_DIR="${LOG_DIR:-/tmp}"
mkdir -p "${LOG_DIR}"

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
echo "[entrypoint] launching Rhodawk orchestrator…"
exec python -u app.py
