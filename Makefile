# Rhodawk AI — Local Developer Makefile
# Resolves W-001: provides a one-shot target to generate gRPC stubs locally
# so the Python brain can run without requiring a full Docker build.

.PHONY: help stubs install dev clean

help:
	@echo "Rhodawk AI — local developer targets"
	@echo "  make stubs    Generate openclaude_pb2*.py gRPC stubs (W-001)"
	@echo "  make install  pip install -r requirements.txt + grpcio-tools"
	@echo "  make dev      Run app.py locally (requires stubs + env vars)"
	@echo "  make clean    Remove generated gRPC stubs"

stubs:
	bash scripts/generate_stubs.sh

install:
	pip install -r requirements.txt
	pip install grpcio-tools

dev: stubs
	python -u app.py

clean:
	rm -f openclaude_grpc/openclaude_pb2.py openclaude_grpc/openclaude_pb2_grpc.py
