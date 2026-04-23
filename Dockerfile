ARG BUN_VERSION=latest

# ─── Stage 1: build the vendored OpenClaude bundle ──────────────────────
FROM oven/bun:${BUN_VERSION} AS openclaude-builder
WORKDIR /openclaude
# FIX: Ignored bun.lock and removed --frozen-lockfile to prevent version mismatch crashes
COPY vendor/openclaude/package.json ./
RUN bun install --no-progress
COPY vendor/openclaude/ ./
RUN bun run build && \
    test -s dist/cli.mjs && \
    echo "[builder] OpenClaude bundle: $(wc -c < dist/cli.mjs) bytes"

# ─── Stage 2: base python+node+bun runtime ──────────────────────────────
FROM python:3.12-slim AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates build-essential unzip xz-utils \
        nodejs npm \
        # ─── camofox-browser runtime deps ────────────────────────────
        # Camoufox is a Firefox fork; it needs the standard X/GTK
        # display libraries even when running headless, plus xvfb so
        # we can attach a virtual display when --headless=virtual.
        xvfb libgtk-3-0 libdbus-glib-1-2 libxt6 libasound2 \
        libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 \
        libxi6 libxrandr2 libxss1 libxtst6 libnss3 libpango-1.0-0 \
        libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# uv (fast Python installer used by sandboxed test runs)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Bun (needed at runtime to launch the daemon: `bun run dev:grpc`)
# FIX: Updated to pull from latest to match Stage 1
COPY --from=oven/bun:latest /usr/local/bin/bun /usr/local/bin/bun
COPY --from=oven/bun:latest /usr/local/bin/bunx /usr/local/bin/bunx

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
                mcp-server-fetch mcp-server-git mcp-server-sqlite \
                grpcio==1.66.* grpcio-tools==1.66.* protobuf==5.*

# MCP servers used by the runtime — installed globally so `npx -y …` is
# instantaneous instead of resolving on every audit.
# NOTE: `@modelcontextprotocol/server-git` and `@modelcontextprotocol/server-sqlite`
# were removed from the npm registry (404) — they are now provided via the
# Python packages `mcp-server-git` and `mcp-server-sqlite` installed above.
RUN npm install -g --quiet \
        @modelcontextprotocol/server-github \
        @modelcontextprotocol/server-filesystem \
        @modelcontextprotocol/server-memory \
        @modelcontextprotocol/server-sequential-thinking \
        @modelcontextprotocol/server-brave-search

# ─── camofox-browser anti-detection browser server ──────────────────────
# Anti-detection browser for AI agents (https://github.com/jo-inc/camofox-browser).
# Installed under /opt/camofox so the orchestrator can launch it via
# entrypoint.sh on 127.0.0.1:9377.  The Camoufox Firefox-fork binary
# (~300MB) is fetched lazily on first launch by camoufox-js — keeping
# the image slim while still giving the orchestrator full access to the
# REST API exposed by camofox_client.py.
RUN mkdir -p /opt/camofox && cd /opt/camofox && \
    npm init -y >/dev/null 2>&1 && \
    npm install --quiet --omit=dev @askjo/camofox-browser@^1.6.0 || \
    npm install --quiet --omit=dev camofox-browser

# ─── Stage 3: final runtime image ───────────────────────────────────────
FROM base AS runtime
LABEL org.opencontainers.image.title="Rhodawk AI DevSecOps Engine" \
      org.opencontainers.image.source="https://github.com/Rhodawk-AI/Rhodawk-devops-engine"

ENV GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    HOME=/home/rhodawk \
    PATH="/home/rhodawk/.local/bin:/usr/local/bin:$PATH" \
    UV_PYTHON_PREFERENCE=system \
    UV_PYTHON=/usr/local/bin/python3 \
    OPENCLAUDE_AUTO_APPROVE=1 \
    OPENCLAUDE_GRPC_HOST=127.0.0.1 \
    OPENCLAUDE_GRPC_PORT_DO=50051 \
    OPENCLAUDE_GRPC_PORT_OR=50052 \
    MCP_RUNTIME_CONFIG=/tmp/mcp_runtime.json \
    # ─── camofox-browser runtime defaults ────────────────────────────
    # The orchestrator talks to the local camofox server through
    # camofox_client.py.  CAMOFOX_API_KEY gates cookie-import — leave
    # it unset to keep cookie writes disabled (server returns 403).
    CAMOFOX_BASE_URL=http://127.0.0.1:9377 \
    CAMOFOX_PORT=9377 \
    CAMOFOX_HOST=127.0.0.1 \
    CAMOFOX_HEADLESS=virtual \
    CAMOFOX_PROFILE_DIR=/data/camofox/profiles \
    CAMOFOX_COOKIES_DIR=/data/camofox/cookies

# HuggingFace UID 1000 handling (idempotent)
RUN id -u 1000 >/dev/null 2>&1 && (userdel -r "$(id -un 1000)" || true) || true && \
    useradd -m -u 1000 -s /bin/bash rhodawk

RUN mkdir -p /data /data/camofox/profiles /data/camofox/cookies /app /opt/openclaude && \
    chmod -R 777 /data && \
    chown -R rhodawk:rhodawk /app /opt/openclaude /opt/camofox

# Bring the prebuilt OpenClaude bundle in as a vendored artifact.
COPY --from=openclaude-builder --chown=rhodawk:rhodawk /openclaude /opt/openclaude

# Tiny global wrappers — the orchestrator never shells out to these
# directly any more (gRPC bridges everything), but we keep them so admins
# can debug interactively from `docker exec`.
RUN ln -sf /opt/openclaude/bin/openclaude /usr/local/bin/openclaude && \
    chmod +x /usr/local/bin/openclaude

WORKDIR /app
USER rhodawk

# Source last so application edits don't bust the heavy node/python layers.
COPY --chown=rhodawk:rhodawk . .

# Generate Python protobuf stubs from the vendored .proto file.
RUN python -m grpc_tools.protoc \
        -I /opt/openclaude/src/proto \
        --python_out=openclaude_grpc \
        --grpc_python_out=openclaude_grpc \
        /opt/openclaude/src/proto/openclaude.proto && \
    # protoc emits absolute-path imports; rewrite for relative package layout
    sed -i 's/^import openclaude_pb2/from . import openclaude_pb2/' \
        openclaude_grpc/openclaude_pb2_grpc.py

EXPOSE 7860 9377 50051 50052

ENTRYPOINT ["/app/entrypoint.sh"]
