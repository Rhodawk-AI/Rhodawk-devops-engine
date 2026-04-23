#!/usr/bin/env bash
# ============================================================================
# Rhodawk AI — Local gRPC Stub Generator
# ----------------------------------------------------------------------------
# Resolves W-001 (CRITICAL): the openclaude_grpc/openclaude_pb2.py and
# openclaude_grpc/openclaude_pb2_grpc.py files are NOT committed to source
# (they are generated at Docker build time). This script generates them
# locally so app.py can be imported and run without a full Docker build.
#
# Usage:
#   bash scripts/generate_stubs.sh
#
# Requirements:
#   pip install grpcio-tools
# ============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${REPO_ROOT}/vendor/openclaude/src/proto"
OUT_DIR="${REPO_ROOT}/openclaude_grpc"

if [ ! -f "${PROTO_DIR}/openclaude.proto" ]; then
    echo "[generate_stubs] ERROR: ${PROTO_DIR}/openclaude.proto not found." >&2
    echo "[generate_stubs] The vendor/openclaude submodule may be missing." >&2
    exit 1
fi

if ! python -c "import grpc_tools" 2>/dev/null; then
    echo "[generate_stubs] ERROR: grpcio-tools not installed." >&2
    echo "[generate_stubs] Run: pip install grpcio-tools" >&2
    exit 1
fi

mkdir -p "${OUT_DIR}"

echo "[generate_stubs] Generating Python gRPC stubs..."
python -m grpc_tools.protoc \
    -I "${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    --grpc_python_out="${OUT_DIR}" \
    "${PROTO_DIR}/openclaude.proto"

# Patch the generated _grpc.py to use a relative import so it works as a
# package module (the protoc default emits an absolute import).
GRPC_FILE="${OUT_DIR}/openclaude_pb2_grpc.py"
if [ -f "${GRPC_FILE}" ]; then
    sed -i.bak 's/^import openclaude_pb2 as openclaude__pb2$/from . import openclaude_pb2 as openclaude__pb2/' "${GRPC_FILE}"
    rm -f "${GRPC_FILE}.bak"
fi

echo "[generate_stubs] Done. Generated:"
ls -la "${OUT_DIR}"/openclaude_pb2*.py
