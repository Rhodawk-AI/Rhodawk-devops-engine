FROM python:3.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl ca-certificates build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s $HOME/.local/bin/uv /usr/local/bin/uv

WORKDIR /build
COPY requirements.txt .
# uv will automatically handle the conflict resolution better than pip
RUN uv pip install --system --no-cache -r requirements.txt mcp-server-fetch && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt mcp-server-fetch

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Rhodawk AI DevSecOps Engine v4.0"
LABEL org.opencontainers.image.description="Autonomous CI/CD healing, red-team CEGIS, SAST, supply-chain gate, SWE-bench, and data flywheel"
LABEL org.opencontainers.image.version="4.0.0"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git curl ca-certificates build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    curl -LsSf https://astral.sh/uv/install.sh | env HOME=/root sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

RUN npm install -g --quiet @modelcontextprotocol/server-github

RUN userdel -r node 2>/dev/null || true && \
    useradd -m -u 1000 -s /bin/bash rhodawk

RUN mkdir -p /data /app && chown -R rhodawk:rhodawk /data /app

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

ENV HOME=/home/rhodawk
ENV PATH=$HOME/.local/bin:/usr/local/bin:$PATH

USER rhodawk

COPY --chown=rhodawk:rhodawk *.py mcp_config.json ./

EXPOSE 7860 7861

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

CMD ["python", "-u", "app.py"]
