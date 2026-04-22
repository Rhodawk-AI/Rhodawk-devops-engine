---
name: browser-engine-security
domain: browser
triggers:
  languages:    [c, cpp, rust, javascript]
  frameworks:   [v8, spidermonkey, jsc, blink, gecko, webkit, chromium]
  asset_types:  [browser, engine, jit, renderer, sandbox]
tools:          [domato, fuzzilli, jsfunfuzz, rr, gdb, lldb]
severity_focus: [P1, P2]
---

# Browser Engine Security

## When to load
V8, SpiderMonkey, JavaScriptCore, WebKit, Blink, Servo source trees;
WebAssembly runtimes; PDF renderers shipped inside browsers.

## Bug classes that pay (Pwn2Own / Chrome VRP / TCC tier)
1. **JIT type confusion** — speculative type narrowing wrong; e.g. range
   analysis assumes int but value is double. Triggered by complex
   array/typed-array interplay.
2. **OOB in JIT'd code** — bounds-check elimination over-aggressive;
   `arr[length-1]` with `length` = 0 turns into negative index.
3. **Use-after-free in DOM** — node removed during a callback while parent
   iteration holds a raw pointer.
4. **Renderer → sandbox escape** — IPC message handler trusts
   renderer-controlled enum; Mojo interface allowing file path traversal.
5. **WebAssembly engine** — JIT for SIMD / GC proposals, structural
   typing bugs in the new GC opcodes.
6. **PDF / image parser** — PDFium, libwebp, libavif — these alone have
   produced $100K+ Chrome bounties.
7. **Site-isolation bypass** — confused-deputy in process model, leaks of
   cross-origin secrets via timing or cache.

## Methodology
1. **Read the recent fix landings** — Chromium `chromium/src` repo,
   `master` branch commits with `[security]` or `Fixed:` referencing
   `crbug.com/<id>`. Public 14 weeks after fix; unpublished bugs leave
   patterns visible.
2. **Re-fuzz the patched function** — use Fuzzilli with the patched
   binary; you're hunting for the *next* bug in the same area.
3. **Differential fuzzing** — V8 vs JSC vs SpiderMonkey on the same
   corpus; output divergence = bug.
4. **Focus the fuzzer on the proposal under active development** —
   intl, Temporal, GC, JSPI, ShadowRealm. New code = least audited.
5. **Symbolic execution on JIT IR** — pin specific operations
   (`Int32Add`, `LoadElement`) with manticore-style constraints.

## Exploitation pattern (modern V8)
- **AddrOf primitive** via leaked pointer in TypedArray length confusion.
- **Arbitrary read/write** by faking a JSArray with crafted map.
- **Code execution** by overwriting WebAssembly RWX page (post-V8 21,
   need pivot via builtin trampoline or RWX in the JIT compiler).
- **Sandbox escape** via separate Mojo bug — chain is required for the
   $100K+ payouts.

## Reporting
Chrome VRP: file via `g.co/vulnz`, attach minimal repro `<200 LOC>`,
include exact commit hash you tested against, ASAN log, and a sentence
on the security boundary crossed.
