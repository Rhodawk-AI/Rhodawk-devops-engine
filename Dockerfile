ARG BUN_VERSION=latest
# ─── Stage 1: build the vendored OpenClaude bundle ────────────────>
FROM oven/bun:${BUN_VERSION} AS openclaude-builder
WORKDIR /openclaude
COPY vendor/openclaude/package.json ./
RUN bun install --no-progress
COPY vendor/openclaude/ ./
RUN bun run build && \
    test -s dist/cli.mjs && \
    echo "[builder] OpenClaude bundle: $(wc -c < dist/cli.mjs) bytes"

# ─── Stage 2: base python+node runtime ────────────────────────────>
FROM python:3.12-slim AS base
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# ─── OS Dependencies & Tooling (SEGMENTED FOR DEBUGGING) ──────────>
RUN apt-get update --fix-missing

# Block 1: Core Build Tools
RUN apt-get install -y --no-install-recommends \
    git curl wget gnupg ca-certificates build-essential unzip xz-utils nodejs

# Block 2: AFL++ and LLVM
RUN apt-get install -y --no-install-recommends \
    afl++ clang lld llvm

# Block 3: Ghidra Dependencies
RUN apt-get install -y --no-install-recommends \
    openjdk-21-jdk-headless

# Block 4: Nsjail Compilation Dependencies
RUN apt-get install -y --no-install-recommends \
    autoconf bison flex libprotobuf-dev libnl-route-3-dev libtool pkg-config protobuf-compiler

# Block 5: Headless Browser OS Dependencies
RUN apt-get install -y --no-install-recommends \
    xvfb libgtk-3-0 libdbus-glib-1-2 libxt6 libasound2 \
    libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 \
    libxi6 libxrandr2 libxss1 libxtst6 libnss3 libpango-1.0-0 \
    libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# ─── Gap 3: Nsjail (Exploit Validator Sandbox) ────────────────────>
RUN git clone https://github.com/google/nsjail.git /tmp/nsjail \
    && cd /tmp/nsjail \
    && make \
    && mv /tmp/nsjail/nsjail /usr/local/bin/ \
    && rm -rf /tmp/nsjail

# ─── Gap 1: CodeQL CLI ────────────────────────────────────────────>
RUN curl -fsSL -o /tmp/codeql.zip \
      https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip \
 && unzip -q /tmp/codeql.zip -d /opt \
 && rm /tmp/codeql.zip \
 && /opt/codeql/codeql pack download \
      codeql/python-queries codeql/javascript-queries \
      codeql/java-queries codeql/cpp-queries codeql/go-queries

# ─── Gap 4: Ghidra ────────────────────────────────────────────────>
RUN curl -fsSL -o /tmp/g.zip https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.2_build/ghidra_11.2_PUBLIC_20240926.zip \
 && unzip -q /tmp/g.zip -d /opt \
 && mv /opt/ghidra_* /opt/ghidra \
 && rm /tmp/g.zip

# ─── Python Dependencies ──────────────────────────────────────────>
WORKDIR /opt/rhodawk

RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# ─── Gap 6: Semantic Embedder Pre-warm ────────────────────────────>
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('nomic-ai/nomic-embed-code', trust_remote_code=True)"

# ─── Copy Application Code ────────────────────────────────────────>
COPY . .
COPY --from=openclaude-builder /openclaude/dist/cli.mjs /opt/rhodawk/vendor/openclaude/dist/cli.mjs

# ─── Final Environment Variables ──────────────────────────────────>
ENV CODEQL_BIN=/opt/codeql/codeql \
    CODEQL_DB_DIR=/data/codeql_dbs \
    GHIDRA_HOME=/opt/ghidra \
    AFL_BIN=afl-fuzz \
    AFL_CC=afl-clang-fast \
    FUZZ_CORPUS_DIR=/data/fuzz_corpus \
    FUZZ_FINDINGS_DIR=/data/fuzz_findings \
    RHODAWK_EMBEDDING_MODEL=nomic-ai/nomic-embed-code \
    RHODAWK_EMBEDDING_DIM=768 \
    RHODAWK_EMBEDDING_DEVICE=cpu

CMD ["python3", "app.py"]
