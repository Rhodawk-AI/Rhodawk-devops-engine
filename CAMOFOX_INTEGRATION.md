# Camofox-Browser Integration

Rhodawk now ships with an embedded
[camofox-browser](https://github.com/jo-inc/camofox-browser) anti-detection
browser server so the orchestrator and analysis engines can browse the live
web without being fingerprinted, blocked by Cloudflare, or flagged by
Google's bot detection.

## Why

Several Rhodawk subsystems already need to fetch real-world web content:

| Subsystem            | Today                       | With camofox-browser                       |
|----------------------|-----------------------------|--------------------------------------------|
| `cve_intel.py`       | Plain `requests` to NVD/SSEC | Real-browser fetch with stable element refs |
| `repo_harvester.py`  | GitHub REST + raw HTML       | Authenticated session reuse, no rate-limit captcha |
| `knowledge_rag.py`   | Static doc scraping          | JS-rendered docs (Notion, Confluence, etc.) |
| `red_team_fuzzer.py` | n/a                          | Live target reconnaissance                 |
| `bounty_gateway.py`  | HackerOne / Bugcrowd REST    | UI fallback when the REST API is down      |

camofox patches Firefox at the **C++ implementation level** —
`navigator.hardwareConcurrency`, WebGL renderers, AudioContext, screen
geometry, WebRTC — all spoofed before JavaScript ever sees them. No shims,
no wrappers, no tells.

## Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  app.py / orchestrator      │  HTTP   │  /opt/camofox  (node)        │
│  cve_intel.py / harvester   │ ──────▶ │  127.0.0.1:9377              │
│  knowledge_rag.py / …       │         │  camofox-browser server      │
│                             │         │  ├── Camoufox (Firefox fork) │
│  camofox_client.py          │         │  ├── Playwright contexts     │
│  └─ CamofoxClient (REST)    │         │  └── per-userId session jar  │
└─────────────────────────────┘         └──────────────────────────────┘
```

* **Server** is launched by `entrypoint.sh` alongside the OpenClaude gRPC
  daemons. Listens on `127.0.0.1:9377` (not exposed publicly by default).
* **Client** is `camofox_client.py` — a thin, dependency-free
  (`requests`-only) Python wrapper that any module can import.
* **Sessions** are isolated per `userId` so concurrent research jobs
  cannot leak cookies into each other.

## Quick Start (Python)

```python
from camofox_client import get_client, fetch_snapshot

# One-shot: fetch a snapshot of a URL with element refs.
snap = fetch_snapshot(
    "https://nvd.nist.gov/vuln/detail/CVE-2024-3094",
    user_id="cve_intel",
)
if snap.get("available"):
    print(snap["snapshot"][:2000])

# Long-running session:
client = get_client()
if client.is_available():
    tab = client.create_tab("harvester", "https://github.com/torvalds/linux")
    snap = client.snapshot(tab)
    client.click(tab, "e1")           # click the first interactive element
    client.type_text(tab, "e2", "fix") # type into the search box
    png = client.screenshot(tab, full_page=True)
    client.close_tab(tab)
```

If the camofox server is not running, `is_available()` returns `False` and
`fetch_snapshot()` returns `{"available": False, "reason": "..."}` so callers
can degrade gracefully to plain `requests`.

## Environment Variables

| Variable                 | Default                        | Purpose                                   |
|--------------------------|--------------------------------|-------------------------------------------|
| `CAMOFOX_BASE_URL`       | `http://127.0.0.1:9377`        | Where the Python client looks for the API |
| `CAMOFOX_PORT`           | `9377`                         | Port the node server binds to             |
| `CAMOFOX_HOST`           | `127.0.0.1`                    | Host the node server binds to             |
| `CAMOFOX_HEADLESS`       | `virtual`                      | `virtual` uses xvfb; `true` uses Firefox headless mode |
| `CAMOFOX_PROFILE_DIR`    | `/data/camofox/profiles`       | Persistent per-user storage state         |
| `CAMOFOX_COOKIES_DIR`    | `/data/camofox/cookies`        | Drop Netscape cookie files here for import |
| `CAMOFOX_API_KEY`        | *(unset → cookie writes disabled)* | Bearer token required for `import_cookies` |
| `PROXY_HOST` / `PROXY_PORT` / `PROXY_USERNAME` / `PROXY_PASSWORD` | *(unset)* | Route browser traffic through a residential proxy. Camoufox's GeoIP then auto-aligns locale + timezone. |

## Files Added

| Path                       | What it is                                  |
|----------------------------|---------------------------------------------|
| `camofox_client.py`        | Python REST client + module-level helpers   |
| `CAMOFOX_INTEGRATION.md`   | This document                               |
| `Dockerfile` (modified)    | Installs `@askjo/camofox-browser` under `/opt/camofox` and the X/GTK runtime libs Camoufox needs |
| `entrypoint.sh` (modified) | Launches the camofox server before the OpenClaude daemons |
