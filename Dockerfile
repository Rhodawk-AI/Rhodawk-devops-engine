# syntax=docker/dockerfile:1.7
# ─────────────────────────────────────────────────────────────────────────
# Rhodawk AI DevSecOps Engine — vendored OpenClaude architecture
#
# Stages:
#   1. openclaude-builder  — uses Bun to compile vendor/openclaude → dist/cli.mjs
#   2. base                — python:3.12-slim with system tooling, uv, Node, Bun
#   3. runtime             — final image (non-root rhodawk user, EXPOSE 7860)
#
# Aider, litellm, configargparse and friends have been completely removed.
# Code generation is now handled by the OpenClaude headless gRPC daemon
# launched from entrypoint.sh.
# ─────────────────────────────────────────────────────────────────────────

ARG BUN_VERSION=1.1.42

# ─── Stage 1: build the vendored OpenClaude bundle ──────────────────────
FROM oven/bun:${BUN_VERSION} AS openclaude-builder
WORKDIR /openclaude
COPY vendor/openclaude/package.json vendor/openclaude/bun.lock ./
RUN bun install --frozen-lockfile --no-progress
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
    && rm -rf /var/lib/apt/lists/*

# uv (fast Python installer used by sandboxed test runs)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Bun (needed at runtime to launch the daemon: `bun run dev:grpc`)
COPY --from=oven/bun:1.1.42 /usr/local/bin/bun /usr/local/bin/bun
COPY --from=oven/bun:1.1.42 /usr/local/bin/bunx /usr/local/bin/bunx

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt mcp-server-fetch \
                grpcio==1.66.* grpcio-tools==1.66.* protobuf==5.*

# MCP servers used by the runtime — installed globally so `npx -y …` is
# instantaneous instead of resolving on every audit.
RUN npm install -g --quiet \
        @modelcontextprotocol/server-github \
        @modelcontextprotocol/server-filesystem \
        @modelcontextprotocol/server-memory \
        @modelcontextprotocol/server-sequential-thinking \
        @modelcontextprotocol/server-git \
        @modelcontextprotocol/server-sqlite \
        @modelcontextprotocol/server-brave-search

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
    MCP_RUNTIME_CONFIG=/tmp/mcp_runtime.json

# HuggingFace UID 1000 handling (idempotent)
RUN id -u 1000 >/dev/null 2>&1 && (userdel -r "$(id -un 1000)" || true) || true && \
    useradd -m -u 1000 -s /bin/bash rhodawk

RUN mkdir -p /data /app /opt/openclaude && \
    chmod 777 /data && \
    chown -R rhodawk:rhodawk /app /opt/openclaude

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

EXPOSE 7860 50051 50052

ENTRYPOINT ["/app/entrypoint.sh"]
