"""
Rhodawk AI — SBOM / SCA Engine (GAP 7)
=======================================
Software Composition Analysis for any cloned repository or container
image, fusing four best-in-class scanners:

  * **syft**         — SBOM generation in CycloneDX 1.5 / SPDX 2.3 JSON.
  * **grype**        — Vuln scan against the syft SBOM (Anchore DB).
  * **osv-scanner**  — Google's OSV.dev cross-ecosystem scanner.
  * **trivy**        — Aqua's filesystem + dependency scanner with
                       OS-package coverage that grype misses.

The four results are normalised into a single ``SBOMReport`` so the
orchestrator and the compliance report generator (Gap 10) can consume
one consistent finding shape regardless of which tool surfaced it.

Each scanner is invoked as a **subprocess** with a strict timeout, no
shell, and an env-var override for the binary path so operators can
swap in patched builds without code changes.

Public API
----------
``run_sbom(target, *, fmt='cyclonedx-json', kind='dir') -> dict``
    Generate the SBOM. ``kind`` ∈ ``dir | image``.

``run_full_sca(target, *, kind='dir') -> SBOMReport``
    Generate the SBOM, then run all available scanners in parallel and
    return a deduplicated, severity-sorted report.

``record_findings_to_threat_graph(report) -> int``
    Push every CRITICAL/HIGH finding into ``threat_graph.record_finding``
    so the compliance report sees them.

Environment variables
---------------------
``SYFT_BIN``         Default ``syft``.
``GRYPE_BIN``        Default ``grype``.
``OSV_BIN``          Default ``osv-scanner``.
``TRIVY_BIN``        Default ``trivy``.
``SCA_TIMEOUT``      Per-scanner timeout (s); default 600.
``SBOM_OUT_DIR``     SBOM + report output directory; default ``/data/sbom``.
"""

from __future__ import annotations

import concurrent.futures as _cf
import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

LOG = logging.getLogger("rhodawk.sbom_engine")
if not LOG.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )

SYFT_BIN     = os.getenv("SYFT_BIN",  "syft")
GRYPE_BIN    = os.getenv("GRYPE_BIN", "grype")
OSV_BIN      = os.getenv("OSV_BIN",   "osv-scanner")
TRIVY_BIN    = os.getenv("TRIVY_BIN", "trivy")
SCA_TIMEOUT  = int(os.getenv("SCA_TIMEOUT", "600"))
SBOM_OUT_DIR = os.getenv("SBOM_OUT_DIR", "/data/sbom")

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE", "UNKNOWN"]
_SEV_RANK      = {s: i for i, s in enumerate(SEVERITY_ORDER)}


# ──────────────────────────────────────────────────────────────────────
@dataclass
class Finding:
    tool:           str
    package:        str
    version:        str
    ecosystem:      str
    cve_id:         str = ""
    advisory_url:   str = ""
    severity:       str = "UNKNOWN"
    cvss_score:     float = 0.0
    fix_version:    str = ""
    title:          str = ""
    cwe:            str = ""

    def dedupe_key(self) -> tuple:
        return (self.package.lower(), self.version, self.cve_id.upper())


@dataclass
class SBOMReport:
    target:         str
    kind:           str          # dir | image
    sbom_path:      str
    findings:       list[Finding] = field(default_factory=list)
    tools_run:      list[str]     = field(default_factory=list)
    tools_skipped:  list[str]     = field(default_factory=list)
    summary:        dict         = field(default_factory=dict)
    wall_time_ms:   int          = 0
    error:          Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [asdict(f) for f in self.findings]
        return d


# ──────────────────────────────────────────────────────────────────────
def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


def _run(cmd: list[str], *, timeout: int = SCA_TIMEOUT) -> tuple[int, str, str]:
    LOG.info("exec: %s", " ".join(cmd))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except Exception as exc:                                # noqa: BLE001
        return 1,   "", str(exc)


def _norm_sev(s: str) -> str:
    s = (s or "UNKNOWN").upper()
    if s in _SEV_RANK:
        return s
    return {
        "CRIT": "CRITICAL", "HI": "HIGH", "MOD": "MEDIUM",
        "MED": "MEDIUM", "INFO": "LOW",
    }.get(s, "UNKNOWN")


# ──────────────────────────────────────────────────────────────────────
# Scanner adapters
# ──────────────────────────────────────────────────────────────────────
def run_sbom(target: str, *, fmt: str = "cyclonedx-json", kind: str = "dir") -> dict:
    """Invoke syft and return the parsed SBOM JSON.

    Returns ``{"path": str, "data": dict}`` on success. Raises on failure.
    """
    if not _have(SYFT_BIN):
        raise RuntimeError(f"{SYFT_BIN} not found in PATH")
    os.makedirs(SBOM_OUT_DIR, exist_ok=True)
    suffix = "json"
    out = os.path.join(SBOM_OUT_DIR, f"sbom_{int(time.time()*1000)}.{suffix}")
    src = target if kind == "image" else f"dir:{target}"
    rc, stdout, stderr = _run([SYFT_BIN, src, "-o", f"{fmt}={out}"])
    if rc != 0 or not os.path.isfile(out):
        raise RuntimeError(f"syft failed (rc={rc}): {stderr[-512:]}")
    with open(out, "r") as fh:
        data = json.load(fh)
    return {"path": out, "data": data}


def _scan_grype(sbom_path: str) -> list[Finding]:
    if not _have(GRYPE_BIN):
        return []
    rc, out, err = _run([GRYPE_BIN, f"sbom:{sbom_path}", "-o", "json"])
    if rc != 0:
        LOG.warning("grype failed: %s", (err or "")[-256:])
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    findings: list[Finding] = []
    for m in data.get("matches", []) or []:
        v = m.get("vulnerability", {}) or {}
        a = m.get("artifact", {}) or {}
        findings.append(Finding(
            tool="grype",
            package=a.get("name", ""),
            version=a.get("version", ""),
            ecosystem=(a.get("type") or "").lower(),
            cve_id=v.get("id", ""),
            advisory_url=v.get("dataSource", ""),
            severity=_norm_sev(v.get("severity", "UNKNOWN")),
            cvss_score=float(((v.get("cvss") or [{}])[0]).get("metrics", {}).get("baseScore") or 0.0),
            fix_version=",".join(v.get("fix", {}).get("versions", []) or []),
            title=v.get("description") or "",
        ))
    return findings


def _scan_osv(target: str, kind: str) -> list[Finding]:
    if not _have(OSV_BIN):
        return []
    cmd = [OSV_BIN, "--format=json"]
    cmd += ["--docker", target] if kind == "image" else [target]
    rc, out, err = _run(cmd)
    if rc not in (0, 1):
        LOG.warning("osv-scanner failed: %s", (err or "")[-256:])
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    findings: list[Finding] = []
    for r in data.get("results", []) or []:
        for pkg in r.get("packages", []) or []:
            info = pkg.get("package", {}) or {}
            for v in pkg.get("vulnerabilities", []) or []:
                sev = "UNKNOWN"
                cvss = 0.0
                for s in v.get("severity", []) or []:
                    sev = _norm_sev(s.get("type", "")) or sev
                    try:
                        cvss = float(s.get("score", "0").split("/")[0])
                    except (ValueError, AttributeError):
                        pass
                findings.append(Finding(
                    tool="osv-scanner",
                    package=info.get("name", ""),
                    version=info.get("version", ""),
                    ecosystem=(info.get("ecosystem") or "").lower(),
                    cve_id=v.get("id", ""),
                    advisory_url=(v.get("references") or [{}])[0].get("url", ""),
                    severity=sev,
                    cvss_score=cvss,
                    title=v.get("summary", ""),
                ))
    return findings


def _scan_trivy(target: str, kind: str) -> list[Finding]:
    if not _have(TRIVY_BIN):
        return []
    sub = "image" if kind == "image" else "fs"
    rc, out, err = _run([TRIVY_BIN, sub, "--quiet", "--format", "json", target])
    if rc not in (0, 1):
        LOG.warning("trivy failed: %s", (err or "")[-256:])
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    findings: list[Finding] = []
    for r in data.get("Results", []) or []:
        for v in r.get("Vulnerabilities", []) or []:
            cvss_score = 0.0
            cvss = v.get("CVSS", {}) or {}
            for vendor in cvss.values():
                try:
                    cvss_score = max(cvss_score, float(vendor.get("V3Score") or 0))
                except (ValueError, TypeError):
                    pass
            findings.append(Finding(
                tool="trivy",
                package=v.get("PkgName", ""),
                version=v.get("InstalledVersion", ""),
                ecosystem=(r.get("Type") or "").lower(),
                cve_id=v.get("VulnerabilityID", ""),
                advisory_url=v.get("PrimaryURL", ""),
                severity=_norm_sev(v.get("Severity", "UNKNOWN")),
                cvss_score=cvss_score,
                fix_version=v.get("FixedVersion", ""),
                title=v.get("Title", ""),
                cwe=",".join(v.get("CweIDs", []) or []),
            ))
    return findings


# ──────────────────────────────────────────────────────────────────────
# Orchestrator
# ──────────────────────────────────────────────────────────────────────
def run_full_sca(target: str, *, kind: str = "dir") -> SBOMReport:
    """Run all available SCA tools in parallel; return a merged report."""
    started = time.monotonic()
    tools_run:     list[str] = []
    tools_skipped: list[str] = []
    sbom_path = ""

    if not (kind == "image" or os.path.isdir(target)):
        return SBOMReport(
            target=target, kind=kind, sbom_path="", error="target not found",
            wall_time_ms=int((time.monotonic() - started) * 1000),
        )

    try:
        sbom = run_sbom(target, kind=kind)
        sbom_path = sbom["path"]
        tools_run.append("syft")
    except Exception as exc:                                # noqa: BLE001
        LOG.warning("syft step failed: %s", exc)
        tools_skipped.append("syft")
        sbom_path = ""

    futures: dict[str, _cf.Future] = {}
    with _cf.ThreadPoolExecutor(max_workers=3) as pool:
        if sbom_path and _have(GRYPE_BIN):
            futures["grype"] = pool.submit(_scan_grype, sbom_path)
        elif not _have(GRYPE_BIN):
            tools_skipped.append("grype")

        if _have(OSV_BIN):
            futures["osv-scanner"] = pool.submit(_scan_osv, target, kind)
        else:
            tools_skipped.append("osv-scanner")

        if _have(TRIVY_BIN):
            futures["trivy"] = pool.submit(_scan_trivy, target, kind)
        else:
            tools_skipped.append("trivy")

        merged: dict[tuple, Finding] = {}
        for name, fut in futures.items():
            try:
                results = fut.result(timeout=SCA_TIMEOUT + 30)
                tools_run.append(name)
                for f in results:
                    key = f.dedupe_key()
                    if key not in merged or _SEV_RANK[f.severity] < _SEV_RANK[merged[key].severity]:
                        merged[key] = f
            except Exception as exc:                        # noqa: BLE001
                LOG.warning("%s scanner failed: %s", name, exc)
                tools_skipped.append(name)

    findings = sorted(
        merged.values(),
        key=lambda f: (_SEV_RANK.get(f.severity, 99), -f.cvss_score, f.package),
    )

    summary = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        summary[f.severity] = summary.get(f.severity, 0) + 1
    summary["total"] = len(findings)

    report = SBOMReport(
        target=target, kind=kind, sbom_path=sbom_path,
        findings=findings, tools_run=tools_run, tools_skipped=tools_skipped,
        summary=summary,
        wall_time_ms=int((time.monotonic() - started) * 1000),
    )
    _persist_report(report)
    return report


def _persist_report(report: SBOMReport) -> Optional[str]:
    try:
        os.makedirs(SBOM_OUT_DIR, exist_ok=True)
        out = os.path.join(
            SBOM_OUT_DIR,
            f"sca_{os.path.basename(report.target.rstrip('/'))}_{int(time.time())}.json",
        )
        with open(out, "w") as fh:
            json.dump(report.to_dict(), fh, indent=2, default=str)
        return out
    except Exception as exc:                                # noqa: BLE001
        LOG.warning("Could not persist SBOM report: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────────
def record_findings_to_threat_graph(report: SBOMReport) -> int:
    """Promote CRITICAL+HIGH findings into the threat graph + ATT&CK map."""
    try:
        from threat_graph import record_finding             # type: ignore
    except Exception as exc:                                # noqa: BLE001
        LOG.warning("threat_graph unavailable: %s", exc)
        return 0
    inserted = 0
    for f in report.findings:
        if f.severity not in ("CRITICAL", "HIGH"):
            continue
        cwe = ""
        if f.cwe:
            first = f.cwe.split(",")[0].strip()
            cwe = first if first.upper().startswith("CWE-") else (
                f"CWE-{first}" if first else ""
            )
        record_finding({
            "id":          f"sbom::{f.tool}::{f.cve_id or f.package}-{f.version}",
            "repo":        report.target,
            "cwe":         cwe,
            "vuln_class":  "deserialization" if "serial" in (f.title or "").lower() else "rce",
            "severity":    f.severity,
            "confidence":  "HIGH",
            "description": f"{f.tool}: {f.cve_id} in {f.package}@{f.version} — {f.title[:200]}",
            "evidence_hash": "",
        })
        inserted += 1
    return inserted
