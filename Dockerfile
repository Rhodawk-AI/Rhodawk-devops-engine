ARG BUN_VERSION=latest

# ─── Stage 1: build the vendored OpenClaude bundle ──────────────────────
FROM oven/bun:${BUN_VERSION} AS openclaude-builder
WORKDIR /openclaude
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
        git curl wget ca-certificates build-essential unzip xz-utils \
        nodejs npm \
        # ─── Gap 2 (Coverage-Guided Fuzzing): AFL++ + Clang/LLD/LLVM ──
        afl++ afl++-clang clang lld llvm \
        # ─── Gap 4 (Binary Exploitation): Ghidra 11.x runtime deps ──
        # OpenJDK is required by Ghidra's analyzeHeadless launcher.
        openjdk-17-jre-headless \
        # ─── camofox-browser runtime deps ────────────────────────────
        xvfb libgtk-3-0 libdbus-glib-1-2 libxt6 libasound2 \
        libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 \
        libxi6 libxrandr2 libxss1 libxtst6 libnss3 libpango-1.0-0 \
        libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# ─── Gap 4 (Binary Exploitation): Ghidra 11.x headless ───────────────────
# Pinned release; the official ZIP unpacks into ghidra_<ver>_PUBLIC/ which
# we symlink to /opt/ghidra so analyzeHeadless lives at a stable path.
ARG GHIDRA_VERSION=11.1.2
ARG GHIDRA_BUILD=20240709
RUN curl -fsSL -o /tmp/ghidra.zip \
      "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_${GHIDRA_VERSION}_build/ghidra_${GHIDRA_VERSION}_PUBLIC_${GHIDRA_BUILD}.zip" \
 && unzip -q /tmp/ghidra.zip -d /opt \
 && ln -sfn "/opt/ghidra_${GHIDRA_VERSION}_PUBLIC" /opt/ghidra \
 && chmod -R a+rX /opt/ghidra/ \
 && rm /tmp/ghidra.zip \
 && mkdir -p /data/ghidra_projects /data/binary_reports \
 && chmod -R a+rwX /data/ghidra_projects /data/binary_reports
ENV GHIDRA_INSTALL_DIR=/opt/ghidra \
    GHIDRA_HEADLESS=/opt/ghidra/support/analyzeHeadless \
    GHIDRA_PROJECT_DIR=/data/ghidra_projects \
    ANGR_TIMEOUT=600 \
    BINARY_ENGINE_OUT=/data/binary_reports

# ─── Gap 7 (SBOM / SCA): syft + grype + osv-scanner + trivy ──────────────
# All four are statically-linked Go binaries pulled from official release
# channels. Versions pinned for reproducibility; bump in sync with the
# upstream advisories.
ARG SYFT_VERSION=1.14.0
ARG GRYPE_VERSION=0.79.6
ARG OSV_VERSION=1.8.5
ARG TRIVY_VERSION=0.55.2
RUN set -eux; \
    curl -fsSL "https://raw.githubusercontent.com/anchore/syft/main/install.sh"  | sh -s -- -b /usr/local/bin "v${SYFT_VERSION}";  \
    curl -fsSL "https://raw.githubusercontent.com/anchore/grype/main/install.sh" | sh -s -- -b /usr/local/bin "v${GRYPE_VERSION}"; \
    curl -fsSL -o /usr/local/bin/osv-scanner \
      "https://github.com/google/osv-scanner/releases/download/v${OSV_VERSION}/osv-scanner_linux_amd64"; \
    chmod +x /usr/local/bin/osv-scanner; \
    curl -fsSL -o /tmp/trivy.tgz \
      "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"; \
    tar -xzf /tmp/trivy.tgz -C /usr/local/bin trivy; \
    rm /tmp/trivy.tgz; \
    mkdir -p /data/sbom; \
    chmod -R a+rwX /data/sbom
ENV SYFT_BIN=/usr/local/bin/syft \
    GRYPE_BIN=/usr/local/bin/grype \
    OSV_BIN=/usr/local/bin/osv-scanner \
    TRIVY_BIN=/usr/local/bin/trivy \
    SCA_TIMEOUT=600 \
    SBOM_OUT_DIR=/data/sbom

# ─── Gap 9 (CI/CD Pentest Gate): nuclei + ffuf + nuclei-templates ────────
ARG NUCLEI_VERSION=3.3.0
ARG FFUF_VERSION=2.1.0
RUN set -eux; \
    curl -fsSL -o /tmp/nuclei.zip \
      "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip"; \
    unzip -q /tmp/nuclei.zip -d /tmp/nuclei && mv /tmp/nuclei/nuclei /usr/local/bin/nuclei; \
    chmod +x /usr/local/bin/nuclei; \
    rm -rf /tmp/nuclei /tmp/nuclei.zip; \
    curl -fsSL -o /tmp/ffuf.tgz \
      "https://github.com/ffuf/ffuf/releases/download/v${FFUF_VERSION}/ffuf_${FFUF_VERSION}_linux_amd64.tar.gz"; \
    tar -xzf /tmp/ffuf.tgz -C /usr/local/bin ffuf; \
    chmod +x /usr/local/bin/ffuf; \
    rm /tmp/ffuf.tgz; \
    git clone --depth=1 https://github.com/projectdiscovery/nuclei-templates.git /opt/nuclei-templates; \
    mkdir -p /opt/wordlists /data/cicd_reports; \
    curl -fsSL -o /opt/wordlists/common.txt \
      https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt; \
    chmod -R a+rX /opt/nuclei-templates /opt/wordlists; \
    chmod -R a+rwX /data/cicd_reports
ENV NUCLEI_BIN=/usr/local/bin/nuclei \
    NUCLEI_TEMPLATES_DIR=/opt/nuclei-templates \
    FFUF_BIN=/usr/local/bin/ffuf \
    FFUF_WORDLIST=/opt/wordlists/common.txt \
    CICD_PENTEST_TIMEOUT=600 \
    CICD_REPORT_DIR=/data/cicd_reports

# ─── Gap 15 (OSS-Fuzz pipeline) data dirs ────────────────────────────────
RUN mkdir -p /data/oss_fuzz_submissions \
 && chmod -R a+rwX /data/oss_fuzz_submissions
ENV OSS_FUZZ_OUT_DIR=/data/oss_fuzz_submissions \
    OSS_FUZZ_DB=/data/oss_fuzz_submissions.sqlite \
    OSS_FUZZ_BASE_BRANCH=master

# ─── Gap 1 (SAST Engine): CodeQL CLI + security query packs ──────────────
RUN curl -fsSL -o /tmp/codeql.zip \
      https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip \
 && unzip -q /tmp/codeql.zip -d /opt \
 && rm /tmp/codeql.zip \
 && /opt/codeql/codeql pack download \
      codeql/python-queries \
      codeql/javascript-queries \
      codeql/java-queries \
      codeql/cpp-queries \
      codeql/go-queries \
 && mkdir -p /data/codeql_dbs \
 && chmod -R a+rX /opt/codeql /data/codeql_dbs
ENV CODEQL_BIN=/opt/codeql/codeql \
    SEMGREP_BIN=semgrep \
    CODEQL_DB_DIR=/data/codeql_dbs \
    SAST_TIMEOUT_SECONDS=600

# ─── Gap 2 (Coverage-Guided Fuzzing): AFL++ env + corpus dirs ────────────
RUN mkdir -p /data/fuzz_corpus /data/fuzz_findings \
 && chmod -R a+rwX /data/fuzz_corpus /data/fuzz_findings
ENV AFL_BIN=afl-fuzz \
    AFL_CC=afl-clang-fast \
    FUZZ_TIMEOUT_SECONDS=1800 \
    FUZZ_CORPUS_DIR=/data/fuzz_corpus \
    FUZZ_FINDINGS_DIR=/data/fuzz_findings

# ─── Gap 5 (Threat Graph): MITRE ATT&CK enterprise STIX 2.1 bundle ───────
# Downloaded once at image build time so the runtime ATTCKMapper never
# pays a network cost. Falls back to the built-in CWE → technique table
# at runtime if the file is missing.
RUN mkdir -p /opt/mitre \
 && curl -fsSL -o /opt/mitre/enterprise-attack.json \
      https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json \
 && chmod -R a+rX /opt/mitre
ENV MITRE_ATTCK_JSON=/opt/mitre/enterprise-attack.json

# ─── Gap 6 (Semantic Embedder) + Gap 10 (Compliance) data dirs ───────────
RUN mkdir -p /data/embed_cache /data/compliance_reports \
 && chmod -R a+rwX /data/embed_cache /data/compliance_reports
ENV RHODAWK_EMBED_CACHE_DIR=/data/embed_cache \
    RHODAWK_REPORT_DIR=/data/compliance_reports \
    RHODAWK_THREAT_GRAPH_DB=/data/threat_graph.sqlite

# uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Bun
COPY --from=oven/bun:latest /usr/local/bin/bun /usr/local/bin/bun
COPY --from=oven/bun:latest /usr/local/bin/bunx /usr/local/bin/bunx

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
                mcp-server-fetch mcp-server-git mcp-server-sqlite \
                grpcio==1.66.* grpcio-tools==1.66.* protobuf==5.*

# Global MCP servers (npm)
RUN npm install -g --quiet \
        @modelcontextprotocol/server-github \
        @modelcontextprotocol/server-filesystem \
        @modelcontextprotocol/server-memory \
        @modelcontextprotocol/server-sequential-thinking \
        @modelcontextprotocol/server-brave-search

# ─── camofox-browser ────────────────────────────────────────────────────
RUN mkdir -p /opt/camofox && cd /opt/camofox && \
    npm init -y >/dev/null 2>&1 && \
    npm install --quiet --omit=dev @askjo/camofox-browser@^1.6.0 || \
    npm install --quiet --omit=dev camofox-browser

# ─── NEW: Install Nous Research Hermes Agent ───────────────────────────
# The official installer places it in $HOME/.hermes-agent (root -> /root)
WORKDIR /tmp
RUN curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash \
    && mkdir -p /opt/hermes-agent \
    && if [ -d /root/.hermes-agent ]; then mv /root/.hermes-agent/* /opt/hermes-agent/; fi \
    && chmod -R a+rX /opt/hermes-agent

# Set environment pointing to our clean location
ENV HERMES_AGENT_HOME=/opt/hermes-agent \
    PATH="/opt/hermes-agent/bin:${PATH}"

# ─── NEW: Install OpenClaw globally ────────────────────────────────────
RUN npm install -g openclaw@latest \
    && mkdir -p /opt/openclaw \
    && cp -R /usr/local/lib/node_modules/openclaw /opt/openclaw/lib \
    && chmod -R a+rX /opt/openclaw

# ─── Stage 3: final runtime image ───────────────────────────────────────
FROM base AS runtime
LABEL org.opencontainers.image.title="Rhodawk AI DevSecOps Engine" \
      org.opencontainers.image.source="https://github.com/Rhodawk-AI/Rhodawk-devops-engine"

ENV GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    HOME=/home/rhodawk \
    PATH="/home/rhodawk/.local/bin:/usr/local/bin:/opt/hermes-agent/bin:${PATH}" \
    UV_PYTHON_PREFERENCE=system \
    UV_PYTHON=/usr/local/bin/python3 \
    OPENCLAUDE_AUTO_APPROVE=1 \
    OPENCLAUDE_GRPC_HOST=127.0.0.1 \
    OPENCLAUDE_GRPC_PORT_DO=50051 \
    OPENCLAUDE_GRPC_PORT_OR=50052 \
    MCP_RUNTIME_CONFIG=/tmp/mcp_runtime.json \
    CAMOFOX_BASE_URL=http://127.0.0.1:9377 \
    CAMOFOX_PORT=9377 \
    CAMOFOX_HOST=127.0.0.1 \
    CAMOFOX_HEADLESS=virtual \
    CAMOFOX_PROFILE_DIR=/data/camofox/profiles \
    CAMOFOX_COOKIES_DIR=/data/camofox/cookies \
    # ─── NEW: Agent configuration defaults ──────────────────────────
    HERMES_AGENT_HOME=/opt/hermes-agent \
    OPENCLAW_HOME=/opt/openclaw \
    HERMES_AGENT_PORT=11434 \
    OPENCLAW_GATEWAY_PORT=18789 \
    EMBODIED_BRIDGE_PORT=9500 \
    # When booting, the bridge will auto-generate these
    HERMES_MCP_CONFIG=/tmp/mcp_runtime.embodied.json \
    OPENCLAW_MCP_CONFIG=/tmp/openclaw_mcp.embodied.json

# Non‑root user
RUN id -u 1000 >/dev/null 2>&1 && (userdel -r "$(id -un 1000)" || true) || true && \
    useradd -m -u 1000 -s /bin/bash rhodawk

RUN mkdir -p /data /data/camofox/profiles /data/camofox/cookies \
    /app /opt/openclaude /opt/hermes-agent /opt/openclaw /opt/camofox && \
    chmod -R 777 /data && \
    chown -R rhodawk:rhodawk /app /opt/openclaude /opt/hermes-agent /opt/openclaw /opt/camofox

# Vendored OpenClaude bundle
COPY --from=openclaude-builder --chown=rhodawk:rhodawk /openclaude /opt/openclaude

# Convenience symlinks
RUN ln -sf /opt/openclaude/bin/openclaude /usr/local/bin/openclaude && \
    chmod +x /usr/local/bin/openclaude

# Copy the whole Rhodawk codebase (as before)
WORKDIR /app
USER rhodawk
COPY --chown=rhodawk:rhodawk . .

# Generate protobuf stubs
RUN python -m grpc_tools.protoc \
        -I /opt/openclaude/src/proto \
        --python_out=openclaude_grpc \
        --grpc_python_out=openclaude_grpc \
        /opt/openclaude/src/proto/openclaude.proto && \
    sed -i 's/^import openclaude_pb2/from . import openclaude_pb2/' \
        openclaude_grpc/openclaude_pb2_grpc.py

# Expose all ports used by the unified system
EXPOSE 7860 9377 50051 50052 9500 11434 18789

ENTRYPOINT ["/app/entrypoint.sh"]
