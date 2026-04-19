# Stage 1: Builder
FROM python:3.12-slim AS base

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

# Install dependencies directly — avoids wheel-build failures for packages
# that require special compile-time tooling (e.g. atheris/libFuzzer).
# atheris has been removed from requirements.txt; Hypothesis is the fallback.
RUN pip install --no-cache-dir -r requirements.txt mcp-server-fetch


# Stage 2: Runtime — inherits installed packages from base
FROM base AS runtime

LABEL org.opencontainers.image.title="Rhodawk AI DevSecOps Engine"

ENV GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    HOME=/home/rhodawk \
    PATH="/home/rhodawk/.local/bin:/usr/local/bin:$PATH" \
    UV_PYTHON_PREFERENCE=system \
    UV_PYTHON=/usr/local/bin/python3

RUN apt-get update && \
    apt-get install -y --no-install-recommends nodejs npm && \
    rm -rf /var/lib/apt/lists/*

RUN npm install -g --quiet @modelcontextprotocol/server-github

# Hugging Face UID 1000 handling
RUN id -u 1000 >/dev/null 2>&1 && (userdel -r $(id -un 1000) || true) || true && \
    useradd -m -u 1000 -s /bin/bash rhodawk

# FIX: create /data with explicit mode so uv venv can write target_venv
# even before the application calls os.makedirs() at runtime.
RUN mkdir -p /data /app && chmod 777 /data && chown -R rhodawk:rhodawk /app

# Copy the uv executable from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
USER rhodawk

# Copy the source code
COPY --chown=rhodawk:rhodawk . .

EXPOSE 7860

CMD ["python", "-u", "app.py"]