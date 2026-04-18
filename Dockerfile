# Stage 1: Builder
FROM python:3.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl ca-certificates build-essential && \
    rm -rf /var/lib/apt/lists/*

# Use the official Astral image for a complete, clean uv installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build
COPY requirements.txt .

# FIX: only build wheels here — do NOT also run uv pip install --system.
# The previous double-install (uv pip install --system AND pip wheel) was
# redundant and could produce conflicting bytecode in the builder layer.
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt mcp-server-fetch


# Stage 2: Runtime
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Rhodawk AI DevSecOps Engine"

# FIX: UV_PYTHON now points to python3 (always present in python:3.12-slim)
# rather than /usr/local/bin/python which may lack the executable in some
# HuggingFace Space runtime snapshots. UV_PYTHON_PREFERENCE=system tells uv
# to skip its managed-toolchain download and use the container Python directly.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    HOME=/home/rhodawk \
    PATH="/home/rhodawk/.local/bin:/usr/local/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=system \
    UV_PYTHON=/usr/local/bin/python3

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl ca-certificates nodejs npm && \
    rm -rf /var/lib/apt/lists/*

RUN npm install -g --quiet @modelcontextprotocol/server-github

# Hugging Face UID 1000 handling
RUN id -u 1000 >/dev/null 2>&1 && (userdel -r $(id -un 1000) || true) || true && \
    useradd -m -u 1000 -s /bin/bash rhodawk

# FIX: create /data with explicit mode so uv venv can write target_venv
# even before the application calls os.makedirs() at runtime.
RUN mkdir -p /data /app && chmod 777 /data && chown -R rhodawk:rhodawk /app

WORKDIR /app

# Copy pre-built wheels from builder
COPY --from=builder /wheels /wheels

# Copy the uv executable from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

USER rhodawk

# Copy the source code
COPY --chown=rhodawk:rhodawk . .

EXPOSE 7860

CMD ["python", "-u", "app.py"]