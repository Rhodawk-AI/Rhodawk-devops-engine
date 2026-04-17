# Stage 1: Builder
FROM python:3.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl ca-certificates build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast, conflict-free dependency resolution
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /build
COPY requirements.txt .

# Fix: Using 'uv' to resolve and pre-build wheels
RUN uv pip install --no-cache --system wheel && \
    uv pip wheel --no-cache -r requirements.txt mcp-server-fetch --wheel-dir /wheels

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Rhodawk AI DevSecOps Engine"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    HOME=/home/rhodawk \
    PATH="/home/rhodawk/.local/bin:/usr/local/bin:$PATH"

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl ca-certificates nodejs npm && \
    rm -rf /var/lib/apt/lists/*

RUN npm install -g --quiet @modelcontextprotocol/server-github

# Fix: Hugging Face specific UID 1000 handling
RUN id -u 1000 >/dev/null 2>&1 && (userdel -r $(id -un 1000) || true) || true && \
    useradd -m -u 1000 -s /bin/bash rhodawk

RUN mkdir -p /data /app && chown -R rhodawk:rhodawk /data /app

WORKDIR /app

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

USER rhodawk

# Copy application files (Ensure mcp_config.json is in your Space's file list)
COPY --chown=rhodawk:rhodawk . .

EXPOSE 7860

CMD ["python", "-u", "app.py"]