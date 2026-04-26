#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Rhodawk runtime bootstrap.
#
# 1. Launch the camofox-browser anti-detection browser server on
#    127.0.0.1:9377.
# 2. Launch the OpenClaude headless gRPC daemons (do / or).
# 3. Launch Nous Research Hermes Agent on :11434.
# 4. Launch OpenClaw multi-channel gateway on :18789.
# 5. Bootstrap the EmbodiedOS bridge + unified gateway + continuous
#    learning daemon.
# 6. Hand off to app.py (Gradio + webhook + legacy stack).
# ─────────────────────────────────────────────────────────────────────
set -eo pipefail

OC_DIR=/opt/openclaude
CAMOFOX_DIR=/opt/camofox
HERMES_DIR="${HERMES_AGENT_HOME:-/opt/hermes-agent}"
OPENCLAW_DIR="${OPENCLAW_HOME:-/opt/openclaw}"
LOG_DIR="${LOG_DIR:-/tmp}"
mkdir -p "${LOG_DIR}"

# ─── camofox-browser ─────────────────────────────────────────────────
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

# ─── NEW: Nous Research Hermes Agent ─────────────────────────────────
start_hermes_agent() {
    local hermes_bin="${HERMES_DIR}/bin/hermes"
    if [[ ! -x "${hermes_bin}" ]]; then
        echo "[entrypoint] Hermes Agent binary not found at ${hermes_bin} — skipping"
        return 0
    fi
    echo "[entrypoint] starting Hermes Agent on :${HERMES_AGENT_PORT:-11434}"
    (
        # Hermes Agent uses the OpenAI-compatible API; set the provider vars.
        HERMES_AGENT_API_KEY="${HERMES_AGENT_API_KEY:-${OPENROUTER_API_KEY:-}}" \
        HERMES_AGENT_BASE_URL="${HERMES_AGENT_BASE_URL:-${OPENROUTER_BASE_URL:-}}" \
        HERMES_AGENT_MODEL="${HERMES_AGENT_MODEL:-${HERMES_MODEL:-}}" \
        HERMES_AGENT_PORT="${HERMES_AGENT_PORT:-11434}" \
        HERMES_MCP_CONFIG="${HERMES_MCP_CONFIG:-/tmp/mcp_runtime.embodied.json}" \
        HERMES_SKILLS_DIR="${HERMES_SKILLS_DIR:-${HOME}/.hermes/skills}" \
            "${hermes_bin}" agent start \
                --port "${HERMES_AGENT_PORT:-11434}" \
                --mcp-config "${HERMES_MCP_CONFIG:-/tmp/mcp_runtime.embodied.json}" \
                > "${LOG_DIR}/hermes-agent.log" 2>&1 &
        echo $! > "${LOG_DIR}/hermes-agent.pid"
    )
}

# ─── NEW: OpenClaw multi-channel gateway ─────────────────────────────
start_openclaw_gateway() {
    local openclaw_bin="${OPENCLAW_DIR}/bin/openclaw"
    if [[ ! -x "${openclaw_bin}" ]]; then
        # Fallback: try global npm binary
        if command -v openclaw >/dev/null 2>&1; then
            openclaw_bin=$(command -v openclaw)
        else
            echo "[entrypoint] OpenClaw binary not found — skipping"
            return 0
        fi
    fi
    echo "[entrypoint] starting OpenClaw gateway on :${OPENCLAW_GATEWAY_PORT:-18789}"
    (
        OPENCLAW_TOKEN="${OPENCLAW_TOKEN:-}" \
        OPENCLAW_MCP_CONFIG="${OPENCLAW_MCP_CONFIG:-/tmp/openclaw_mcp.embodied.json}" \
        OPENCLAW_SKILLS_DIR="${OPENCLAW_SKILLS_DIR:-${HOME}/.openclaw/skills}" \
            "${openclaw_bin}" gateway start \
                --port "${OPENCLAW_GATEWAY_PORT:-18789}" \
                --mcp-config "${OPENCLAW_MCP_CONFIG:-}" \
                > "${LOG_DIR}/openclaw.log" 2>&1 &
        echo $! > "${LOG_DIR}/openclaw.pid"
    )
}

# ─── ORDER OF OPERATIONS ─────────────────────────────────────────────

# 1. camofox (slowest, lazy engine download)
start_camofox

# 2. OpenClaude gRPC daemons (do / or)
export EXECUTION_MODEL="${EXECUTION_MODEL:-llama3.3-70b-instruct}"
export HERMES_MODEL="${HERMES_MODEL:-deepseek-r1-distill-llama-70b}"
export RECON_MODEL="${RECON_MODEL:-kimi-k2.5}"
export TRIAGE_MODEL="${TRIAGE_MODEL:-qwen3-32b}"
export FALLBACK_MODEL="${FALLBACK_MODEL:-claude-4.6-sonnet}"
export FALLBACK_MODEL_ALT="${FALLBACK_MODEL_ALT:-minimax-m2.5}"

DO_BASE="${DO_INFERENCE_BASE_URL:-https://inference.do-ai.run/v1}"
DO_MODEL="${DO_INFERENCE_MODEL:-${EXECUTION_MODEL}}"
start_daemon "do" 50051 "${DO_BASE}" \
    "${DO_INFERENCE_API_KEY:-${DIGITALOCEAN_INFERENCE_KEY:-}}" \
    "${DO_MODEL}"

OR_BASE="${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}"
OR_MODEL="${OPENROUTER_MODEL:-meta-llama/llama3.3-70b-instruct}"
start_daemon "or" 50052 "${OR_BASE}" "${OPENROUTER_API_KEY:-}" "${OR_MODEL}"

sleep 2

# 3. Hermes Agent
start_hermes_agent

# 4. OpenClaw Gateway
start_openclaw_gateway

# Let them bind before the bridge tries to connect
sleep 2

# 5. G0DM0D3 Meta-Learner Daemon (legacy)
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

# 6. EmbodiedOS unified bootstrap (bridge, gateway, research)
export OPENCLAW="${OPENCLAW:-1}"

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
