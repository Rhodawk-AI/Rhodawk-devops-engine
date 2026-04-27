"""
Rhodawk AI — Compliance Report Generator (GAP 10)
==================================================
Translates raw findings + ATT&CK coverage into auditor-ready reports
mapped to the major compliance frameworks:

  * **OWASP Top-10 (2021)**
  * **SOC 2 Trust Services Criteria** (CC-Series — Common Criteria)
  * **PCI DSS v4.0** (the application-layer requirements that map to
    code-level CWEs)
  * **ISO/IEC 27001:2022 Annex A**
  * **NIST CSF 2.0** (subset — Protect & Detect functions)

Three output formats are produced from the same internal model:

  * ``to_json()``   — machine-readable, used by the dashboard + APIs
  * ``to_markdown()`` — human-readable, used by Telegram + Slack
  * ``to_html()``   — auditor-facing, embeds ATT&CK heatmap + finding table

Design constraints
------------------
1. **No new heavy dependencies.** Pure stdlib + the existing
   ``vuln_classifier`` (CWE → CVSS table) + ``threat_graph``
   (ATT&CK coverage). HTML is generated with f-strings — no Jinja.
2. **Idempotent.** Generating the same input twice produces the same
   bytes (sorted dicts, deterministic timestamps via ``generated_at``).
3. **No silent fallbacks for missing CWEs** — unmapped findings appear
   in a dedicated ``unmapped`` section so auditors can see the gap.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from html import escape as _esc
from typing import Iterable, Optional


# ──────────────────────────────────────────────────────────────────────
# Compliance maps. Sources:
#   * OWASP Top-10 2021 official mapping
#   * AICPA TSC 2017 (revised 2022) — Common Criteria
#   * PCI DSS v4.0 §6.2.4 (secure coding)
#   * ISO/IEC 27001:2022 Annex A controls
#   * NIST CSF 2.0 categories
# ──────────────────────────────────────────────────────────────────────

CWE_TO_OWASP: dict[str, str] = {
    "CWE-79":  "A03:2021-Injection",
    "CWE-89":  "A03:2021-Injection",
    "CWE-78":  "A03:2021-Injection",
    "CWE-77":  "A03:2021-Injection",
    "CWE-94":  "A03:2021-Injection",
    "CWE-918": "A10:2021-SSRF",
    "CWE-22":  "A01:2021-Broken Access Control",
    "CWE-352": "A01:2021-Broken Access Control",
    "CWE-639": "A01:2021-Broken Access Control",
    "CWE-285": "A01:2021-Broken Access Control",
    "CWE-863": "A01:2021-Broken Access Control",
    "CWE-287": "A07:2021-Identification and Authentication Failures",
    "CWE-798": "A07:2021-Identification and Authentication Failures",
    "CWE-259": "A07:2021-Identification and Authentication Failures",
    "CWE-502": "A08:2021-Software and Data Integrity Failures",
    "CWE-611": "A05:2021-Security Misconfiguration",
    "CWE-732": "A05:2021-Security Misconfiguration",
    "CWE-1188": "A05:2021-Security Misconfiguration",
    "CWE-209": "A04:2021-Insecure Design",
    "CWE-119": "A06:2021-Vulnerable and Outdated Components",
    "CWE-120": "A06:2021-Vulnerable and Outdated Components",
    "CWE-787": "A06:2021-Vulnerable and Outdated Components",
    "CWE-416": "A06:2021-Vulnerable and Outdated Components",
    "CWE-190": "A06:2021-Vulnerable and Outdated Components",
    "CWE-434": "A04:2021-Insecure Design",
    "CWE-269": "A01:2021-Broken Access Control",
}

CWE_TO_SOC2: dict[str, list[str]] = {
    # Common Criteria (CC) — security/availability/confidentiality.
    "CWE-79":  ["CC6.1", "CC6.6", "CC7.2"],         # Logical access + system ops
    "CWE-89":  ["CC6.1", "CC7.2"],
    "CWE-78":  ["CC6.1", "CC7.2"],
    "CWE-77":  ["CC6.1", "CC7.2"],
    "CWE-94":  ["CC6.1", "CC7.2"],
    "CWE-918": ["CC6.6", "CC7.2"],
    "CWE-22":  ["CC6.1", "CC6.7"],
    "CWE-352": ["CC6.1"],
    "CWE-639": ["CC6.1", "CC6.3"],
    "CWE-287": ["CC6.1", "CC6.2"],                  # Auth provisioning
    "CWE-798": ["CC6.1", "CC6.2"],
    "CWE-259": ["CC6.1", "CC6.2"],
    "CWE-502": ["CC7.1", "CC8.1"],                  # Change/release integrity
    "CWE-611": ["CC6.6", "CC7.2"],
    "CWE-732": ["CC6.1", "CC6.3"],
    "CWE-209": ["CC6.7", "CC7.3"],                  # Disclosure / monitoring
    "CWE-119": ["CC7.1"],
    "CWE-120": ["CC7.1"],
    "CWE-787": ["CC7.1"],
    "CWE-416": ["CC7.1"],
    "CWE-190": ["CC7.1"],
    "CWE-434": ["CC6.1", "CC6.7"],
    "CWE-269": ["CC6.1", "CC6.3"],
    "CWE-285": ["CC6.1", "CC6.3"],
    "CWE-863": ["CC6.1", "CC6.3"],
}

CWE_TO_PCI_DSS: dict[str, list[str]] = {
    "CWE-79":  ["PCI 6.2.4", "PCI 6.4.1"],
    "CWE-89":  ["PCI 6.2.4", "PCI 6.4.1"],
    "CWE-78":  ["PCI 6.2.4"],
    "CWE-94":  ["PCI 6.2.4"],
    "CWE-918": ["PCI 6.2.4"],
    "CWE-22":  ["PCI 6.2.4", "PCI 7.2"],
    "CWE-352": ["PCI 6.2.4"],
    "CWE-287": ["PCI 8.3"],
    "CWE-798": ["PCI 8.3.1", "PCI 6.5"],
    "CWE-259": ["PCI 8.3.1"],
    "CWE-639": ["PCI 7.2"],
    "CWE-502": ["PCI 6.2.4"],
    "CWE-611": ["PCI 6.2.4"],
    "CWE-732": ["PCI 7.1"],
    "CWE-285": ["PCI 7.2"],
    "CWE-863": ["PCI 7.2"],
}

CWE_TO_ISO27001: dict[str, list[str]] = {
    "CWE-79":  ["A.8.28"],         # Secure coding
    "CWE-89":  ["A.8.28"],
    "CWE-78":  ["A.8.28"],
    "CWE-94":  ["A.8.28"],
    "CWE-918": ["A.8.28", "A.8.23"],   # Web filtering
    "CWE-22":  ["A.8.28", "A.8.3"],
    "CWE-352": ["A.8.28"],
    "CWE-287": ["A.5.16", "A.8.5"],   # Identity / secure auth
    "CWE-798": ["A.8.24"],            # Cryptography / secret mgmt
    "CWE-259": ["A.8.24"],
    "CWE-639": ["A.5.15"],            # Access control
    "CWE-502": ["A.8.28"],
    "CWE-611": ["A.8.28"],
    "CWE-732": ["A.8.3"],             # Information access restriction
    "CWE-285": ["A.5.15"],
    "CWE-863": ["A.5.15"],
    "CWE-269": ["A.5.15"],
}

CWE_TO_NIST_CSF: dict[str, list[str]] = {
    "CWE-79":  ["PR.PS-06"],         # Secure software development
    "CWE-89":  ["PR.PS-06"],
    "CWE-78":  ["PR.PS-06"],
    "CWE-94":  ["PR.PS-06"],
    "CWE-918": ["PR.PS-06", "DE.CM-06"],
    "CWE-22":  ["PR.AA-05", "PR.PS-06"],
    "CWE-287": ["PR.AA-01", "PR.AA-03"],
    "CWE-798": ["PR.AA-01", "PR.DS-02"],
    "CWE-259": ["PR.AA-01", "PR.DS-02"],
    "CWE-502": ["PR.PS-06"],
    "CWE-611": ["PR.PS-06"],
    "CWE-732": ["PR.AA-05"],
    "CWE-285": ["PR.AA-05"],
    "CWE-863": ["PR.AA-05"],
}


SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"]
SEVERITY_RANK  = {s: i for i, s in enumerate(SEVERITY_ORDER)}


# ──────────────────────────────────────────────────────────────────────
@dataclass
class MappedFinding:
    """One finding with all framework mappings resolved."""
    id: str
    repo: str
    cwe: str
    cwe_name: str = ""
    vuln_class: str = ""
    severity: str = "UNKNOWN"
    confidence: str = "UNKNOWN"
    description: str = ""
    evidence_hash: str = ""
    owasp: Optional[str] = None
    soc2: list[str] = field(default_factory=list)
    pci_dss: list[str] = field(default_factory=list)
    iso27001: list[str] = field(default_factory=list)
    nist_csf: list[str] = field(default_factory=list)
    attck: list[dict] = field(default_factory=list)
    cvss_base_score: float = 0.0


@dataclass
class ComplianceReport:
    """Aggregate, framework-keyed view over a list of findings."""
    repo: str
    generated_at: float
    summary: dict[str, int]
    by_framework: dict[str, dict[str, list[str]]]
    findings: list[MappedFinding]
    unmapped: list[MappedFinding]
    attck_coverage: dict
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "repo":           self.repo,
            "generated_at":   self.generated_at,
            "summary":        self.summary,
            "by_framework":   self.by_framework,
            "findings":       [asdict(f) for f in self.findings],
            "unmapped":       [asdict(f) for f in self.unmapped],
            "attck_coverage": self.attck_coverage,
            "notes":          self.notes,
        }


# ──────────────────────────────────────────────────────────────────────
def _enrich_finding(raw: dict) -> MappedFinding:
    cwe = (raw.get("cwe") or "").upper().strip()
    if cwe and not cwe.startswith("CWE-"):
        cwe = f"CWE-{cwe}"

    cwe_name = ""
    cvss_base = 0.0
    try:
        from vuln_classifier import _CWE_DATABASE      # type: ignore
        meta = _CWE_DATABASE.get(cwe) or {}
        cwe_name  = meta.get("name", "")
        cvss_base = float(meta.get("cvss_base", 0.0))
    except Exception:                                  # noqa: BLE001
        pass

    attck_techniques: list[dict] = []
    try:
        from threat_graph import get_mapper            # type: ignore
        m = get_mapper()
        techs = m.cwe_to_techniques(cwe) if cwe else []
        if not techs and raw.get("vuln_class"):
            techs = m.vuln_class_to_techniques(raw["vuln_class"])
        attck_techniques = [t.to_dict() for t in techs]
    except Exception:                                  # noqa: BLE001
        pass

    return MappedFinding(
        id=str(raw.get("id") or f"f-{int(time.time()*1000)}"),
        repo=raw.get("repo", ""),
        cwe=cwe,
        cwe_name=cwe_name,
        vuln_class=(raw.get("vuln_class") or "").lower(),
        severity=(raw.get("severity") or "UNKNOWN").upper(),
        confidence=(raw.get("confidence") or "UNKNOWN").upper(),
        description=raw.get("description", ""),
        evidence_hash=raw.get("evidence_hash", ""),
        owasp=CWE_TO_OWASP.get(cwe),
        soc2=list(CWE_TO_SOC2.get(cwe, [])),
        pci_dss=list(CWE_TO_PCI_DSS.get(cwe, [])),
        iso27001=list(CWE_TO_ISO27001.get(cwe, [])),
        nist_csf=list(CWE_TO_NIST_CSF.get(cwe, [])),
        attck=attck_techniques,
        cvss_base_score=cvss_base,
    )


def build_report(repo: str, raw_findings: Iterable[dict],
                 *, notes: str = "") -> ComplianceReport:
    """Build a ``ComplianceReport`` from a list of raw findings."""
    findings: list[MappedFinding] = []
    for raw in raw_findings:
        if not raw:
            continue
        if not raw.get("repo"):
            raw = {**raw, "repo": repo}
        findings.append(_enrich_finding(raw))

    findings.sort(key=lambda f: (
        SEVERITY_RANK.get(f.severity, len(SEVERITY_ORDER)),
        -f.cvss_base_score,
        f.cwe,
    ))

    summary = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        summary[f.severity] = summary.get(f.severity, 0) + 1
    summary["total"] = len(findings)

    by_framework: dict[str, dict[str, list[str]]] = {
        "owasp_top10": {}, "soc2": {}, "pci_dss": {},
        "iso27001": {}, "nist_csf": {},
    }
    unmapped: list[MappedFinding] = []
    for f in findings:
        any_map = False
        if f.owasp:
            by_framework["owasp_top10"].setdefault(f.owasp, []).append(f.id)
            any_map = True
        for ctrl in f.soc2:
            by_framework["soc2"].setdefault(ctrl, []).append(f.id);     any_map = True
        for ctrl in f.pci_dss:
            by_framework["pci_dss"].setdefault(ctrl, []).append(f.id);  any_map = True
        for ctrl in f.iso27001:
            by_framework["iso27001"].setdefault(ctrl, []).append(f.id); any_map = True
        for ctrl in f.nist_csf:
            by_framework["nist_csf"].setdefault(ctrl, []).append(f.id); any_map = True
        if not any_map:
            unmapped.append(f)

    for fw, controls in by_framework.items():
        by_framework[fw] = {k: sorted(set(v)) for k, v in sorted(controls.items())}

    attck_coverage = {}
    try:
        from threat_graph import risk_score             # type: ignore
        attck_coverage = risk_score(repo)
    except Exception:                                   # noqa: BLE001
        attck_coverage = {"repo": repo, "technique_count": 0,
                          "techniques": [], "tactic_counts": {},
                          "kill_chain_depth": 0, "risk_band": "UNKNOWN"}

    return ComplianceReport(
        repo=repo, generated_at=time.time(),
        summary=summary, by_framework=by_framework,
        findings=findings, unmapped=unmapped,
        attck_coverage=attck_coverage, notes=notes,
    )


# ──────────────────────────────────────────────────────────────────────
# Renderers
# ──────────────────────────────────────────────────────────────────────
def to_json(report: ComplianceReport, *, indent: int = 2) -> str:
    return json.dumps(report.to_dict(), indent=indent, sort_keys=True, default=str)


def to_markdown(report: ComplianceReport) -> str:
    s = report.summary
    lines: list[str] = [
        f"# Rhodawk Compliance Report — `{report.repo}`",
        "",
        f"_Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(report.generated_at))}_",
        "",
        "## Severity Summary",
        "",
        "| Severity | Count |",
        "|---|---|",
    ]
    for sev in SEVERITY_ORDER:
        lines.append(f"| {sev} | {s.get(sev, 0)} |")
    lines.append(f"| **TOTAL** | **{s.get('total', 0)}** |")
    lines.append("")

    cov = report.attck_coverage
    lines += [
        "## ATT&CK Coverage",
        f"* Risk band: **{cov.get('risk_band', 'UNKNOWN')}**",
        f"* Kill-chain depth: **{cov.get('kill_chain_depth', 0)}**",
        f"* Distinct techniques observed: **{cov.get('technique_count', 0)}**",
        "",
    ]

    for fw_key, fw_label in [
        ("owasp_top10", "OWASP Top-10 (2021)"),
        ("soc2",        "SOC 2 Common Criteria"),
        ("pci_dss",     "PCI DSS v4.0"),
        ("iso27001",    "ISO/IEC 27001:2022 Annex A"),
        ("nist_csf",    "NIST CSF 2.0"),
    ]:
        entries = report.by_framework.get(fw_key, {})
        lines.append(f"## {fw_label}")
        if not entries:
            lines.append("* _No findings mapped._")
        else:
            for ctrl, fids in entries.items():
                lines.append(f"* **{ctrl}** — {len(fids)} finding(s): "
                             + ", ".join(f"`{x}`" for x in fids))
        lines.append("")

    if report.unmapped:
        lines += [
            "## Unmapped Findings",
            "_The following findings did not match any framework control."
            " Extend the CWE→framework tables in `report_generator.py`._",
            "",
        ]
        for f in report.unmapped:
            lines.append(f"* `{f.id}` — {f.cwe or 'no-cwe'} ({f.severity})")
        lines.append("")

    if report.notes:
        lines += ["## Notes", report.notes, ""]
    return "\n".join(lines)


def to_html(report: ComplianceReport) -> str:
    s = report.summary
    cov = report.attck_coverage
    severity_rows = "".join(
        f"<tr><td>{sev}</td><td>{s.get(sev, 0)}</td></tr>"
        for sev in SEVERITY_ORDER
    )
    framework_blocks = []
    for fw_key, fw_label in [
        ("owasp_top10", "OWASP Top-10 (2021)"),
        ("soc2",        "SOC 2 Common Criteria"),
        ("pci_dss",     "PCI DSS v4.0"),
        ("iso27001",    "ISO/IEC 27001:2022 Annex A"),
        ("nist_csf",    "NIST CSF 2.0"),
    ]:
        entries = report.by_framework.get(fw_key, {})
        if not entries:
            body = "<em>No findings mapped.</em>"
        else:
            body = "<ul>" + "".join(
                f"<li><strong>{_esc(ctrl)}</strong> — {len(fids)} finding(s): "
                + ", ".join(f"<code>{_esc(x)}</code>" for x in fids)
                + "</li>"
                for ctrl, fids in entries.items()
            ) + "</ul>"
        framework_blocks.append(f"<h2>{_esc(fw_label)}</h2>{body}")

    finding_rows = "".join(
        f"<tr>"
        f"<td><code>{_esc(f.id)}</code></td>"
        f"<td>{_esc(f.cwe or '-')}</td>"
        f"<td>{_esc(f.cwe_name)}</td>"
        f"<td>{_esc(f.severity)}</td>"
        f"<td>{f.cvss_base_score:.1f}</td>"
        f"<td>{_esc(f.owasp or '-')}</td>"
        f"<td>{_esc(', '.join(t['technique_id'] for t in f.attck) or '-')}</td>"
        f"</tr>"
        for f in report.findings
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Rhodawk Compliance Report — {_esc(report.repo)}</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}}
 h1{{border-bottom:2px solid #333}} h2{{margin-top:2rem;border-bottom:1px solid #ccc}}
 table{{border-collapse:collapse;width:100%;margin:1rem 0}}
 th,td{{border:1px solid #ccc;padding:.4rem .6rem;text-align:left;font-size:.9rem}}
 th{{background:#f4f4f4}} code{{background:#f0f0f0;padding:.05rem .25rem;border-radius:3px}}
 .band-CRITICAL{{color:#a40}} .band-HIGH{{color:#c60}} .band-MEDIUM{{color:#a80}}
</style></head><body>
<h1>Rhodawk Compliance Report — <code>{_esc(report.repo)}</code></h1>
<p><em>Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(report.generated_at))}</em></p>

<h2>Severity Summary</h2>
<table><tr><th>Severity</th><th>Count</th></tr>{severity_rows}
<tr><th>TOTAL</th><th>{s.get('total', 0)}</th></tr></table>

<h2>ATT&amp;CK Coverage</h2>
<ul>
 <li>Risk band: <strong class="band-{_esc(cov.get('risk_band','UNKNOWN'))}">{_esc(cov.get('risk_band','UNKNOWN'))}</strong></li>
 <li>Kill-chain depth: <strong>{cov.get('kill_chain_depth', 0)}</strong></li>
 <li>Distinct techniques: <strong>{cov.get('technique_count', 0)}</strong></li>
</ul>

{''.join(framework_blocks)}

<h2>All Findings</h2>
<table>
 <tr><th>ID</th><th>CWE</th><th>Name</th><th>Severity</th><th>CVSS</th><th>OWASP</th><th>ATT&amp;CK</th></tr>
 {finding_rows}
</table>

{('<h2>Notes</h2><p>' + _esc(report.notes) + '</p>') if report.notes else ''}
</body></html>"""


def write_report(report: ComplianceReport, out_dir: str) -> dict[str, str]:
    """Persist all three formats to disk and return their paths."""
    os.makedirs(out_dir, exist_ok=True)
    base = f"compliance_{report.repo.replace('/', '_')}_{int(report.generated_at)}"
    paths = {
        "json":     os.path.join(out_dir, f"{base}.json"),
        "markdown": os.path.join(out_dir, f"{base}.md"),
        "html":     os.path.join(out_dir, f"{base}.html"),
    }
    with open(paths["json"], "w", encoding="utf-8") as fh:
        fh.write(to_json(report))
    with open(paths["markdown"], "w", encoding="utf-8") as fh:
        fh.write(to_markdown(report))
    with open(paths["html"], "w", encoding="utf-8") as fh:
        fh.write(to_html(report))
    return paths
