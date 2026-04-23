# External Knowledge & Tool Integrations

Rhodawk now embeds three external knowledge / capability sources directly
into the runtime so the orchestrator and analysis engines can use them
offline, without round-tripping to the public web on every audit.

| Vendor                                                      | Lives at                          | Python module             | What it gives Rhodawk |
|-------------------------------------------------------------|-----------------------------------|---------------------------|------------------------|
| [`jo-inc/camofox-browser`](https://github.com/jo-inc/camofox-browser)               | `/opt/camofox` (npm) + node server | `camofox_client.py`       | Anti-detection Firefox-fork browsing for live web tasks (cve_intel, repo_harvester, knowledge_rag, red_team_fuzzer, bounty_gateway) |
| [`0xmaximus/Galaxy-Bugbounty-Checklist`](https://github.com/0xmaximus/Galaxy-Bugbounty-Checklist) | `vendor/galaxy_bugbounty/`        | `bugbounty_checklist.py`  | 24-category bug bounty methodology + payload corpora keyed by CWE / vuln tag |
| [`zomasec/client-side-bugs-resources`](https://github.com/zomasec/client-side-bugs-resources)     | `vendor/clientside_bugs/`         | `clientside_resources.py` | Curated client-side (XSS / CSP / postMessage / prototype-pollution / CORS) reading list — section-indexed |
| [`PrathamLearnsToCode/paper2code`](https://github.com/PrathamLearnsToCode/paper2code)             | `vendor/paper2code/`              | `paper2code_engine.py`    | arXiv-paper → citation-anchored, ambiguity-audited Python scaffold (uses the existing OpenClaude gRPC bridge for LLM calls) |

## Where they plug into the existing engines

### `bugbounty_checklist.py`

* **`vuln_classifier.py`** — after CWE classification, call
  `bugbounty_checklist.match_for_tag(cwe)` to surface the canonical
  Galaxy checklist for that class (24 categories covered: XSS, SSRF,
  SQLi, OAuth, CSRF bypass, IDOR, file upload, request smuggling,
  rate-limit bypass, password reset, IIS, Log4Shell, WordPress, …).
* **`red_team_fuzzer.py` / `harness_factory.py`** — call
  `payloads_for("sql_injection")` to seed the SQLi corpus from
  Galaxy's `SQL.txt`, or `payloads_for("xss")` to harvest inline
  XSS payload snippets from the README.
* **`hermes_orchestrator.py`** — call
  `hints_for_finding(cwe=..., label=..., description=...)` to inject
  hand-curated tradecraft bullets into the triage prompt.

### `clientside_resources.py`

* **`knowledge_rag.py`** — `seed_urls()` returns a flat unique list of
  the upstream README's links, perfect as initial input to the
  embedding-store ingest loop.
* **`red_team_fuzzer.py`** — `for_tag("postmessage")` returns the
  reference write-ups to attach to a generated client-side PoC.
* **`vuln_classifier.py`** — `search("dompurify")` etc. surfaces
  reference research write-ups when classifying client-side findings.

### `paper2code_engine.py`

* **`hermes_orchestrator.py`** Night-Hunt mode — when a new primitive
  surfaces in the wild, call `paper2code_engine.run(arxiv_url)` to
  scaffold a reproduction under `/data/paper2code/{slug}/` with an
  ambiguity audit.  The orchestrator can then hand the scaffold to
  the OpenClaude gRPC bridge for completion.
* **`training_store.py`** — register the scaffold's
  `REPRODUCTION_NOTES.md` + `ambiguity_audit.json` as a training
  example for the data flywheel.
* **`knowledge_rag.py`** — the ambiguity audit (per-dimension
  SPECIFIED / PARTIALLY_SPECIFIED / UNSPECIFIED classification) is
  embedded alongside the paper text so the RAG store learns *what is
  uncertain*, not just *what was written*.

## Quick programmatic checks

```python
import bugbounty_checklist as bb
print(bb.stats())                      # {'categories': 24, 'total_payloads': ...}
print(bb.list_categories())
print(bb.payloads_for('sqli', limit=5))
print(bb.hints_for_finding(cwe='CWE-918'))

import clientside_resources as cs
print(cs.stats())                      # sections + resource count
print(cs.for_tag('prototype_pollution'))

import paper2code_engine as p2c
print(p2c.stats())                     # vendor + LLM availability
result = p2c.run('https://arxiv.org/abs/1706.03762')   # heuristic mode if no LLM
print(result.to_dict())
```

## Vendoring policy

* All three repos are mirrored under `vendor/` so the runtime is
  self-contained and reproducible — no surprise upstream changes can
  break a Rhodawk scan in the middle of an engagement.
* Re-vendoring is a manual operation (just `git clone` the upstream
  and copy the relevant directories) — version pinning is implicit
  through git history.
* Source licenses (MIT for camofox-browser and clientside-bugs,
  MIT for paper2code, MIT for Galaxy-Bugbounty-Checklist) are
  preserved alongside the vendored content.
