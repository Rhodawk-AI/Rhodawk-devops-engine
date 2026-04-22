"""
httpx-probe-mcp — concurrent HTTP(S) probing + tech fingerprinting (§9.2).

Native ``httpx`` (projectdiscovery) is preferred; otherwise we fall back to
``requests`` + a tiny header / body fingerprint.
"""

from __future__ import annotations

import concurrent.futures as cf
import shutil
import subprocess
from typing import Any

import requests

from ._mcp_runtime import MCPServer

server = MCPServer(name="httpx-probe-mcp")


def _fingerprint(headers: dict[str, str], body: str) -> list[str]:
    techs: list[str] = []
    h = {k.lower(): v.lower() for k, v in headers.items()}
    server_h = h.get("server", "")
    powered  = h.get("x-powered-by", "")
    for kw, tech in [
        ("nginx", "nginx"), ("apache", "apache"), ("cloudflare", "cloudflare"),
        ("envoy", "envoy"), ("openresty", "openresty"), ("caddy", "caddy"),
        ("iis", "iis"), ("amazons3", "amazon-s3"),
    ]:
        if kw in server_h:
            techs.append(tech)
    for kw, tech in [
        ("php", "php"), ("express", "express"), ("django", "django"),
        ("rails", "rails"), ("asp.net", "asp.net"),
    ]:
        if kw in powered:
            techs.append(tech)
    snippet = body[:6000].lower()
    for kw, tech in [
        ("wp-content", "wordpress"), ("drupal", "drupal"), ("react", "react"),
        ("__next_data__", "next.js"), ("ng-version", "angular"),
        ("vue.js", "vue"), ("graphql", "graphql"),
    ]:
        if kw in snippet:
            techs.append(tech)
    return sorted(set(techs))


def _probe_one(host: str) -> dict[str, Any]:
    for scheme in ("https", "http"):
        url = f"{scheme}://{host}"
        try:
            r = requests.get(url, timeout=10, allow_redirects=True, verify=False)
            return {"host": host, "url": r.url, "status": r.status_code,
                    "title": _title(r.text),
                    "tech": _fingerprint(dict(r.headers), r.text)}
        except Exception:  # noqa: BLE001
            continue
    return {"host": host, "url": None, "status": None}


def _title(body: str) -> str:
    import re
    m = re.search(r"<title[^>]*>([^<]+)</title>", body, re.I)
    return (m.group(1).strip() if m else "")[:160]


@server.tool("probe", schema={"hosts": "list[string]", "concurrency": "int"})
def probe(hosts: list[str], concurrency: int = 16) -> dict[str, Any]:
    if not hosts:
        return {"live": [], "dead": [], "count": 0}
    if shutil.which("httpx"):
        try:
            inp = "\n".join(hosts).encode()
            r = subprocess.run(
                ["httpx", "-silent", "-status-code", "-tech-detect", "-title", "-json"],
                input=inp, capture_output=True, timeout=180,
            )
            import json
            live = []
            for line in r.stdout.decode(errors="ignore").splitlines():
                try:
                    live.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    pass
            return {"live": live, "count": len(live), "backend": "httpx"}
        except Exception:  # noqa: BLE001
            pass
    live, dead = [], []
    with cf.ThreadPoolExecutor(max_workers=concurrency) as ex:
        for r in ex.map(_probe_one, hosts):
            (live if r.get("status") else dead).append(r)
    return {"live": live, "dead": dead, "count": len(live), "backend": "requests"}


if __name__ == "__main__":
    server.serve_stdio()
