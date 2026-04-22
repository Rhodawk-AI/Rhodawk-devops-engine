---
name: memory-safety
domain: binary
triggers:
  languages:    [c, cpp, asm]
  asset_types:  [elf, pe, kernel, firmware]
tools:          [aflpp, klee, angr, gdb, asan, ubsan, valgrind]
severity_focus: [P1, P2]
---

# Memory Safety

## When to load
Native code (C / C++ / Rust unsafe / kernel modules / firmware) where the
attacker can influence buffer length, lifetime or layout.

## Vulnerability classes
* **Stack BOF** — `gets`, `strcpy`, manual `memcpy(stack_buf, src, attacker_len)`.
* **Heap BOF** — `malloc(small) → memcpy(big)`, off-by-one on length.
* **UAF** — pointer used after `free`; common after error paths that double-
  free or after async callbacks.
* **Double-free** — same pointer freed in two error branches.
* **Format-string** — `printf(user_input)`.
* **Integer overflow** — `len * sizeof(T)` wraps before `malloc`.
* **OOB-read** — index not bounds-checked; leaks ASLR / stack canary / heap
  metadata.
* **Type confusion** — vtable corruption in C++ via UAF on a polymorphic
  object.

## Procedure
1. Build the target with `-fsanitize=address,undefined -g -O1` if source is
   available.  Otherwise instrument with QEMU + AFL++.
2. Generate a small seed corpus from the existing test suite.
3. Run AFL++ with `-V 7200` (2 h) per harness; preserve `crashes/` and
   `hangs/`.
4. Triage with `gdb -ex 'r < crash' -ex bt`.
5. Use `mythos.dynamic.klee_runner` to prove reachability under attacker
   control.
6. Write the PoC in pwntools (`mythos.exploit.pwntools_synth.assemble`).
7. Suggest fix:
   * Replace bare `strcpy` → `strlcpy` / `snprintf`.
   * Use `__builtin_mul_overflow` before allocation.
   * Add `assert(idx < cap);` before indexing.

## Reporting
Always include: crash hash, ASAN trace, root cause file:line, exploitability
notes (RIP control, info-leak, DoS-only), suggested patch.
