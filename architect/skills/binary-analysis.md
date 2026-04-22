---
name: binary-analysis
domain: binary
triggers:
  languages:    [c, cpp, rust, asm, go]
  asset_types:  [elf, pe, macho, firmware]
tools:          [ghidra, radare2, objdump, readelf, gdb, angr]
severity_focus: [P1, P2]
---

# Binary Analysis

## When to load
Compiled native artefacts (ELF/PE/Mach-O), embedded firmware images, or any
target where source is unavailable.

## Procedure
1. **Triage** — `file <bin>`, `readelf -aW <bin>`, `strings -n 8 <bin> | head`.
   Note the architecture, ASLR/PIE/RELRO/NX/Stack-Canary flags (`checksec`).
2. **Function discovery** — `r2 -A <bin>` then `afl` to list functions, or
   Ghidra Auto-Analysis (analyzeHeadless if scripted via the
   `ghidra-bridge-mcp` tool).
3. **Sink hunt** — search for known-dangerous calls: `strcpy`, `gets`,
   `sprintf`, `system`, `popen`, `memcpy(_, _, attacker_len)`,
   `Runtime.getRuntime().exec` (in JNI shims).
4. **Source identification** — find input boundaries: `recv`, `read`,
   `fread`, `getenv`, command-line args, file format parsers.
5. **Reachability** — use angr (`mythos.dynamic.klee_runner` for symbolic
   companion) to prove a path from a source to a sink under attacker
   control.
6. **Exploitability** — pwntools template (`mythos.exploit.pwntools_synth`)
   for stack-overflow, ROP-chain builder for ASLR bypass, heap-fengshui via
   `heap_exploit`.
7. **Sanitisation** — recompile with `-fsanitize=address,undefined` and
   re-run the AFL++ corpus to confirm.

## Known-bad patterns
* User-controlled length passed straight to `memcpy`/`strncpy`.
* Stack arrays with VLA / `alloca(attacker_size)`.
* Format strings that include `%n` and accept user input.
* Integer overflow before `malloc(size_t)` allocation.

## Tool calls (MCP)
* `ghidra-bridge-mcp.analyse_binary` — full SAST sweep
* `mythos.dynamic.klee` — symbolic execution on critical functions
* `mythos.dynamic.aflpp` — coverage-guided fuzz, 2 h budget
* `mythos.exploit.rop` — ROP-chain candidate generation
