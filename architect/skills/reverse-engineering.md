---
name: reverse-engineering
domain: binary
triggers:
  languages:    [c, cpp, asm, go, rust]
  asset_types:  [elf, pe, macho, dotnet, jar, dex, wasm]
tools:          [ghidra, ida, rizin, dnSpy, jadx, wabt, FLIRT]
severity_focus: [P1, P2]
---

# Reverse Engineering

## When to load
Closed-source binaries, packed/obfuscated samples, .NET assemblies, JARs,
WASM modules.

## Procedure
1. Identify packer (`die`, `peid`); unpack with appropriate technique
   (UPX `-d`, manual OEP find for custom packers).
2. Detect language: stripped Go binaries have `.gopclntab`, Rust have
   `core::panicking`, Nim have `nim_main`, .NET via `corflags`.
3. Apply FLIRT signatures to recover library functions; decompile in Ghidra.
4. Diff against benign baseline if available (`bindiff`).
5. Identify protocol/serialisation by data flow into `recv`/`read`.
6. Document call graph for the security-critical surface (auth, crypto,
   parser).

## Outputs
* Annotated Ghidra GZF or radare2 project
* Function summary table → fed back to the LLM as context
* Suggested fuzzing harness skeletons (one per attacker-influenced sink)
