# Stage 1: Builder
FROM python:3.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl ca-certificates build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast, conflict-free resolution
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /build
COPY requirements.txt .

# FIX: Use uv to resolve the entire requirements tree at once.
# This prevents the "ResolutionImpossible" error by finding the 
# valid intersection between Gradio 5 and Aider-chat.
RUN uv pip install --no-cache --system -r requirements.txt mcp-server-fetch && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt mcp-server-fetch


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

# Fix: Hugging Face UID 1000 handling
RUN id -u 1000 >/dev/null 2>&1 && (userdel -r $(id -un 1000) || true) || true && \
    useradd -m -u 1000 -s /bin/bash rhodawk

RUN mkdir -p /data /app && chown -R rhodawk:rhodawk /data /app

WORKDIR /app

# Copy pre-built wheels from builder
COPY --from=builder /wheels /wheels

# ADDED FIX: Copy the uv executable from the builder stage
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

USER rhodawk

# Copy the source code
COPY --chown=rhodawk:rhodawk . .

EXPOSE 7860

CMD ["python", "-u", "app.py"]